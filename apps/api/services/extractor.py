"""Decision and entity extraction with embedding-based knowledge graph.

KG-P0-2: LLM response caching to avoid redundant API calls
KG-P0-3: Relationship type validation before storing
"""

import hashlib
import json
from datetime import UTC, datetime
from typing import Optional
from uuid import uuid4

import redis.asyncio as redis
from neo4j.exceptions import ClientError, DatabaseError

from config import get_settings
from db.neo4j import get_neo4j_session
from models.ontology import (
    ENTITY_ONLY_RELATIONSHIPS,
    get_canonical_name,
    validate_entity_relationship,
)
from models.schemas import DecisionCreate, Entity
from services.embeddings import get_embedding_service
from services.entity_resolver import EntityResolver
from services.llm import get_llm_client
from services.parser import Conversation
from utils.json_extraction import extract_json_from_response
from utils.logging import get_logger
from utils.vectors import cosine_similarity

logger = get_logger(__name__)

# Default values for missing decision fields (ML-QW-3)
DEFAULT_DECISION_FIELDS = {
    "confidence": 0.5,
    "context": "",
    "rationale": "",
    "options": [],
    "trigger": "Unknown trigger",
    "decision": "",
}


def apply_decision_defaults(decision_data: dict) -> dict:
    """Apply default values for missing or None decision fields (ML-QW-3).

    This ensures that incomplete decision data from LLM extraction
    or cached responses doesn't cause errors during processing.

    Args:
        decision_data: Raw decision dict from LLM or cache

    Returns:
        Decision dict with defaults applied for missing fields
    """
    result = {}
    for key, default_value in DEFAULT_DECISION_FIELDS.items():
        value = decision_data.get(key)
        if value is None or (isinstance(value, str) and value.strip() == ""):
            result[key] = default_value
        elif isinstance(default_value, list) and not isinstance(value, list):
            # Handle case where options might be a string or other type
            result[key] = default_value
        else:
            result[key] = value
    # Preserve any extra fields not in defaults
    for key, value in decision_data.items():
        if key not in result:
            result[key] = value
    return result



# Few-shot decision extraction prompt with Chain-of-Thought reasoning
DECISION_EXTRACTION_PROMPT = """Analyze this conversation and extract any technical decisions made.

## What constitutes a decision?
A decision is a choice made between alternatives that affects the project. It should have:
- A trigger (problem, requirement, or question that prompted the decision)
- Context (background information, constraints)
- Options (alternatives that were considered)
- The actual decision (what was chosen)
- Rationale (why this choice was made)

## Examples

### Example 1: Single clear decision
Conversation:
"We need to pick a database. I looked at PostgreSQL and MongoDB. PostgreSQL seems better for our relational data needs and the team already knows SQL. Let's go with PostgreSQL."

Output:
```json
[
  {{
    "trigger": "Need to select a database for the project",
    "context": "Team has SQL experience, data is relational in nature",
    "options": ["PostgreSQL", "MongoDB"],
    "decision": "Use PostgreSQL as the primary database",
    "rationale": "Better fit for relational data and team already has SQL expertise",
    "confidence": 0.95
  }}
]
```

### Example 2: Multiple decisions in one conversation
Conversation:
"For the frontend, React makes sense since we're already using it elsewhere. For styling, I considered Tailwind vs CSS modules. Tailwind will speed up development, so let's use that."

Output:
```json
[
  {{
    "trigger": "Need to choose frontend framework",
    "context": "Team already using React in other projects",
    "options": ["React"],
    "decision": "Use React for the frontend",
    "rationale": "Consistency with existing projects and team familiarity",
    "confidence": 0.9
  }},
  {{
    "trigger": "Need to choose a styling approach",
    "context": "Building frontend with React",
    "options": ["Tailwind CSS", "CSS modules"],
    "decision": "Use Tailwind CSS for styling",
    "rationale": "Faster development velocity with utility classes",
    "confidence": 0.85
  }}
]
```

### Example 3: No decisions (just discussion)
Conversation:
"What do you think about microservices? I've heard they can be complex but offer good scalability. We should probably discuss this more with the team before deciding anything."

Output:
```json
[]
```

## Instructions
For each decision found, provide:
- trigger: What prompted the decision (be specific)
- context: Relevant background (constraints, requirements, team situation)
- options: All alternatives considered (include the chosen one)
- decision: What was decided (clear statement)
- rationale: Why this choice (key factors)
- confidence: 0.0-1.0 (how clear/complete the decision is)

If no clear decisions are found, return an empty array [].

## Conversation to analyze:
{conversation_text}

Return ONLY valid JSON, no markdown code blocks or explanation."""


