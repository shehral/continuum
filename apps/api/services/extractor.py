"""Decision and entity extraction with embedding-based knowledge graph."""

import json
from datetime import UTC, datetime
from json import JSONDecodeError
from typing import Optional
from uuid import uuid4

from neo4j.exceptions import ClientError, DatabaseError

from db.neo4j import get_neo4j_session
from models.ontology import get_canonical_name
from models.schemas import DecisionCreate, Entity
from services.embeddings import get_embedding_service
from services.entity_resolver import EntityResolver
from services.llm import get_llm_client
from services.parser import Conversation
from utils.logging import get_logger
from utils.vectors import cosine_similarity

logger = get_logger(__name__)

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


class DecisionExtractor:
    """Extract decisions and entities from conversations using LLM.

    Enhanced with:
    - Few-shot Chain-of-Thought prompts for better extraction
    - Entity resolution to prevent duplicates
    - ALTERNATIVE_TO relationship detection
    - SUPERSEDES and CONTRADICTS relationship analysis
    - Embedding generation for semantic search
    """

    def __init__(self):
        self.llm = get_llm_client()
        self.embedding_service = get_embedding_service()
        self.similarity_threshold = 0.75  # Minimum similarity to create edge

    async def extract_decisions(self, conversation: Conversation) -> list[DecisionCreate]:
        """Extract decision traces from a conversation."""
        prompt = f"""Analyze this conversation and extract any technical decisions made.
For each decision, identify:
1. Trigger: What prompted the decision (problem, question, requirement)
2. Context: Relevant background information
3. Options: What alternatives were considered
4. Decision: What was decided
5. Rationale: Why this decision was made

Conversation:
{conversation.get_full_text()}

Return a JSON array of decisions. Each decision should have:
{{
  "trigger": "string",
  "context": "string",
  "options": ["string"],
  "decision": "string",
  "rationale": "string",
  "confidence": 0.0-1.0
}}

If no clear decisions are found, return an empty array [].
Return ONLY valid JSON, no markdown or explanation."""

        try:
            response = await self.llm.generate(prompt, temperature=0.3)

            # Parse JSON response
            text = response.strip()
            # Remove markdown code blocks if present
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]

            decisions_data = json.loads(text)

            return [
                DecisionCreate(
                    trigger=d.get("trigger", ""),
                    context=d.get("context", ""),
                    options=d.get("options", []),
                    decision=d.get("decision", ""),
                    rationale=d.get("rationale", ""),
                    confidence=d.get("confidence", 0.8),
                )
                for d in decisions_data
            ]

        except JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            return []
        except (TimeoutError, ConnectionError) as e:
            logger.error(f"LLM connection error: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error extracting decisions: {e}")
            return []

    async def extract_entities(self, text: str) -> list[dict]:
        """Extract entities from text using few-shot CoT prompt.

        Returns list of dicts with name, type, and confidence.
        """
        prompt = ENTITY_EXTRACTION_PROMPT.format(decision_text=text)

        try:
            response = await self.llm.generate(prompt, temperature=0.3)

            # Parse JSON response
            result_text = response.strip()
            if result_text.startswith("```"):
                result_text = result_text.split("\n", 1)[1]
                result_text = result_text.rsplit("```", 1)[0]

            result = json.loads(result_text)
            entities = result.get("entities", [])

            # Log reasoning for debugging
            if result.get("reasoning"):
                logger.debug(f"Entity reasoning: {result['reasoning']}")

            return entities

        except JSONDecodeError as e:
            logger.error(f"Failed to parse entity extraction response: {e}")
            return []
        except (TimeoutError, ConnectionError) as e:
            logger.error(f"LLM connection error during entity extraction: {e}")
            return []

    async def extract_entity_relationships(
        self, entities: list[Entity], context: str = ""
    ) -> list[dict]:
        """Extract relationships between entities using few-shot CoT prompt."""
        if len(entities) < 2:
            return []

        entity_names = [e.name if hasattr(e, 'name') else e.get('name', '') for e in entities]

        prompt = ENTITY_RELATIONSHIP_PROMPT.format(
            entities=json.dumps(entity_names),
            context=context or "General technical discussion",
        )

        try:
            response = await self.llm.generate(prompt, temperature=0.3)

            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]

            result = json.loads(text)
            relationships = result.get("relationships", [])

            # Log reasoning for debugging
            if result.get("reasoning"):
                logger.debug(f"Relationship reasoning: {result['reasoning']}")

            return relationships

        except JSONDecodeError as e:
            logger.error(f"Failed to parse relationship extraction response: {e}")
            return []
        except (TimeoutError, ConnectionError) as e:
            logger.error(f"LLM connection error during relationship extraction: {e}")
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

            text = response.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]

            result = json.loads(text)

            if result.get("relationship") is None:
                return None

            return {
                "type": result.get("relationship"),
                "confidence": result.get("confidence", 0.5),
                "reasoning": result.get("reasoning", ""),
            }

        except JSONDecodeError as e:
            logger.error(f"Failed to parse decision relationship response: {e}")
            return None
        except (TimeoutError, ConnectionError) as e:
            logger.error(f"LLM connection error during decision relationship analysis: {e}")
            return None

    async def save_decision(self, decision: DecisionCreate, source: str = "unknown") -> str:
        """Save a decision to Neo4j with embeddings and rich relationships.

        Uses entity resolution to prevent duplicates and canonicalize names.

        Args:
            decision: The decision to save
            source: Where this decision came from ('claude_logs', 'interview', 'manual')
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
            # Create decision node with embedding
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
                        source: $source
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
                )

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

                    # Validate relationship type
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
            if embedding:
                await self._link_similar_decisions(session, decision_id, embedding)

            # Create temporal chains (INFLUENCED_BY)
            await self._create_temporal_chains(session, decision_id)

        return decision_id

    async def _link_similar_decisions(
        self,
        session,
        decision_id: str,
        embedding: list[float],
    ):
        """Find semantically similar decisions and create SIMILAR_TO edges."""
        try:
            # Use Neo4j vector search to find similar decisions
            result = await session.run(
                """
                MATCH (d:DecisionTrace)
                WHERE d.id <> $id AND d.embedding IS NOT NULL
                WITH d, gds.similarity.cosine(d.embedding, $embedding) AS similarity
                WHERE similarity > $threshold
                RETURN d.id AS similar_id, similarity
                ORDER BY similarity DESC
                LIMIT 5
                """,
                id=decision_id,
                embedding=embedding,
                threshold=self.similarity_threshold,
            )

            records = [r async for r in result]

            for record in records:
                similar_id = record["similar_id"]
                similarity = record["similarity"]

                await session.run(
                    """
                    MATCH (d1:DecisionTrace {id: $id1})
                    MATCH (d2:DecisionTrace {id: $id2})
                    MERGE (d1)-[r:SIMILAR_TO]->(d2)
                    SET r.score = $score
                    """,
                    id1=decision_id,
                    id2=similar_id,
                    score=similarity,
                )
                logger.info(f"Linked similar decision {similar_id} (score: {similarity:.3f})")

        except (ClientError, DatabaseError) as e:
            # GDS library may not be installed, fall back to manual calculation
            logger.debug(f"Vector search failed (GDS may not be installed): {e}")
            await self._link_similar_decisions_manual(session, decision_id, embedding)

    async def _link_similar_decisions_manual(
        self,
        session,
        decision_id: str,
        embedding: list[float],
    ):
        """Fallback: Calculate similarity manually without GDS."""
        try:
            result = await session.run(
                """
                MATCH (d:DecisionTrace)
                WHERE d.id <> $id AND d.embedding IS NOT NULL
                RETURN d.id AS other_id, d.embedding AS other_embedding
                """
                , id=decision_id
            )

            records = [r async for r in result]

            for record in records:
                other_id = record["other_id"]
                other_embedding = record["other_embedding"]

                # Calculate cosine similarity
                similarity = cosine_similarity(embedding, other_embedding)

                if similarity > self.similarity_threshold:
                    await session.run(
                        """
                        MATCH (d1:DecisionTrace {id: $id1})
                        MATCH (d2:DecisionTrace {id: $id2})
                        MERGE (d1)-[r:SIMILAR_TO]->(d2)
                        SET r.score = $score
                        """,
                        id1=decision_id,
                        id2=other_id,
                        score=similarity,
                    )
                    logger.info(f"Linked similar decision {other_id} (score: {similarity:.3f})")

        except (ClientError, DatabaseError) as e:
            logger.error(f"Manual similarity linking failed: {e}")

    async def _create_temporal_chains(self, session, decision_id: str):
        """Create INFLUENCED_BY edges based on shared entities and temporal order."""
        try:
            # Find older decisions that share entities with this one
            await session.run(
                """
                MATCH (d_new:DecisionTrace {id: $new_id})
                MATCH (d_old:DecisionTrace)-[:INVOLVES]->(e:Entity)<-[:INVOLVES]-(d_new)
                WHERE d_old.id <> d_new.id AND d_old.created_at < d_new.created_at
                WITH d_new, d_old, count(DISTINCT e) AS shared_count
                WHERE shared_count >= 2
                MERGE (d_new)-[r:INFLUENCED_BY]->(d_old)
                SET r.shared_entities = shared_count
                """,
                new_id=decision_id,
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
