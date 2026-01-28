from fastapi import APIRouter

from db.neo4j import get_neo4j_session
from models.schemas import DashboardStats, Decision, Entity

router = APIRouter()


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats():
    """Get dashboard statistics."""
    try:
        session = await get_neo4j_session()
        async with session:
            # Count decisions
            result = await session.run("MATCH (d:DecisionTrace) RETURN count(d) as count")
            record = await result.single()
            total_decisions = record["count"] if record else 0

            # Count entities
            result = await session.run("MATCH (e:Entity) RETURN count(e) as count")
            record = await result.single()
            total_entities = record["count"] if record else 0

            # Get recent decisions
            result = await session.run(
                """
                MATCH (d:DecisionTrace)
                OPTIONAL MATCH (d)-[:INVOLVES]->(e:Entity)
                WITH d, collect(e) as entities
                ORDER BY d.created_at DESC
                LIMIT 6
                RETURN d, entities
                """
            )

            recent_decisions = []
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
                )
                recent_decisions.append(decision)

            return DashboardStats(
                total_decisions=total_decisions,
                total_entities=total_entities,
                total_sessions=0,  # TODO: Get from PostgreSQL
                recent_decisions=recent_decisions,
            )
    except Exception:
        # Return empty stats if databases are not available
        return DashboardStats(
            total_decisions=0,
            total_entities=0,
            total_sessions=0,
            recent_decisions=[],
        )
