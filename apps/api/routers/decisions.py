"""Decision endpoints with user isolation.

All decisions are isolated by user. Users can only access their own decisions.
Anonymous users can create and view decisions, but they are isolated under
the "anonymous" user_id and not shared across sessions.
"""

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j.exceptions import ClientError, DatabaseError, DriverError
from pydantic import BaseModel

from db.neo4j import get_neo4j_session
from models.schemas import Decision, DecisionCreate, Entity
from routers.auth import get_current_user_id
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


class ManualDecisionInput(BaseModel):
    trigger: str
    context: str
    options: list[str]
    decision: str
    rationale: str
    entities: list[str] = []  # Entity names to link (optional manual override)
    auto_extract: bool = True  # Whether to auto-extract entities


@router.get("", response_model=list[Decision])
async def get_decisions(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: str = Depends(get_current_user_id),
):
    """Get all decisions for the current user with pagination.

    Users can only see their own decisions. For backward compatibility,
    decisions without a user_id are visible to all users.
    """
    try:
        session = await get_neo4j_session()
        async with session:
            result = await session.run(
                """
                MATCH (d:DecisionTrace)
                WHERE d.user_id = $user_id OR d.user_id IS NULL
                OPTIONAL MATCH (d)-[:INVOLVES]->(e:Entity)
                WITH d, collect(e) as entities
                ORDER BY d.created_at DESC
                SKIP $offset
                LIMIT $limit
                RETURN d, entities
                """,
                user_id=user_id,
                offset=offset,
                limit=limit,
            )

            decisions = []
            async for record in result:
                d = record["d"]
                entities = record["entities"]

                decision = Decision(
                    id=d["id"],
                    trigger=d.get("trigger", ""),
                    context=d.get("context", ""),
                    options=d.get("options", []),
                    decision=d.get("decision", ""),
                    rationale=d.get("rationale", ""),
                    confidence=d.get("confidence", 0.0),
                    created_at=d.get("created_at", ""),
                    entities=[
                        Entity(
                            id=e["id"],
                            name=e["name"],
                            type=e.get("type", "concept"),
                        )
                        for e in entities
                        if e
                    ],
                    source=d.get("source", "unknown"),
                )
                decisions.append(decision)

            return decisions
    except DriverError as e:
        logger.error(f"Database connection error: {e}")
        raise HTTPException(status_code=503, detail="Database unavailable")
    except (ClientError, DatabaseError) as e:
        logger.error(f"Error fetching decisions: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch decisions")