# Few-shot entity extraction prompt with Chain-of-Thought reasoning
ENTITY_EXTRACTION_PROMPT = """Extract technical entities from this decision text.

## Entity Types
- technology: Specific tools, languages, frameworks, databases (e.g., PostgreSQL, React, Python)
- concept: Abstract ideas, principles, methodologies (e.g., microservices, REST API, caching)
- pattern: Design and architectural patterns (e.g., singleton, repository pattern, CQRS)
- system: Software systems, services, components (e.g., authentication system, payment gateway)
- person: People mentioned (team members, stakeholders)
- organization: Companies, teams, departments

## Examples

Input: "We chose React over Vue for the frontend"
Output:
{{
  "entities": [
    {{"name": "React", "type": "technology", "confidence": 0.95}},
    {{"name": "Vue", "type": "technology", "confidence": 0.95}},
    {{"name": "frontend", "type": "concept", "confidence": 0.85}}
  ],
  "reasoning": "React and Vue are frontend frameworks (technology). Frontend is the general concept being discussed."
}}

Input: "JWT tokens stored in Redis for session management"
Output:
{{
  "entities": [
    {{"name": "JWT", "type": "technology", "confidence": 0.95}},
    {{"name": "Redis", "type": "technology", "confidence": 0.95}},
    {{"name": "session management", "type": "concept", "confidence": 0.85}}
  ],
  "reasoning": "JWT is an authentication token standard (technology). Redis is a database (technology). Session management is the concept being implemented."
}}

Input: "Implementing the repository pattern with SQLAlchemy for data access"
Output:
{{
  "entities": [
    {{"name": "repository pattern", "type": "pattern", "confidence": 0.95}},
    {{"name": "SQLAlchemy", "type": "technology", "confidence": 0.95}},
    {{"name": "data access", "type": "concept", "confidence": 0.8}}
  ],
  "reasoning": "Repository pattern is a design pattern. SQLAlchemy is an ORM technology. Data access is the concept being addressed."
}}

## Decision Text
{decision_text}

Extract entities with your reasoning. Return ONLY valid JSON:
{{
  "entities": [{{"name": "string", "type": "entity_type", "confidence": 0.0-1.0}}, ...],
  "reasoning": "Brief explanation of your categorization"
}}"""


# Few-shot entity relationship extraction prompt
ENTITY_RELATIONSHIP_PROMPT = """Identify relationships between these entities.

## Relationship Types
- IS_A: X is a type/category of Y (e.g., "PostgreSQL IS_A Database")
- PART_OF: X is a component of Y (e.g., "React Flow PART_OF React ecosystem")
- DEPENDS_ON: X requires/depends on Y (e.g., "Next.js DEPENDS_ON React")
- RELATED_TO: X is generally related to Y (e.g., "FastAPI RELATED_TO Python")
- ALTERNATIVE_TO: X can be used instead of Y (e.g., "MongoDB ALTERNATIVE_TO PostgreSQL")

## Examples

Entities: ["React", "Vue", "frontend"]
Context: "We chose React over Vue for the frontend"
Output:
{{
  "relationships": [
    {{"from": "React", "to": "frontend", "type": "PART_OF", "confidence": 0.9}},
    {{"from": "Vue", "to": "frontend", "type": "PART_OF", "confidence": 0.9}},
    {{"from": "React", "to": "Vue", "type": "ALTERNATIVE_TO", "confidence": 0.95}}
  ],
  "reasoning": "React and Vue are both frontend frameworks (PART_OF frontend). They were considered as alternatives."
}}

Entities: ["PostgreSQL", "Redis", "caching", "database"]
Context: "Using PostgreSQL as the primary database with Redis for caching"
Output:
{{
  "relationships": [
    {{"from": "PostgreSQL", "to": "database", "type": "IS_A", "confidence": 0.95}},
    {{"from": "Redis", "to": "caching", "type": "PART_OF", "confidence": 0.9}},
    {{"from": "Redis", "to": "database", "type": "IS_A", "confidence": 0.85}}
  ],
  "reasoning": "PostgreSQL is a relational database. Redis is used for caching but is also a database (key-value store)."
}}

Entities: ["Next.js", "React", "TypeScript", "frontend"]
Context: "Building the frontend with Next.js and TypeScript"
Output:
{{
  "relationships": [
    {{"from": "Next.js", "to": "React", "type": "DEPENDS_ON", "confidence": 0.95}},
    {{"from": "Next.js", "to": "frontend", "type": "PART_OF", "confidence": 0.9}},
    {{"from": "TypeScript", "to": "frontend", "type": "PART_OF", "confidence": 0.85}}
  ],
  "reasoning": "Next.js is built on top of React (DEPENDS_ON). Both Next.js and TypeScript are part of the frontend stack."
}}

## Entities: {entities}
## Context: {context}

Identify relationships. Only include relationships you're confident about (>0.7 confidence).
Return ONLY valid JSON:
{{
  "relationships": [{{"from": "entity", "to": "entity", "type": "RELATIONSHIP_TYPE", "confidence": 0.0-1.0}}, ...],
  "reasoning": "Brief explanation"
}}"""


