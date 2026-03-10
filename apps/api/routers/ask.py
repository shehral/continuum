"""Ask router — SSE streaming endpoint for GraphRAG Q&A.

Provides a GET /api/ask endpoint that:
1. Retrieves relevant context from the knowledge graph via hybrid search
2. Streams an LLM-generated answer as Server-Sent Events (SSE)
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse

from routers.auth import get_current_user_id
from services.graph_rag import get_graph_rag_service
from services.llm import get_llm_client
from utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()

SYSTEM_PROMPT = """You are Continuum, a knowledge graph assistant. Answer the user's question using ONLY the provided graph context below. Be concise and specific.

Rules:
- Base your answer strictly on the provided context
- Reference specific decisions, entities, and relationships from the context
- If the context doesn't contain enough information, say "I don't have enough information in the knowledge graph to answer that"
- Do not make up information not present in the context
- Use markdown formatting for readability

## Knowledge Graph Context
{context}"""


def _sse_event(event: str, data: dict) -> str:
    """Format a Server-Sent Event."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get("")
async def ask(
    q: str = Query(..., min_length=3, description="The question to ask"),
    depth: int = Query(default=2, ge=1, le=3, description="Graph traversal depth"),
    top_k: int = Query(default=5, ge=1, le=10, description="Number of seed nodes"),
    user_id: str = Depends(get_current_user_id),
):
    """Ask a question and receive a streamed answer grounded in the knowledge graph."""

    async def event_stream():
        try:
            # Step 1: Retrieve context from the knowledge graph
            graph_rag = get_graph_rag_service()
            subgraph, context_text = await graph_rag.retrieve_context(
                query=q,
                user_id=user_id,
                top_k=top_k,
                depth=depth,
            )

            # Send context event with the retrieved subgraph
            seed_ids = [n.get("id") for n in subgraph.get("nodes", []) if n.get("id")]
            yield _sse_event("context", {
                "nodes": subgraph.get("nodes", []),
                "edges": subgraph.get("edges", []),
                "seed_ids": seed_ids,
            })

            # Step 2: If no context, send a direct "no info" message
            if not context_text:
                no_info_msg = (
                    "I don't have enough information in the knowledge graph "
                    "to answer that question."
                )
                yield _sse_event("token", {"text": no_info_msg})
                yield _sse_event("done", {"token_count": len(no_info_msg.split())})
                return

            # Step 3: Stream LLM response
            system_prompt = SYSTEM_PROMPT.format(context=context_text)
            llm = get_llm_client()
            token_count = 0

            async for chunk in llm.generate_stream(
                prompt=q,
                system_prompt=system_prompt,
                temperature=0.3,
                max_tokens=2048,
                user_id=user_id,
                sanitize_input=False,
            ):
                token_count += 1
                yield _sse_event("token", {"text": chunk})

            yield _sse_event("done", {"token_count": token_count})

        except Exception as e:
            logger.exception(f"Error in /api/ask stream: {e}")
            yield _sse_event("error", {"detail": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
