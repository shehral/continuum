"""Knowledge graph tools for Strands interview agent.

These @tool functions give the interview agent access to the knowledge graph
during conversations, enabling context-aware interviewing.
"""

from strands import tool
from strands.tools.decorator import ToolContext

from utils.logging import get_logger

logger = get_logger(__name__)


@tool(context=True)
async def check_prior_decisions(tool_context: ToolContext, topic: str) -> dict:
    """Check the knowledge graph for similar past decisions about a topic.

    Use this when the user mentions a technology, approach, or decision area
    that may have existing history. Returns similar decisions, contradictions,
    and abandoned patterns.

    Args:
        topic: The technology, approach, or decision area to check.

    Returns:
        Summary of related prior decisions from the knowledge graph.
    """
    user_id = tool_context.agent.state.get("user_id", "anonymous")

    try:
        from services.agent_context import AgentContextService

        service = AgentContextService(user_id=user_id)
        result = await service.check_prior_art(proposed_decision=topic)

        parts = []
        if result.similar_decisions:
            parts.append(f"Found {len(result.similar_decisions)} related decisions:")
            for d in result.similar_decisions[:3]:
                parts.append(f"  - {d.decision} (confidence: {d.confidence:.0%})")
                if d.rationale:
                    parts.append(f"    Rationale: {d.rationale[:100]}")

        if result.contradictions:
            parts.append(f"\nPotential contradictions ({len(result.contradictions)}):")
            for c in result.contradictions[:2]:
                parts.append(f"  - {c.decision}")

        if result.abandoned_patterns:
            parts.append(f"\nAbandoned approaches ({len(result.abandoned_patterns)}):")
            for a in result.abandoned_patterns[:2]:
                parts.append(f"  - {a.original_decision} → superseded by {a.superseding_decision}")

        if not parts:
            parts.append("No prior decisions found for this topic.")

        return {"status": "success", "content": [{"text": "\n".join(parts)}]}

    except Exception as e:
        logger.warning(f"check_prior_decisions failed: {e}")
        return {"status": "success", "content": [{"text": "Could not check prior decisions (knowledge graph unavailable)."}]}


@tool(context=True)
async def search_knowledge(tool_context: ToolContext, query: str) -> dict:
    """Search the knowledge graph for relevant context about a query.

    Use this to find entities, technologies, and decisions related to the
    user's current topic. Helpful for providing informed follow-up questions.

    Args:
        query: The search query (technology name, concept, or question).

    Returns:
        Relevant entities and decisions from the knowledge graph.
    """
    user_id = tool_context.agent.state.get("user_id", "anonymous")

    try:
        from services.agent_context import AgentContextService

        service = AgentContextService(user_id=user_id)
        result = await service.get_context(query=query, user_id=user_id)

        parts = []
        if result.decisions:
            parts.append(f"Related decisions ({len(result.decisions)}):")
            for d in result.decisions[:3]:
                parts.append(f"  - {d.decision}")

        if result.entities:
            parts.append(f"\nKnown entities ({len(result.entities)}):")
            for e in result.entities[:5]:
                parts.append(f"  - {e.name} ({e.type})")

        if not parts:
            parts.append("No relevant knowledge found.")

        return {"status": "success", "content": [{"text": "\n".join(parts)}]}

    except Exception as e:
        logger.warning(f"search_knowledge failed: {e}")
        return {"status": "success", "content": [{"text": "Could not search knowledge graph."}]}