# Decision-to-decision relationship extraction prompt
DECISION_RELATIONSHIP_PROMPT = """Analyze if these two decisions have a significant relationship.

## Relationship Types
- SUPERSEDES: The newer decision explicitly replaces or changes the older decision
- CONTRADICTS: The decisions fundamentally conflict (choosing opposite approaches)

## Examples

Decision A (Jan 15): "Using PostgreSQL for the primary database"
Decision B (Mar 20): "Migrating to MongoDB for horizontal scaling needs"
Output:
{{
  "relationship": "SUPERSEDES",
  "confidence": 0.9,
  "reasoning": "Decision B explicitly changes the database choice from PostgreSQL to MongoDB, superseding Decision A."
}}

Decision A (Feb 1): "REST API for all client communication"
Decision B (Feb 15): "GraphQL for mobile app queries to reduce overfetching"
Output:
{{
  "relationship": null,
  "confidence": 0.0,
  "reasoning": "These decisions are complementary - GraphQL is added for mobile while REST remains for other clients."
}}

Decision A (Jan 10): "Monolithic architecture for faster initial development"
Decision B (Jun 1): "Breaking into microservices for better scaling"
Output:
{{
  "relationship": "SUPERSEDES",
  "confidence": 0.85,
  "reasoning": "Decision B transitions from the monolithic approach in Decision A to microservices."
}}

Decision A (Mar 1): "Using JWT for stateless authentication"
Decision B (Mar 5): "Using session cookies for authentication"
Output:
{{
  "relationship": "CONTRADICTS",
  "confidence": 0.9,
  "reasoning": "JWT (stateless) and session cookies (stateful) are conflicting authentication approaches."
}}

## Decision A ({decision_a_date}):
Trigger: {decision_a_trigger}
Decision: {decision_a_text}
Rationale: {decision_a_rationale}

## Decision B ({decision_b_date}):
Trigger: {decision_b_trigger}
Decision: {decision_b_text}
Rationale: {decision_b_rationale}

Analyze the relationship. Return ONLY valid JSON:
{{
  "relationship": "SUPERSEDES" | "CONTRADICTS" | null,
  "confidence": 0.0-1.0,
  "reasoning": "Brief explanation"
}}"""


class LLMResponseCache:
    """Redis-based cache for LLM extraction responses (KG-P0-2).

    Caches LLM responses keyed by:
    - Hash of input text
    - Prompt template version
    - Extraction type (decision, entity, relationship)

    This avoids redundant API calls when reprocessing the same content.
    """

    def __init__(self):
        self._redis: redis.Redis | None = None
        self._settings = get_settings()

    async def _get_redis(self) -> redis.Redis | None:
        """Get or create Redis connection for caching."""
        if self._redis is None:
            try:
                self._redis = redis.from_url(
                    self._settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await self._redis.ping()
            except Exception as e:
                logger.warning(f"LLM cache Redis connection failed: {e}")
                self._redis = None
        return self._redis

    def _get_cache_key(self, text: str, extraction_type: str) -> str:
        """Generate a cache key for the LLM response.

        Format: llm:{version}:{type}:{hash(text)}
        """
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        version = self._settings.llm_extraction_prompt_version
        return f"llm:{version}:{extraction_type}:{text_hash}"

    async def get(self, text: str, extraction_type: str) -> dict | list | None:
        """Get cached LLM response if available."""
        if not self._settings.llm_cache_enabled:
            return None

        redis_client = await self._get_redis()
        if redis_client is None:
            return None

        try:
            cache_key = self._get_cache_key(text, extraction_type)
            cached = await redis_client.get(cache_key)
            if cached:
                logger.debug(f"LLM cache hit for {extraction_type}")
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"LLM cache read error: {e}")

        return None

    async def set(self, text: str, extraction_type: str, response: dict | list) -> None:
        """Cache an LLM response."""
        if not self._settings.llm_cache_enabled:
            return

        redis_client = await self._get_redis()
        if redis_client is None:
            return

        try:
            cache_key = self._get_cache_key(text, extraction_type)
            await redis_client.setex(
                cache_key,
                self._settings.llm_cache_ttl,
                json.dumps(response),
            )
            logger.debug(f"LLM cache set for {extraction_type}")
        except Exception as e:
            logger.warning(f"LLM cache write error: {e}")


