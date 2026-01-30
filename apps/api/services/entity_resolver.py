"""Entity resolution service with multi-stage matching pipeline.

Entity resolution is user-scoped - it only considers entities
connected to the user's decisions when finding duplicates and matches.

Fuzzy Matching Threshold Design Decision (KG-P2-2: Now configurable):
The default 85% threshold was chosen to balance precision and recall:
- 90%+ would miss common variations (e.g., "PostgreSQL" vs "Postgres")
- 80% or below would create too many false positives
- 85% catches most variations while maintaining quality

Thresholds are now configurable via environment variables:
- FUZZY_MATCH_THRESHOLD: For string fuzzy matching (default: 0.85)
- EMBEDDING_SIMILARITY_THRESHOLD: For vector similarity (default: 0.90)

Higher thresholds = more false negatives (duplicates created)
Lower thresholds = more false positives (incorrect merges)
"""

from typing import Optional
from uuid import uuid4

from neo4j.exceptions import ClientError, DatabaseError
from rapidfuzz import fuzz

from config import get_settings
from models.ontology import (
    CANONICAL_NAMES,
    ResolvedEntity,
    get_canonical_name,
    normalize_entity_name,
)
from services.embeddings import get_embedding_service
from utils.logging import get_logger
from utils.vectors import cosine_similarity

logger = get_logger(__name__)

# Configuration constants
FUZZY_MATCH_LIMIT = 500  # Maximum entities to load for fuzzy matching
FUZZY_MATCH_BATCH_SIZE = 100  # Batch size for paginated loading


