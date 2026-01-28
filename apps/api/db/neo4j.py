from neo4j import AsyncGraphDatabase

from config import get_settings

driver = None

# Embedding dimensions from NVIDIA NV-EmbedQA model
EMBEDDING_DIMENSIONS = 2048


async def init_neo4j():
    global driver
    settings = get_settings()

    driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )

    # Create constraints and indexes
    async with driver.session() as session:
        # Constraints
        await session.run(
            "CREATE CONSTRAINT decision_id IF NOT EXISTS FOR (d:DecisionTrace) REQUIRE d.id IS UNIQUE"
        )
        await session.run(
            "CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE"
        )
        await session.run(
            "CREATE CONSTRAINT concept_id IF NOT EXISTS FOR (c:Concept) REQUIRE c.id IS UNIQUE"
        )
        await session.run(
            "CREATE CONSTRAINT system_id IF NOT EXISTS FOR (s:System) REQUIRE s.id IS UNIQUE"
        )
        await session.run(
            "CREATE CONSTRAINT technology_id IF NOT EXISTS FOR (t:Technology) REQUIRE t.id IS UNIQUE"
        )
        await session.run(
            "CREATE CONSTRAINT pattern_id IF NOT EXISTS FOR (p:Pattern) REQUIRE p.id IS UNIQUE"
        )

        # Standard indexes
        await session.run(
            "CREATE INDEX decision_created IF NOT EXISTS FOR (d:DecisionTrace) ON (d.created_at)"
        )
        await session.run(
            "CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name)"
        )
        await session.run(
            "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)"
        )

        # Case-insensitive entity lookup (lowercase name)
        # Note: Neo4j doesn't support functional indexes directly, so we use a workaround
        # by creating an index on name and using toLower() in queries
        try:
            await session.run(
                "CREATE INDEX entity_name_lookup IF NOT EXISTS FOR (e:Entity) ON (e.name)"
            )
            print("[Neo4j] Created entity_name_lookup index")
        except Exception as e:
            print(f"[Neo4j] Entity name lookup index skipped: {e}")

        # Entity aliases index for resolution
        try:
            await session.run(
                "CREATE INDEX entity_aliases IF NOT EXISTS FOR (e:Entity) ON (e.aliases)"
            )
            print("[Neo4j] Created entity_aliases index")
        except Exception as e:
            print(f"[Neo4j] Entity aliases index skipped: {e}")

        # Decision source index for filtering
        try:
            await session.run(
                "CREATE INDEX decision_source IF NOT EXISTS FOR (d:DecisionTrace) ON (d.source)"
            )
            print("[Neo4j] Created decision_source index")
        except Exception as e:
            print(f"[Neo4j] Decision source index skipped: {e}")

        # Vector indexes for semantic search (Neo4j 5.11+)
        # These enable fast similarity searches using embeddings
        try:
            await session.run(
                """
                CREATE VECTOR INDEX decision_embedding IF NOT EXISTS
                FOR (d:DecisionTrace)
                ON d.embedding
                OPTIONS {
                    indexConfig: {
                        `vector.dimensions`: $dimensions,
                        `vector.similarity_function`: 'cosine'
                    }
                }
                """,
                dimensions=EMBEDDING_DIMENSIONS,
            )
            print("[Neo4j] Created decision_embedding vector index")
        except Exception as e:
            print(f"[Neo4j] Vector index creation skipped (may already exist or Neo4j < 5.11): {e}")

        try:
            await session.run(
                """
                CREATE VECTOR INDEX entity_embedding IF NOT EXISTS
                FOR (e:Entity)
                ON e.embedding
                OPTIONS {
                    indexConfig: {
                        `vector.dimensions`: $dimensions,
                        `vector.similarity_function`: 'cosine'
                    }
                }
                """,
                dimensions=EMBEDDING_DIMENSIONS,
            )
            print("[Neo4j] Created entity_embedding vector index")
        except Exception as e:
            print(f"[Neo4j] Vector index creation skipped: {e}")

        # Full-text indexes for hybrid search
        try:
            await session.run(
                """
                CREATE FULLTEXT INDEX decision_fulltext IF NOT EXISTS
                FOR (d:DecisionTrace)
                ON EACH [d.trigger, d.context, d.decision, d.rationale]
                """
            )
            print("[Neo4j] Created decision_fulltext index")
        except Exception as e:
            print(f"[Neo4j] Full-text index creation skipped: {e}")

        try:
            await session.run(
                """
                CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS
                FOR (e:Entity)
                ON EACH [e.name]
                """
            )
            print("[Neo4j] Created entity_fulltext index")
        except Exception as e:
            print(f"[Neo4j] Full-text index creation skipped: {e}")


async def close_neo4j():
    global driver
    if driver:
        await driver.close()


async def get_neo4j_session():
    return driver.session()


# Helper functions for common queries

async def find_entity_by_name(name: str, session=None) -> dict | None:
    """Find an entity by name (case-insensitive) or alias."""
    close_session = False
    if session is None:
        session = await get_neo4j_session()
        close_session = True

    try:
        result = await session.run(
            """
            MATCH (e:Entity)
            WHERE toLower(e.name) = toLower($name)
               OR ANY(alias IN COALESCE(e.aliases, []) WHERE toLower(alias) = toLower($name))
            RETURN e.id AS id, e.name AS name, e.type AS type, e.aliases AS aliases
            LIMIT 1
            """,
            name=name,
        )
        record = await result.single()
        return dict(record) if record else None
    finally:
        if close_session:
            await session.close()


async def get_all_entity_names(session=None) -> list[dict]:
    """Get all entity names for fuzzy matching."""
    close_session = False
    if session is None:
        session = await get_neo4j_session()
        close_session = True

    try:
        result = await session.run(
            """
            MATCH (e:Entity)
            RETURN e.id AS id, e.name AS name, e.type AS type
            """
        )
        return [dict(record) async for record in result]
    finally:
        if close_session:
            await session.close()


async def get_decisions_involving_entity(
    entity_name: str, order_by: str = "created_at", session=None
) -> list[dict]:
    """Get all decisions involving an entity, ordered by specified field."""
    close_session = False
    if session is None:
        session = await get_neo4j_session()
        close_session = True

    try:
        result = await session.run(
            f"""
            MATCH (e:Entity)
            WHERE toLower(e.name) = toLower($name)
               OR ANY(alias IN COALESCE(e.aliases, []) WHERE toLower(alias) = toLower($name))
            WITH e
            MATCH (d:DecisionTrace)-[:INVOLVES]->(e)
            RETURN d.id AS id,
                   d.trigger AS trigger,
                   d.decision AS decision,
                   d.rationale AS rationale,
                   d.created_at AS created_at,
                   d.source AS source
            ORDER BY d.{order_by} ASC
            """,
            name=entity_name,
        )
        return [dict(record) async for record in result]
    finally:
        if close_session:
            await session.close()


async def find_similar_entity_by_embedding(
    embedding: list[float], threshold: float = 0.9, session=None
) -> dict | None:
    """Find an entity by embedding similarity."""
    close_session = False
    if session is None:
        session = await get_neo4j_session()
        close_session = True

    try:
        # Try using GDS cosine similarity
        try:
            result = await session.run(
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
            # Fall back to returning all entities for manual calculation
            result = await session.run(
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
                similarity = _cosine_similarity(embedding, other_embedding)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = {
                        "id": record["id"],
                        "name": record["name"],
                        "type": record["type"],
                        "similarity": similarity,
                    }

            return best_match
    finally:
        if close_session:
            await session.close()


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    dot_product = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot_product / (norm_a * norm_b)
