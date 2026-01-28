"""Entity resolution service with multi-stage matching pipeline."""

from typing import Optional
from uuid import uuid4

from rapidfuzz import fuzz

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


class EntityResolver:
    """Multi-stage entity resolution pipeline.

    Resolution stages (in order):
    1. Exact match - Case-insensitive lookup in Neo4j
    2. Canonical lookup - Map aliases to canonical names
    3. Alias search - Check entity aliases field
    4. Fuzzy match - rapidfuzz with 85% threshold
    5. Embedding similarity - Cosine similarity > 0.9
    6. Create new - If no match found
    """

    def __init__(self, neo4j_session):
        self.session = neo4j_session
        self.embedding_service = get_embedding_service()
        self.fuzzy_threshold = 85  # Percentage for fuzzy matching
        self.embedding_threshold = 0.9  # Cosine similarity threshold

    async def resolve(self, name: str, entity_type: str) -> ResolvedEntity:
        """Resolve an entity name to an existing entity or create a new one.

        Args:
            name: The entity name to resolve
            entity_type: The type of entity (technology, concept, etc.)

        Returns:
            ResolvedEntity with match details
        """
        normalized_name = normalize_entity_name(name)

        # Stage 1: Exact match (case-insensitive)
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

        # Stage 4: Fuzzy match
        all_entities = await self._get_all_entity_names()
        best_fuzzy_match = None
        best_fuzzy_score = 0

        for entity in all_entities:
            score = fuzz.ratio(normalized_name, entity["name"].lower())
            if score >= self.fuzzy_threshold and score > best_fuzzy_score:
                best_fuzzy_score = score
                best_fuzzy_match = entity

        if best_fuzzy_match:
            return ResolvedEntity(
                id=best_fuzzy_match["id"],
                name=best_fuzzy_match["name"],
                type=best_fuzzy_match["type"],
                is_new=False,
                match_method="fuzzy",
                confidence=best_fuzzy_score / 100.0,
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
        except Exception as e:
            logger.error(f"Embedding similarity check failed: {e}")

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
        """Find entity by exact case-insensitive name match."""
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
        """Find entity by alias."""
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

    async def _get_all_entity_names(self) -> list[dict]:
        """Get all entity names for fuzzy matching."""
        result = await self.session.run(
            """
            MATCH (e:Entity)
            RETURN e.id AS id, e.name AS name, e.type AS type
            """
        )
        return [dict(record) async for record in result]

    async def _find_by_embedding_similarity(
        self, embedding: list[float], threshold: float
    ) -> Optional[dict]:
        """Find entity by embedding similarity."""
        # Try GDS cosine similarity first
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
        except Exception:
            # Fall back to manual calculation
            return await self._find_by_embedding_similarity_manual(embedding, threshold)

    async def _find_by_embedding_similarity_manual(
        self, embedding: list[float], threshold: float
    ) -> Optional[dict]:
        """Fallback: Find entity by embedding similarity without GDS."""
        result = await self.session.run(
            """
            MATCH (e:Entity)
            WHERE e.embedding IS NOT NULL
            RETURN e.id AS id, e.name AS name, e.type AS type, e.embedding AS embedding
            """
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

        return best_match

    async def merge_duplicate_entities(self) -> dict:
        """Find and merge duplicate entities based on fuzzy matching.

        Returns statistics about merged entities.
        """
        all_entities = await self._get_all_entity_names()
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
def get_entity_resolver(neo4j_session) -> EntityResolver:
    """Create an EntityResolver instance with the given Neo4j session."""
    return EntityResolver(neo4j_session)