class EntityResolver:
    """Multi-stage entity resolution pipeline.

    Resolution is user-scoped - only matches against entities
    connected to the user's decisions.

    Resolution stages (in order):
    1. Exact match - Case-insensitive lookup in Neo4j
    2. Canonical lookup - Map aliases to canonical names
    3. Alias search - Check entity aliases field
    4. Fulltext prefix search - Neo4j fulltext index for fuzzy candidates
    5. Fuzzy match - rapidfuzz with configurable threshold (default 85%)
    6. Embedding similarity - Cosine similarity with configurable threshold (default 0.9)
    7. Create new - If no match found

    Performance Considerations:
    - Stages 1-4 use Neo4j indexes and are O(log n) or O(1)
    - Stage 5 (fuzzy) loads candidates in batches with LIMIT to prevent OOM
    - Stage 6 (embedding) uses vector index when available

    Threshold Configuration (KG-P2-2):
    Thresholds are loaded from settings and can be configured via environment:
    - fuzzy_match_threshold: 0.0-1.0 (multiplied by 100 for rapidfuzz)
    - embedding_similarity_threshold: 0.0-1.0 (cosine similarity)
    """

    def __init__(self, neo4j_session, user_id: str = "anonymous"):
        self.session = neo4j_session
        self.user_id = user_id
        self.embedding_service = get_embedding_service()

        # Load configurable thresholds from settings (KG-P2-2)
        settings = get_settings()
        # Convert 0-1 scale to 0-100 for rapidfuzz
        self.fuzzy_threshold = int(settings.fuzzy_match_threshold * 100)
        self.embedding_threshold = settings.embedding_similarity_threshold

        logger.debug(
            f"EntityResolver initialized: fuzzy_threshold={self.fuzzy_threshold}%, "
            f"embedding_threshold={self.embedding_threshold}"
        )

    async def resolve(self, name: str, entity_type: str) -> ResolvedEntity:
        """Resolve an entity name to an existing entity or create a new one.

        Resolution is scoped to user's entities first, then global entities.

        Args:
            name: The entity name to resolve
            entity_type: The type of entity (technology, concept, etc.)

        Returns:
            ResolvedEntity with match details
        """
        normalized_name = normalize_entity_name(name)

        # Stage 1: Exact match (case-insensitive) - user's entities first
        existing = await self._find_by_exact_match(normalized_name)
        if existing:
            return ResolvedEntity(
                id=existing["id"],
                name=existing["name"],
                type=existing["type"],
                is_new=False,
                match_method="exact",
                confidence=1.0,
            )

        # Stage 2: Canonical lookup
        canonical = get_canonical_name(name)
        if canonical.lower() != normalized_name:
            existing = await self._find_by_exact_match(canonical.lower())
            if existing:
                return ResolvedEntity(
                    id=existing["id"],
                    name=existing["name"],
                    type=existing["type"],
                    is_new=False,
                    match_method="canonical",
                    confidence=0.95,
                    canonical_name=canonical,
                )

        # Stage 3: Alias search
        existing = await self._find_by_alias(normalized_name)
        if existing:
            return ResolvedEntity(
                id=existing["id"],
                name=existing["name"],
                type=existing["type"],
                is_new=False,
                match_method="alias",
                confidence=0.92,
            )

        # Stage 4: Fulltext prefix search + Fuzzy match
        # Use Neo4j fulltext index to get candidates, then apply fuzzy matching
        fuzzy_result = await self._find_by_fuzzy_with_fulltext(normalized_name)
        if fuzzy_result:
            return ResolvedEntity(
                id=fuzzy_result["id"],
                name=fuzzy_result["name"],
                type=fuzzy_result["type"],
                is_new=False,
                match_method="fuzzy",
                confidence=fuzzy_result["score"] / 100.0,
            )

        # Stage 5: Embedding similarity
        try:
            embedding = await self.embedding_service.embed_text(
                f"{entity_type}: {name}", input_type="passage"
            )
            similar = await self._find_by_embedding_similarity(
                embedding, threshold=self.embedding_threshold
            )
            if similar:
                return ResolvedEntity(
                    id=similar["id"],
                    name=similar["name"],
                    type=similar["type"],
                    is_new=False,
                    match_method="embedding",
                    confidence=similar["similarity"],
                )
        except (TimeoutError, ConnectionError) as e:
            logger.warning(f"Embedding service connection failed: {e}")
        except (ClientError, DatabaseError) as e:
            logger.warning(f"Database error during embedding similarity: {e}")

        # Stage 6: Create new entity
        final_name = canonical if canonical.lower() != normalized_name else name
        return ResolvedEntity(
            id=str(uuid4()),
            name=final_name,
            type=entity_type,
            is_new=True,
            match_method="new",
            confidence=1.0,
            aliases=[name] if final_name != name else [],
        )

    async def resolve_batch(
        self, entities: list[dict]
    ) -> list[ResolvedEntity]:
        """Resolve multiple entities, returning resolved versions.

        Args:
            entities: List of dicts with 'name' and 'type' keys

        Returns:
            List of ResolvedEntity objects
        """
        resolved = []
        seen_names = {}  # Track resolved names to avoid duplicates within batch

        for entity in entities:
            name = entity.get("name", "")
            entity_type = entity.get("type", "concept")
            normalized = normalize_entity_name(name)

            # Check if we've already resolved this name in this batch
            if normalized in seen_names:
                resolved.append(seen_names[normalized])
                continue

            result = await self.resolve(name, entity_type)
            seen_names[normalized] = result

            # Also track canonical form
            canonical = get_canonical_name(name)
            if canonical.lower() != normalized:
                seen_names[canonical.lower()] = result

            resolved.append(result)

        return resolved

    async def _find_by_exact_match(self, normalized_name: str) -> Optional[dict]:
        """Find entity by exact case-insensitive name match.

        Prefers user's entities but falls back to global entities.
        """
        # First try user's entities
        result = await self.session.run(
            """
            MATCH (d:DecisionTrace)-[:INVOLVES]->(e:Entity)
            WHERE (d.user_id = $user_id OR d.user_id IS NULL)
            AND toLower(e.name) = $name
            RETURN DISTINCT e.id AS id, e.name AS name, e.type AS type
            LIMIT 1
            """,
            name=normalized_name,
            user_id=self.user_id,
        )
        record = await result.single()
        if record:
            return dict(record)

        # Fall back to any entity (for cases like entity creation during decision save)
        result = await self.session.run(
            """
            MATCH (e:Entity)
            WHERE toLower(e.name) = $name
            RETURN e.id AS id, e.name AS name, e.type AS type
            LIMIT 1
            """,
            name=normalized_name,
        )
        record = await result.single()
        return dict(record) if record else None

    async def _find_by_alias(self, normalized_name: str) -> Optional[dict]:
        """Find entity by alias, preferring user's entities."""
        # First try user's entities
        result = await self.session.run(
            """
            MATCH (d:DecisionTrace)-[:INVOLVES]->(e:Entity)
            WHERE (d.user_id = $user_id OR d.user_id IS NULL)
            AND ANY(alias IN COALESCE(e.aliases, []) WHERE toLower(alias) = $name)
            RETURN DISTINCT e.id AS id, e.name AS name, e.type AS type
            LIMIT 1
            """,
            name=normalized_name,
            user_id=self.user_id,
        )
        record = await result.single()
        if record:
            return dict(record)

        # Fall back to any entity
        result = await self.session.run(
            """
            MATCH (e:Entity)
            WHERE ANY(alias IN COALESCE(e.aliases, []) WHERE toLower(alias) = $name)
            RETURN e.id AS id, e.name AS name, e.type AS type
            LIMIT 1
            """,
            name=normalized_name,
        )
        record = await result.single()
        return dict(record) if record else None

    async def _find_by_fuzzy_with_fulltext(self, normalized_name: str) -> Optional[dict]:
        """Find entity using fulltext index for candidates, then fuzzy match.

        This is more efficient than loading all entities:
        1. Use fulltext index to find candidates with similar prefixes/tokens
        2. Apply fuzzy matching only to candidates
        3. Fall back to batched loading if fulltext fails

        Returns dict with id, name, type, score or None.
        """
        # Try fulltext search first to get candidates
        try:
            # Search for entities with similar names using fulltext index
            # Use wildcard search for prefix matching
            search_term = f"{normalized_name}*"

            # First try user's entities via fulltext
            result = await self.session.run(
                """
                CALL db.index.fulltext.queryNodes('entity_fulltext', $search_term)
                YIELD node, score AS fulltext_score
                MATCH (d:DecisionTrace)-[:INVOLVES]->(node)
                WHERE d.user_id = $user_id OR d.user_id IS NULL
                RETURN DISTINCT node.id AS id, node.name AS name, node.type AS type
                LIMIT $limit
                """,
                search_term=search_term,
                user_id=self.user_id,
                limit=FUZZY_MATCH_LIMIT,
            )
            candidates = [dict(r) async for r in result]

            # Also try without fulltext for token-based matching
            if not candidates:
                # Try direct fuzzy on limited set
                candidates = await self._get_entity_names_batched()

            # Apply fuzzy matching to candidates
            best_match = None
            best_score = 0

            for entity in candidates:
                score = fuzz.ratio(normalized_name, entity["name"].lower())
                if score >= self.fuzzy_threshold and score > best_score:
                    best_score = score
                    best_match = entity

            if best_match:
                return {**best_match, "score": best_score}

            return None

        except (ClientError, DatabaseError) as e:
            # Fulltext index may not exist, fall back to batched loading
            logger.debug(f"Fulltext search failed (index may not exist): {e}")
            return await self._find_by_fuzzy_batched(normalized_name)

    async def _find_by_fuzzy_batched(self, normalized_name: str) -> Optional[dict]:
        """Fallback: Find entity by fuzzy matching with batched loading.

        Loads entities in batches to prevent memory issues at scale.
        """
        best_match = None
        best_score = 0
        offset = 0

        while offset < FUZZY_MATCH_LIMIT:
            # Get user's entities in batches
            result = await self.session.run(
                """
                MATCH (d:DecisionTrace)-[:INVOLVES]->(e:Entity)
                WHERE d.user_id = $user_id OR d.user_id IS NULL
                RETURN DISTINCT e.id AS id, e.name AS name, e.type AS type
                SKIP $offset
                LIMIT $batch_size
                """,
                user_id=self.user_id,
                offset=offset,
                batch_size=FUZZY_MATCH_BATCH_SIZE,
            )

            batch = [dict(r) async for r in result]
            if not batch:
                break

            for entity in batch:
                score = fuzz.ratio(normalized_name, entity["name"].lower())
                if score >= self.fuzzy_threshold and score > best_score:
                    best_score = score
                    best_match = entity

            offset += FUZZY_MATCH_BATCH_SIZE

        # If no user entities matched, try global entities with limit
        if not best_match:
            result = await self.session.run(
                """
                MATCH (e:Entity)
                RETURN e.id AS id, e.name AS name, e.type AS type
                LIMIT $limit
                """,
                limit=FUZZY_MATCH_LIMIT,
            )

            async for record in result:
                entity = dict(record)
                score = fuzz.ratio(normalized_name, entity["name"].lower())
                if score >= self.fuzzy_threshold and score > best_score:
                    best_score = score
                    best_match = entity

        if best_match:
            return {**best_match, "score": best_score}
        return None

    async def _get_entity_names_batched(self) -> list[dict]:
        """Get entity names with batched loading and LIMIT.

        Returns user's entities first with a reasonable limit to prevent OOM.
        """
        # Get user's entities with limit
        result = await self.session.run(
            """
            MATCH (d:DecisionTrace)-[:INVOLVES]->(e:Entity)
            WHERE d.user_id = $user_id OR d.user_id IS NULL
            RETURN DISTINCT e.id AS id, e.name AS name, e.type AS type
            LIMIT $limit
            """,
            user_id=self.user_id,
            limit=FUZZY_MATCH_LIMIT,
        )
        user_entities = [dict(record) async for record in result]

        # If we have user entities, use those for fuzzy matching
        if user_entities:
            return user_entities

        # Fall back to all entities if user has none (with limit)
        result = await self.session.run(
            """
            MATCH (e:Entity)
            RETURN e.id AS id, e.name AS name, e.type AS type
            LIMIT $limit
            """,
            limit=FUZZY_MATCH_LIMIT,
        )
        return [dict(record) async for record in result]

    async def _get_all_entity_names(self) -> list[dict]:
        """Get all entity names for fuzzy matching.

        DEPRECATED: Use _get_entity_names_batched() or _find_by_fuzzy_with_fulltext() instead.
        This method is kept for backward compatibility but now applies LIMIT.

        Returns user's entities first, then global entities.
        """
        logger.warning("_get_all_entity_names is deprecated. Use _find_by_fuzzy_with_fulltext instead.")
        return await self._get_entity_names_batched()

    async def _find_by_embedding_similarity(
        self, embedding: list[float], threshold: float
    ) -> Optional[dict]:
        """Find entity by embedding similarity, preferring user's entities."""
        # Try user's entities first with GDS
        try:
            result = await self.session.run(
                """
                MATCH (d:DecisionTrace)-[:INVOLVES]->(e:Entity)
                WHERE (d.user_id = $user_id OR d.user_id IS NULL)
                AND e.embedding IS NOT NULL
                WITH DISTINCT e, gds.similarity.cosine(e.embedding, $embedding) AS similarity
                WHERE similarity > $threshold
                RETURN e.id AS id, e.name AS name, e.type AS type, similarity
                ORDER BY similarity DESC
                LIMIT 1
                """,
                embedding=embedding,
                threshold=threshold,
                user_id=self.user_id,
            )
            record = await result.single()
            if record:
                return dict(record)
        except (ClientError, DatabaseError):
            # Fall back to manual calculation (GDS not installed)
            return await self._find_by_embedding_similarity_manual(embedding, threshold)

        # Fall back to all entities
        try:
            result = await self.session.run(
                """
                MATCH (e:Entity)
                WHERE e.embedding IS NOT NULL
                WITH e, gds.similarity.cosine(e.embedding, $embedding) AS similarity
                WHERE similarity > $threshold
                RETURN e.id AS id, e.name AS name, e.type AS type, similarity
                ORDER BY similarity DESC
                LIMIT 1
                """,
                embedding=embedding,
                threshold=threshold,
            )
            record = await result.single()
            return dict(record) if record else None
        except (ClientError, DatabaseError):
            return await self._find_by_embedding_similarity_manual(embedding, threshold)

    async def _find_by_embedding_similarity_manual(
        self, embedding: list[float], threshold: float
    ) -> Optional[dict]:
        """Fallback: Find entity by embedding similarity without GDS.

        Prefers user's entities. Now uses LIMIT to prevent OOM.
        """
        # Try user's entities first (with limit)
        result = await self.session.run(
            """
            MATCH (d:DecisionTrace)-[:INVOLVES]->(e:Entity)
            WHERE (d.user_id = $user_id OR d.user_id IS NULL)
            AND e.embedding IS NOT NULL
            RETURN DISTINCT e.id AS id, e.name AS name, e.type AS type, e.embedding AS embedding
            LIMIT $limit
            """,
            user_id=self.user_id,
            limit=FUZZY_MATCH_LIMIT,
        )

        best_match = None
        best_similarity = threshold

        async for record in result:
            other_embedding = record["embedding"]
            similarity = cosine_similarity(embedding, other_embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = {
                    "id": record["id"],
                    "name": record["name"],
                    "type": record["type"],
                    "similarity": similarity,
                }

        if best_match:
            return best_match

        # Fall back to all entities (with limit)
        result = await self.session.run(
            """
            MATCH (e:Entity)
            WHERE e.embedding IS NOT NULL
            RETURN e.id AS id, e.name AS name, e.type AS type, e.embedding AS embedding
            LIMIT $limit
            """,
            limit=FUZZY_MATCH_LIMIT,
        )

        async for record in result:
            other_embedding = record["embedding"]
            similarity = cosine_similarity(embedding, other_embedding)
            if similarity > best_similarity:
                best_similarity = similarity
                best_match = {
                    "id": record["id"],
                    "name": record["name"],
                    "type": record["type"],
                    "similarity": similarity,
                }

        return best_match

    async def merge_duplicate_entities(self) -> dict:
        """Find and merge duplicate entities based on fuzzy matching.

        Only merges entities connected to the user's decisions.
        Returns statistics about merged entities.

        Uses batched loading to prevent memory issues at scale.
        """
        all_entities = await self._get_entity_names_batched()
        merged_count = 0
        merge_groups = []

        # Find potential duplicates
        processed = set()
        for i, entity in enumerate(all_entities):
            if entity["id"] in processed:
                continue

            group = [entity]
            processed.add(entity["id"])

            for other in all_entities[i + 1:]:
                if other["id"] in processed:
                    continue

                score = fuzz.ratio(
                    entity["name"].lower(), other["name"].lower()
                )
                if score >= self.fuzzy_threshold:
                    group.append(other)
                    processed.add(other["id"])

            if len(group) > 1:
                merge_groups.append(group)

        # Merge each group
        for group in merge_groups:
            # Keep the entity with the canonical name or the first one
            canonical_entity = None
            for entity in group:
                if entity["name"] in CANONICAL_NAMES.values():
                    canonical_entity = entity
                    break

            primary = canonical_entity or group[0]
            others = [e for e in group if e["id"] != primary["id"]]

            for other in others:
                await self._merge_entities(primary["id"], other["id"])
                merged_count += 1

        return {
            "groups_found": len(merge_groups),
            "entities_merged": merged_count,
        }

    async def _merge_entities(self, primary_id: str, secondary_id: str):
        """Merge secondary entity into primary, transferring all relationships."""
        # Step 1: Transfer INVOLVES relationships
        await self.session.run(
            """
            MATCH (primary:Entity {id: $primary_id})
            MATCH (secondary:Entity {id: $secondary_id})
            OPTIONAL MATCH (d:DecisionTrace)-[r:INVOLVES]->(secondary)
            WITH primary, secondary, collect(DISTINCT d) AS decisions
            FOREACH (d IN decisions |
                MERGE (d)-[:INVOLVES]->(primary)
            )
            """,
            primary_id=primary_id,
            secondary_id=secondary_id,
        )

        # Step 2: Transfer each relationship type separately (Cypher limitation)
        for rel_type in ['IS_A', 'PART_OF', 'RELATED_TO', 'DEPENDS_ON', 'ALTERNATIVE_TO']:
            # Outgoing relationships
            await self.session.run(
                f"""
                MATCH (primary:Entity {{id: $primary_id}})
                MATCH (secondary:Entity {{id: $secondary_id}})
                OPTIONAL MATCH (secondary)-[r:{rel_type}]->(other:Entity)
                WHERE other <> primary
                WITH primary, collect(DISTINCT other) AS targets
                FOREACH (t IN targets |
                    MERGE (primary)-[:{rel_type}]->(t)
                )
                """,
                primary_id=primary_id,
                secondary_id=secondary_id,
            )
            # Incoming relationships
            await self.session.run(
                f"""
                MATCH (primary:Entity {{id: $primary_id}})
                MATCH (secondary:Entity {{id: $secondary_id}})
                OPTIONAL MATCH (other:Entity)-[r:{rel_type}]->(secondary)
                WHERE other <> primary
                WITH primary, collect(DISTINCT other) AS sources
                FOREACH (s IN sources |
                    MERGE (s)-[:{rel_type}]->(primary)
                )
                """,
                primary_id=primary_id,
                secondary_id=secondary_id,
            )

        # Step 3: Add secondary name as alias and delete secondary
        await self.session.run(
            """
            MATCH (primary:Entity {id: $primary_id})
            MATCH (secondary:Entity {id: $secondary_id})
            SET primary.aliases = COALESCE(primary.aliases, []) + secondary.name
            DETACH DELETE secondary
            """,
            primary_id=primary_id,
            secondary_id=secondary_id,
        )

    async def add_alias(self, entity_id: str, alias: str):
        """Add an alias to an entity."""
        await self.session.run(
            """
            MATCH (e:Entity {id: $id})
            SET e.aliases = COALESCE(e.aliases, []) + $alias
            """,
            id=entity_id,
            alias=alias,
        )


# Factory function
def get_entity_resolver(neo4j_session, user_id: str = "anonymous") -> EntityResolver:
    """Create an EntityResolver instance with the given Neo4j session."""
    return EntityResolver(neo4j_session, user_id=user_id)