class DecisionExtractor:
    """Extract decisions and entities from conversations using LLM.

    Enhanced with:
    - Few-shot Chain-of-Thought prompts for better extraction
    - Entity resolution to prevent duplicates
    - ALTERNATIVE_TO relationship detection
    - SUPERSEDES and CONTRADICTS relationship analysis
    - Embedding generation for semantic search
    - Multi-tenant user isolation via user_id
    - Robust JSON parsing for LLM responses
    - Configurable similarity threshold
    - LLM response caching (KG-P0-2)
    - Relationship type validation (KG-P0-3)
    """

    def __init__(self):
        self.llm = get_llm_client()
        self.embedding_service = get_embedding_service()
        self.cache = LLMResponseCache()
        settings = get_settings()
        self.similarity_threshold = settings.similarity_threshold
        self.high_confidence_threshold = settings.high_confidence_similarity_threshold

    async def extract_decisions(
        self,
        conversation: Conversation,
        bypass_cache: bool = False
    ) -> list[DecisionCreate]:
        """Extract decision traces from a conversation using few-shot CoT prompt.

        Args:
            conversation: The conversation to extract decisions from
            bypass_cache: If True, skip cache lookup and force fresh extraction
        """
        conversation_text = conversation.get_full_text()

        # Check cache first (KG-P0-2)
        if not bypass_cache:
            cached = await self.cache.get(conversation_text, "decisions")
            if cached is not None:
                logger.info("Using cached decision extraction")
                # Apply defaults for missing fields (ML-QW-3)
                return [
                    DecisionCreate(**{
                        k: v for k, v in apply_decision_defaults(d).items()
                        if k in ("trigger", "context", "options", "decision", "rationale", "confidence")
                    })
                    for d in cached
                    if apply_decision_defaults(d).get("decision")
                ]

        prompt = DECISION_EXTRACTION_PROMPT.format(
            conversation_text=conversation_text
        )

        try:
            response = await self.llm.generate(prompt, temperature=0.3)

            # Use robust JSON extraction
            decisions_data = extract_json_from_response(response)

            if decisions_data is None:
                logger.warning("Failed to parse decisions from LLM response")
                return []

            # Ensure we have a list
            if not isinstance(decisions_data, list):
                logger.warning(f"Expected list, got {type(decisions_data)}")
                return []

            # Cache the result (KG-P0-2)
            await self.cache.set(conversation_text, "decisions", decisions_data)

            # Apply defaults for missing fields (ML-QW-3)
            return [
                DecisionCreate(**{
                    k: v for k, v in apply_decision_defaults(d).items()
                    if k in ("trigger", "context", "options", "decision", "rationale", "confidence")
                })
                for d in decisions_data
                if apply_decision_defaults(d).get("decision")  # Skip entries without a decision
            ]

        except (TimeoutError, ConnectionError) as e:
            logger.error(f"LLM connection error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error extracting decisions: {e}")
            return []

    async def extract_entities(
        self,
        text: str,
        bypass_cache: bool = False
    ) -> list[dict]:
        """Extract entities from text using few-shot CoT prompt.

        Args:
            text: The text to extract entities from
            bypass_cache: If True, skip cache lookup and force fresh extraction

        Returns list of dicts with name, type, and confidence.
        """
        # Check cache first (KG-P0-2)
        if not bypass_cache:
            cached = await self.cache.get(text, "entities")
            if cached is not None:
                logger.info("Using cached entity extraction")
                return cached

        prompt = ENTITY_EXTRACTION_PROMPT.format(decision_text=text)

        try:
            response = await self.llm.generate(prompt, temperature=0.3)

            # Use robust JSON extraction
            result = extract_json_from_response(response)

            if result is None:
                logger.warning("Failed to parse entity extraction response")
                return []

            entities = result.get("entities", [])

            # Log reasoning for debugging
            if result.get("reasoning"):
                logger.debug(f"Entity reasoning: {result['reasoning']}")

            # Cache the result (KG-P0-2)
            await self.cache.set(text, "entities", entities)

            return entities

        except (TimeoutError, ConnectionError) as e:
            logger.error(f"LLM connection error during entity extraction: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during entity extraction: {e}")
            return []

    async def extract_entity_relationships(
        self,
        entities: list[Entity],
        context: str = "",
        bypass_cache: bool = False
    ) -> list[dict]:
        """Extract relationships between entities using few-shot CoT prompt.

        Includes relationship type validation (KG-P0-3).
        """
        if len(entities) < 2:
            return []

        import json as json_module
        entity_names = [e.name if hasattr(e, 'name') else e.get('name', '') for e in entities]

        # Build entity type lookup for validation
        entity_types = {}
        for e in entities:
            name = e.name if hasattr(e, 'name') else e.get('name', '')
            etype = e.type if hasattr(e, 'type') else e.get('type', 'concept')
            entity_types[name.lower()] = etype

        # Cache key includes entities and context
        cache_text = f"{json_module.dumps(sorted(entity_names))}|{context}"

        # Check cache first (KG-P0-2)
        if not bypass_cache:
            cached = await self.cache.get(cache_text, "relationships")
            if cached is not None:
                logger.info("Using cached relationship extraction")
                return cached

        prompt = ENTITY_RELATIONSHIP_PROMPT.format(
            entities=json_module.dumps(entity_names),
            context=context or "General technical discussion",
        )

        try:
            response = await self.llm.generate(prompt, temperature=0.3)

            # Use robust JSON extraction
            result = extract_json_from_response(response)

            if result is None:
                logger.warning("Failed to parse relationship extraction response")
                return []

            relationships = result.get("relationships", [])

            # Log reasoning for debugging
            if result.get("reasoning"):
                logger.debug(f"Relationship reasoning: {result['reasoning']}")

            # Validate and filter relationships (KG-P0-3)
            validated_relationships = []
            for rel in relationships:
                rel_type = rel.get("type", "RELATED_TO")
                from_name = rel.get("from", "")
                to_name = rel.get("to", "")
                confidence = rel.get("confidence", 0.8)

                # Get entity types for validation
                from_type = entity_types.get(from_name.lower(), "concept")
                to_type = entity_types.get(to_name.lower(), "concept")

                # Validate the relationship (KG-P0-3)
                is_valid, error_msg = validate_entity_relationship(
                    rel_type, from_type, to_type
                )

                if is_valid:
                    validated_relationships.append(rel)
                else:
                    # Log invalid relationship for review
                    logger.warning(
                        f"Invalid relationship skipped: {from_name} ({from_type}) "
                        f"-[{rel_type}]-> {to_name} ({to_type}). Reason: {error_msg}"
                    )
                    # Try to suggest a valid alternative
                    if rel_type in ENTITY_ONLY_RELATIONSHIPS:
                        # Fall back to RELATED_TO if the specific type doesn't work
                        validated_relationships.append({
                            "from": from_name,
                            "to": to_name,
                            "type": "RELATED_TO",
                            "confidence": confidence * 0.8,  # Lower confidence for fallback
                        })
                        logger.info(
                            f"Fell back to RELATED_TO for: {from_name} -> {to_name}"
                        )

            # Cache the validated result (KG-P0-2)
            await self.cache.set(cache_text, "relationships", validated_relationships)

            return validated_relationships

        except (TimeoutError, ConnectionError) as e:
            logger.error(f"LLM connection error during relationship extraction: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error during relationship extraction: {e}")
            return []

    async def extract_decision_relationship(
        self, decision_a: dict, decision_b: dict
    ) -> Optional[dict]:
        """Analyze two decisions for SUPERSEDES or CONTRADICTS relationship."""
        prompt = DECISION_RELATIONSHIP_PROMPT.format(
            decision_a_date=decision_a.get("created_at", "unknown"),
            decision_a_trigger=decision_a.get("trigger", ""),
            decision_a_text=decision_a.get("decision", ""),
            decision_a_rationale=decision_a.get("rationale", ""),
            decision_b_date=decision_b.get("created_at", "unknown"),
            decision_b_trigger=decision_b.get("trigger", ""),
            decision_b_text=decision_b.get("decision", ""),
            decision_b_rationale=decision_b.get("rationale", ""),
        )

        try:
            response = await self.llm.generate(prompt, temperature=0.3)

            # Use robust JSON extraction
            result = extract_json_from_response(response)

            if result is None:
                logger.warning("Failed to parse decision relationship response")
                return None

            if result.get("relationship") is None:
                return None

            return {
                "type": result.get("relationship"),
                "confidence": result.get("confidence", 0.5),
                "reasoning": result.get("reasoning", ""),
            }

        except (TimeoutError, ConnectionError) as e:
            logger.error(f"LLM connection error during decision relationship analysis: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during decision relationship analysis: {e}")
            return None

    async def save_decision(
        self,
        decision: DecisionCreate,
        source: str = "unknown",
        user_id: str = "anonymous",
    ) -> str:
        """Save a decision to Neo4j with embeddings and rich relationships.

        Uses entity resolution to prevent duplicates and canonicalize names.
        Includes user_id for multi-tenant data isolation.

        Args:
            decision: The decision to save
            source: Where this decision came from ('claude_logs', 'interview', 'manual')
            user_id: The user ID for multi-tenant isolation (default: "anonymous")

        Returns:
            The ID of the created decision
        """
        decision_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()
        # Use source from decision if provided, otherwise use parameter
        decision_source = getattr(decision, 'source', None) or source

        # Generate embedding for the decision
        decision_dict = {
            "trigger": decision.trigger,
            "context": decision.context,
            "options": decision.options,
            "decision": decision.decision,
            "rationale": decision.rationale,
        }

        try:
            embedding = await self.embedding_service.embed_decision(decision_dict)
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
        except (TimeoutError, ConnectionError) as e:
            logger.warning(f"Embedding service connection failed: {e}")
            embedding = None
        except ValueError as e:
            logger.warning(f"Invalid embedding input: {e}")
            embedding = None

        session = await get_neo4j_session()
        async with session:
            # Create decision node with embedding and user_id
            if embedding:
                await session.run(
                    """
                    CREATE (d:DecisionTrace {
                        id: $id,
                        trigger: $trigger,
                        context: $context,
                        options: $options,
                        decision: $decision,
                        rationale: $rationale,
                        confidence: $confidence,
                        created_at: $created_at,
                        source: $source,
                        user_id: $user_id,
                        embedding: $embedding
                    })
                    """,
                    id=decision_id,
                    trigger=decision.trigger,
                    context=decision.context,
                    options=decision.options,
                    decision=decision.decision,
                    rationale=decision.rationale,
                    confidence=decision.confidence,
                    created_at=created_at,
                    source=decision_source,
                    user_id=user_id,
                    embedding=embedding,
                )
            else:
                await session.run(
                    """
                    CREATE (d:DecisionTrace {
                        id: $id,
                        trigger: $trigger,
                        context: $context,
                        options: $options,
                        decision: $decision,
                        rationale: $rationale,
                        confidence: $confidence,
                        created_at: $created_at,
                        source: $source,
                        user_id: $user_id
                    })
                    """,
                    id=decision_id,
                    trigger=decision.trigger,
                    context=decision.context,
                    options=decision.options,
                    decision=decision.decision,
                    rationale=decision.rationale,
                    confidence=decision.confidence,
                    created_at=created_at,
                    source=decision_source,
                    user_id=user_id,
                )

            logger.info(f"Created decision {decision_id} for user {user_id}")

            # Extract entities with enhanced prompt
            full_text = f"{decision.trigger} {decision.context} {decision.decision} {decision.rationale}"
            entities_data = await self.extract_entities(full_text)
            logger.info(f"Extracted {len(entities_data)} entities")

            # Create entity resolver for this session
            resolver = EntityResolver(session)

            # Resolve and create/link entities
            resolved_entities = []
            for entity_data in entities_data:
                name = entity_data.get("name", "")
                entity_type = entity_data.get("type", "concept")
                confidence = entity_data.get("confidence", 0.8)

                if not name:
                    continue

                # Resolve entity (finds existing or creates new)
                resolved = await resolver.resolve(name, entity_type)
                resolved_entities.append(resolved)

                # Generate entity embedding for new entities
                entity_embedding = None
                if resolved.is_new:
                    try:
                        entity_embedding = await self.embedding_service.embed_entity({
                            "name": resolved.name,
                            "type": resolved.type,
                        })
                    except (TimeoutError, ConnectionError, ValueError):
                        pass

                # Create or update entity node
                if resolved.is_new:
                    if entity_embedding:
                        await session.run(
                            """
                            CREATE (e:Entity {
                                id: $id,
                                name: $name,
                                type: $type,
                                aliases: $aliases,
                                embedding: $embedding
                            })
                            WITH e
                            MATCH (d:DecisionTrace {id: $decision_id})
                            CREATE (d)-[:INVOLVES {weight: $confidence}]->(e)
                            """,
                            id=resolved.id,
                            name=resolved.name,
                            type=resolved.type,
                            aliases=resolved.aliases,
                            embedding=entity_embedding,
                            decision_id=decision_id,
                            confidence=confidence,
                        )
                    else:
                        await session.run(
                            """
                            CREATE (e:Entity {
                                id: $id,
                                name: $name,
                                type: $type,
                                aliases: $aliases
                            })
                            WITH e
                            MATCH (d:DecisionTrace {id: $decision_id})
                            CREATE (d)-[:INVOLVES {weight: $confidence}]->(e)
                            """,
                            id=resolved.id,
                            name=resolved.name,
                            type=resolved.type,
                            aliases=resolved.aliases,
                            decision_id=decision_id,
                            confidence=confidence,
                        )
                    logger.info(f"Created new entity: {resolved.name} ({resolved.type})")
                else:
                    # Link to existing entity
                    await session.run(
                        """
                        MATCH (e:Entity {id: $entity_id})
                        MATCH (d:DecisionTrace {id: $decision_id})
                        MERGE (d)-[:INVOLVES {weight: $confidence}]->(e)
                        """,
                        entity_id=resolved.id,
                        decision_id=decision_id,
                        confidence=confidence,
                    )
                    logger.info(f"Linked to existing entity: {resolved.name} (method: {resolved.match_method})")

            # Extract and create entity-to-entity relationships
            if len(resolved_entities) >= 2:
                entity_rels = await self.extract_entity_relationships(
                    [{"name": e.name, "type": e.type} for e in resolved_entities],
                    context=full_text,
                )
                logger.info(f"Extracted {len(entity_rels)} entity relationships")

                for rel in entity_rels:
                    rel_type = rel.get("type", "RELATED_TO")
                    confidence = rel.get("confidence", 0.8)
                    from_name = rel.get("from")
                    to_name = rel.get("to")

                    # Validate relationship type (already done in extract_entity_relationships)
                    valid_types = ["IS_A", "PART_OF", "RELATED_TO", "DEPENDS_ON", "ALTERNATIVE_TO"]
                    if rel_type not in valid_types:
                        rel_type = "RELATED_TO"

                    # Resolve entity names to canonical forms
                    from_canonical = get_canonical_name(from_name) if from_name else None
                    to_canonical = get_canonical_name(to_name) if to_name else None

                    if from_canonical and to_canonical:
                        await session.run(
                            f"""
                            MATCH (e1:Entity)
                            WHERE toLower(e1.name) = toLower($from_name)
                               OR ANY(alias IN COALESCE(e1.aliases, []) WHERE toLower(alias) = toLower($from_name))
                            MATCH (e2:Entity)
                            WHERE toLower(e2.name) = toLower($to_name)
                               OR ANY(alias IN COALESCE(e2.aliases, []) WHERE toLower(alias) = toLower($to_name))
                            WITH e1, e2
                            WHERE e1 <> e2
                            MERGE (e1)-[r:{rel_type}]->(e2)
                            SET r.confidence = $confidence
                            """,
                            from_name=from_name,
                            to_name=to_name,
                            confidence=confidence,
                        )

            # Find and link similar decisions (if embedding exists)
            # Only compare with decisions from the same user for isolation
            if embedding:
                await self._link_similar_decisions(session, decision_id, embedding, user_id)

            # Create temporal chains (INFLUENCED_BY)
            # Only within the same user's decisions
            await self._create_temporal_chains(session, decision_id, user_id)

        return decision_id

    async def _link_similar_decisions(
        self,
        session,
        decision_id: str,
        embedding: list[float],
        user_id: str,
    ):
        """Find semantically similar decisions and create SIMILAR_TO edges.

        Only compares within the same user's decisions for multi-tenant isolation.
        Uses configurable similarity threshold from settings.
        """
        try:
            # Use Neo4j vector search to find similar decisions within user scope
            result = await session.run(
                """
                MATCH (d:DecisionTrace)
                WHERE d.id <> $id AND d.embedding IS NOT NULL
                  AND (d.user_id = $user_id OR d.user_id IS NULL)
                WITH d, gds.similarity.cosine(d.embedding, $embedding) AS similarity
                WHERE similarity > $threshold
                RETURN d.id AS similar_id, similarity
                ORDER BY similarity DESC
                LIMIT 5
                """,
                id=decision_id,
                embedding=embedding,
                threshold=self.similarity_threshold,
                user_id=user_id,
            )

            records = [r async for r in result]

            for record in records:
                similar_id = record["similar_id"]
                similarity = record["similarity"]

                # Determine confidence tier
                confidence_tier = "high" if similarity >= self.high_confidence_threshold else "moderate"

                await session.run(
                    """
                    MATCH (d1:DecisionTrace {id: $id1})
                    MATCH (d2:DecisionTrace {id: $id2})
                    MERGE (d1)-[r:SIMILAR_TO]->(d2)
                    SET r.score = $score, r.confidence_tier = $tier
                    """,
                    id1=decision_id,
                    id2=similar_id,
                    score=similarity,
                    tier=confidence_tier,
                )
                logger.info(f"Linked similar decision {similar_id} (score: {similarity:.3f}, tier: {confidence_tier})")

        except (ClientError, DatabaseError) as e:
            # GDS library may not be installed, fall back to manual calculation
            logger.debug(f"Vector search failed (GDS may not be installed): {e}")
            await self._link_similar_decisions_manual(session, decision_id, embedding, user_id)

    async def _link_similar_decisions_manual(
        self,
        session,
        decision_id: str,
        embedding: list[float],
        user_id: str,
    ):
        """Fallback: Calculate similarity manually without GDS.

        Only compares within the same user's decisions.
        """
        try:
            result = await session.run(
                """
                MATCH (d:DecisionTrace)
                WHERE d.id <> $id AND d.embedding IS NOT NULL
                  AND (d.user_id = $user_id OR d.user_id IS NULL)
                RETURN d.id AS other_id, d.embedding AS other_embedding
                """,
                id=decision_id,
                user_id=user_id,
            )

            records = [r async for r in result]

            for record in records:
                other_id = record["other_id"]
                other_embedding = record["other_embedding"]

                # Calculate cosine similarity
                similarity = cosine_similarity(embedding, other_embedding)

                if similarity > self.similarity_threshold:
                    # Determine confidence tier
                    confidence_tier = "high" if similarity >= self.high_confidence_threshold else "moderate"

                    await session.run(
                        """
                        MATCH (d1:DecisionTrace {id: $id1})
                        MATCH (d2:DecisionTrace {id: $id2})
                        MERGE (d1)-[r:SIMILAR_TO]->(d2)
                        SET r.score = $score, r.confidence_tier = $tier
                        """,
                        id1=decision_id,
                        id2=other_id,
                        score=similarity,
                        tier=confidence_tier,
                    )
                    logger.info(f"Linked similar decision {other_id} (score: {similarity:.3f}, tier: {confidence_tier})")

        except (ClientError, DatabaseError) as e:
            logger.error(f"Manual similarity linking failed: {e}")

    async def _create_temporal_chains(self, session, decision_id: str, user_id: str):
        """Create INFLUENCED_BY edges based on shared entities and temporal order.

        Only creates chains within the same user's decisions.
        """
        try:
            # Find older decisions that share entities with this one (within user scope)
            await session.run(
                """
                MATCH (d_new:DecisionTrace {id: $new_id})
                MATCH (d_old:DecisionTrace)-[:INVOLVES]->(e:Entity)<-[:INVOLVES]-(d_new)
                WHERE d_old.id <> d_new.id AND d_old.created_at < d_new.created_at
                  AND (d_old.user_id = $user_id OR d_old.user_id IS NULL)
                WITH d_new, d_old, count(DISTINCT e) AS shared_count
                WHERE shared_count >= 2
                MERGE (d_new)-[r:INFLUENCED_BY]->(d_old)
                SET r.shared_entities = shared_count
                """,
                new_id=decision_id,
                user_id=user_id,
            )
            logger.debug(f"Created temporal chains for decision {decision_id}")
        except (ClientError, DatabaseError) as e:
            logger.error(f"Temporal chain creation failed: {e}")


# Singleton instance
_extractor: Optional[DecisionExtractor] = None


def get_extractor() -> DecisionExtractor:
    """Get the decision extractor singleton."""
    global _extractor
    if _extractor is None:
        _extractor = DecisionExtractor()
    return _extractor
