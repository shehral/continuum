from uuid import uuid4
from fastapi import APIRouter

from db.neo4j import get_neo4j_session
from models.schemas import Entity, LinkEntityRequest, SuggestEntitiesRequest
from services.extractor import DecisionExtractor

router = APIRouter()


@router.post("/link")
async def link_entity(request: LinkEntityRequest):
    """Link an entity to a decision."""
    session = await get_neo4j_session()
    async with session:
        await session.run(
            """
            MATCH (d:DecisionTrace {id: $decision_id})
            MATCH (e:Entity {id: $entity_id})
            MERGE (d)-[:INVOLVES {relationship: $relationship}]->(e)
            """,
            decision_id=request.decision_id,
            entity_id=request.entity_id,
            relationship=request.relationship,
        )

    return {"status": "linked"}


@router.post("/suggest", response_model=list[Entity])
async def suggest_entities(request: SuggestEntitiesRequest):
    """Suggest entities to link based on text content."""
    extractor = DecisionExtractor()

    # Extract entities from text
    raw_entities = await extractor.extract_entities(request.text)

    # Convert to Entity objects if they're dicts
    entities = []
    for e in raw_entities:
        if isinstance(e, dict):
            entities.append(Entity(
                id=e.get("id"),
                name=e.get("name", ""),
                type=e.get("type", "concept"),
            ))
        else:
            entities.append(e)

    # Find existing entities that match
    session = await get_neo4j_session()
    async with session:
        suggestions = []

        for entity in entities:
            # Look for similar existing entities
            result = await session.run(
                """
                MATCH (e:Entity)
                WHERE toLower(e.name) CONTAINS toLower($name)
                RETURN e
                LIMIT 3
                """,
                name=entity.name,
            )

            async for record in result:
                e = record["e"]
                suggestions.append(
                    Entity(
                        id=e["id"],
                        name=e["name"],
                        type=e.get("type", "concept"),
                    )
                )

        # Add new entities if not found
        for entity in entities:
            if not any(s.name.lower() == entity.name.lower() for s in suggestions):
                suggestions.append(entity)

        return suggestions


@router.get("", response_model=list[Entity])
async def get_all_entities():
    """Get all entities."""
    try:
        session = await get_neo4j_session()
        async with session:
            result = await session.run(
                """
                MATCH (e:Entity)
                RETURN e
                ORDER BY e.name
                LIMIT 100
                """
            )

            entities = []
            async for record in result:
                e = record["e"]
                entities.append(
                    Entity(
                        id=e["id"],
                        name=e["name"],
                        type=e.get("type", "concept"),
                    )
                )

            return entities
    except Exception:
        return []


@router.post("", response_model=Entity)
async def create_entity(entity: Entity):
    """Create a new entity."""
    session = await get_neo4j_session()
    async with session:
        # Generate ID if not provided
        entity_id = entity.id or str(uuid4())

        await session.run(
            """
            CREATE (e:Entity {
                id: $id,
                name: $name,
                type: $type
            })
            """,
            id=entity_id,
            name=entity.name,
            type=entity.type,
        )

    return Entity(id=entity_id, name=entity.name, type=entity.type)


@router.get("/{entity_id}", response_model=Entity)
async def get_entity(entity_id: str):
    """Get a single entity by ID."""
    from fastapi import HTTPException

    session = await get_neo4j_session()
    async with session:
        result = await session.run(
            """
            MATCH (e:Entity {id: $id})
            RETURN e
            """,
            id=entity_id,
        )

        record = await result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Entity not found")

        e = record["e"]
        return Entity(
            id=e["id"],
            name=e["name"],
            type=e.get("type", "concept"),
        )


@router.delete("/{entity_id}")
async def delete_entity(entity_id: str, force: bool = False):
    """Delete an entity by ID.

    Args:
        entity_id: The ID of the entity to delete
        force: If True, delete even if entity has relationships.
               If False (default), only delete orphan entities.
    """
    from fastapi import HTTPException

    session = await get_neo4j_session()
    async with session:
        # Check if entity exists
        result = await session.run(
            "MATCH (e:Entity {id: $id}) RETURN e",
            id=entity_id,
        )
        record = await result.single()
        if not record:
            raise HTTPException(status_code=404, detail="Entity not found")

        # Check for relationships if not forcing
        if not force:
            result = await session.run(
                """
                MATCH (e:Entity {id: $id})-[r]-()
                RETURN count(r) as rel_count
                """,
                id=entity_id,
            )
            record = await result.single()
            if record and record["rel_count"] > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Entity has {record['rel_count']} relationships. Use force=true to delete anyway.",
                )

        # Delete the entity (DETACH DELETE removes all relationships too)
        await session.run(
            "MATCH (e:Entity {id: $id}) DETACH DELETE e",
            id=entity_id,
        )

    return {"status": "deleted", "id": entity_id}