@router.delete("/{decision_id}")
async def delete_decision(
    decision_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Delete a decision by ID.

    Users can only delete their own decisions.
    This removes the decision and all its relationships,
    but preserves the entities it was linked to.
    """
    session = await get_neo4j_session()
    async with session:
        # Check if decision exists AND belongs to the user
        result = await session.run(
            """
            MATCH (d:DecisionTrace {id: $id})
            WHERE d.user_id = $user_id OR d.user_id IS NULL
            RETURN d
            """,
            id=decision_id,
            user_id=user_id,
        )
        record = await result.single()
        if not record:
            # Don't reveal if decision exists but belongs to another user
            raise HTTPException(status_code=404, detail="Decision not found")

        # Delete the decision (DETACH DELETE removes relationships but keeps entities)
        await session.run(
            """
            MATCH (d:DecisionTrace {id: $id})
            WHERE d.user_id = $user_id OR d.user_id IS NULL
            DETACH DELETE d
            """,
            id=decision_id,
            user_id=user_id,
        )

    logger.info(f"Deleted decision {decision_id} for user {user_id}")
    return {"status": "deleted", "id": decision_id}


@router.get("/{decision_id}", response_model=Decision)
async def get_decision(
    decision_id: str,
    user_id: str = Depends(get_current_user_id),
):
    """Get a single decision by ID.

    Users can only access their own decisions.
    """
    session = await get_neo4j_session()
    async with session:
        result = await session.run(
            """
            MATCH (d:DecisionTrace {id: $id})
            WHERE d.user_id = $user_id OR d.user_id IS NULL
            OPTIONAL MATCH (d)-[:INVOLVES]->(e:Entity)
            WITH d, collect(e) as entities
            RETURN d, entities
            """,
            id=decision_id,
            user_id=user_id,
        )

        record = await result.single()
        if not record:
            # Don't reveal if decision exists but belongs to another user
            raise HTTPException(status_code=404, detail="Decision not found")

        d = record["d"]
        entities = record["entities"]

        return Decision(
            id=d["id"],
            trigger=d.get("trigger", ""),
            context=d.get("context", ""),
            options=d.get("options", []),
            decision=d.get("decision", ""),
            rationale=d.get("rationale", ""),
            confidence=d.get("confidence", 0.0),
            created_at=d.get("created_at", ""),
            entities=[
                Entity(
                    id=e["id"],
                    name=e["name"],
                    type=e.get("type", "concept"),
                )
                for e in entities
                if e
            ],
            source=d.get("source", "unknown"),
        )


@router.post("", response_model=Decision)
async def create_decision(
    input: ManualDecisionInput,
    user_id: str = Depends(get_current_user_id),
):
    """Create a decision with automatic entity extraction.

    The decision is linked to the current user for multi-tenant isolation.

    Uses the enhanced extractor with:
    - Few-shot CoT prompts for better entity extraction
    - Entity resolution to prevent duplicates
    - Automatic embedding generation
    - Relationship extraction between entities
    """
    from services.extractor import get_extractor

    # Create DecisionCreate object
    decision_create = DecisionCreate(
        trigger=input.trigger,
        context=input.context,
        options=input.options,
        decision=input.decision,
        rationale=input.rationale,
        source="manual",
    )

    if input.auto_extract:
        # Use the enhanced extractor for automatic entity extraction
        extractor = get_extractor()
        decision_id = await extractor.save_decision(
            decision_create, source="manual", user_id=user_id
        )
    else:
        # Manual creation without extraction
        decision_id = str(uuid4())
        created_at = datetime.now(UTC).isoformat()

        session = await get_neo4j_session()
        async with session:
            await session.run(
                """
                CREATE (d:DecisionTrace {
                    id: $id,
                    trigger: $trigger,
                    context: $context,
                    options: $options,
                    decision: $decision,
                    rationale: $rationale,
                    confidence: 1.0,
                    created_at: $created_at,
                    source: 'manual',
                    user_id: $user_id
                })
                """,
                id=decision_id,
                trigger=input.trigger,
                context=input.context,
                options=input.options,
                decision=input.decision,
                rationale=input.rationale,
                created_at=created_at,
                user_id=user_id,
            )

            # Create and link manually specified entities
            for entity_name in input.entities:
                if entity_name.strip():
                    entity_id = str(uuid4())
                    await session.run(
                        """
                        MERGE (e:Entity {name: $name})
                        ON CREATE SET e.id = $id, e.type = 'concept'
                        WITH e
                        MATCH (d:DecisionTrace {id: $decision_id})
                        MERGE (d)-[:INVOLVES]->(e)
                        """,
                        id=entity_id,
                        name=entity_name.strip(),
                        decision_id=decision_id,
                    )

    logger.info(f"Created decision {decision_id} for user {user_id}")

    # Fetch and return the created decision with its entities
    session = await get_neo4j_session()
    async with session:
        result = await session.run(
            """
            MATCH (d:DecisionTrace {id: $id})
            OPTIONAL MATCH (d)-[:INVOLVES]->(e:Entity)
            WITH d, collect(e) as entities
            RETURN d, entities
            """,
            id=decision_id,
        )

        record = await result.single()
        d = record["d"]
        entities = record["entities"]

        return Decision(
            id=d["id"],
            trigger=d.get("trigger", ""),
            context=d.get("context", ""),
            options=d.get("options", []),
            decision=d.get("decision", ""),
            rationale=d.get("rationale", ""),
            confidence=d.get("confidence", 0.0),
            created_at=d.get("created_at", ""),
            entities=[
                Entity(
                    id=e["id"],
                    name=e["name"],
                    type=e.get("type", "concept"),
                )
                for e in entities
                if e
            ],
            source=d.get("source", "unknown"),
        )
