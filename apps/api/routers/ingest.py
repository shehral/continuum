from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.postgres import get_db
from models.schemas import IngestionResult, IngestionStatus
from services.extractor import DecisionExtractor
from services.parser import ClaudeLogParser

router = APIRouter()

# Track ingestion state
ingestion_state = {
    "is_watching": False,
    "last_run": None,
    "files_processed": 0,
}


class ProjectInfo(BaseModel):
    dir: str
    name: str
    files: int
    path: str


class ConversationPreview(BaseModel):
    file: str
    project: str
    messages: int
    preview: str


class PreviewResponse(BaseModel):
    total_conversations: int
    previews: list[ConversationPreview]
    project_filter: Optional[str]
    exclude_projects: list[str]


@router.get("/projects", response_model=list[ProjectInfo])
async def list_available_projects():
    """List all Claude Code projects available for ingestion.

    Returns project directories with conversation file counts.
    Use this to see what projects are available before filtering.
    """
    settings = get_settings()
    parser = ClaudeLogParser(settings.claude_logs_path)
    return parser.get_available_projects()


@router.get("/preview", response_model=PreviewResponse)
async def preview_ingestion(
    project: Optional[str] = Query(None, description="Only include this project (partial match)"),
    exclude: Optional[str] = Query(None, description="Comma-separated list of projects to exclude"),
    limit: int = Query(10, ge=1, le=50, description="Max conversations to preview"),
):
    """Preview what would be imported without actually importing.

    Use this to verify your filters before running ingestion.
    """
    settings = get_settings()
    parser = ClaudeLogParser(settings.claude_logs_path)

    exclude_list = [e.strip() for e in exclude.split(",")] if exclude else []

    previews = await parser.preview_logs(
        project_filter=project,
        exclude_projects=exclude_list,
        max_conversations=limit,
    )

    return PreviewResponse(
        total_conversations=len(previews),
        previews=[ConversationPreview(**p) for p in previews],
        project_filter=project,
        exclude_projects=exclude_list,
    )


@router.get("/status", response_model=IngestionStatus)
async def get_ingestion_status():
    """Get the current ingestion status."""
    return IngestionStatus(
        is_watching=ingestion_state["is_watching"],
        last_run=ingestion_state["last_run"],
        files_processed=ingestion_state["files_processed"],
    )


@router.post("/trigger", response_model=IngestionResult)
async def trigger_ingestion(
    project: Optional[str] = Query(None, description="Only include this project (partial match)"),
    exclude: Optional[str] = Query(None, description="Comma-separated list of projects to exclude"),
    db: AsyncSession = Depends(get_db),
):
    """Trigger ingestion of Claude Code logs with optional filtering.

    Examples:
    - /api/ingest/trigger?project=continuum - Only import from continuum project
    - /api/ingest/trigger?exclude=CS5330,CS6120 - Exclude coursework
    - /api/ingest/trigger?project=continuum&exclude=test - Continuum except test files
    """
    settings = get_settings()
    parser = ClaudeLogParser(settings.claude_logs_path)
    extractor = DecisionExtractor()

    exclude_list = [e.strip() for e in exclude.split(",")] if exclude else []

    files_processed = 0
    decisions_extracted = 0

    try:
        async for file_path, conversations in parser.parse_all_logs(
            project_filter=project,
            exclude_projects=exclude_list,
        ):
            for conversation in conversations:
                # Extract decisions from conversation
                decisions = await extractor.extract_decisions(conversation)
                decisions_extracted += len(decisions)

                # Save decisions to Neo4j with source tag
                for decision in decisions:
                    await extractor.save_decision(decision, source="claude_logs")

            files_processed += 1

        ingestion_state["files_processed"] += files_processed
        ingestion_state["last_run"] = datetime.utcnow()

        return IngestionResult(
            status="completed",
            processed=files_processed,
            decisions_extracted=decisions_extracted,
        )
    except Exception as e:
        return IngestionResult(
            status=f"error: {str(e)}",
            processed=files_processed,
            decisions_extracted=decisions_extracted,
        )


@router.post("/watch/start")
async def start_watching():
    """Start watching Claude Code logs for new conversations."""
    ingestion_state["is_watching"] = True
    # TODO: Implement file watcher using watchdog or similar
    return {"status": "watching started"}


@router.post("/watch/stop")
async def stop_watching():
    """Stop watching Claude Code logs."""
    ingestion_state["is_watching"] = False
    return {"status": "watching stopped"}
