"""Ingestion endpoints with proper error handling (SEC-014).

SEC-014: Replaced silent exception handling with specific exception handling and logging.
SD-024: Cache invalidation added after ingestion completes.
"""

from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.postgres import get_db
from models.schemas import IngestionResult, IngestionStatus
from services.extractor import DecisionExtractor
from services.file_watcher import get_file_watcher
from services.parser import ClaudeLogParser
from utils.cache import invalidate_user_caches
from utils.logging import get_logger

logger = get_logger(__name__)

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


class FileInfo(BaseModel):
    """Information about a single JSONL file."""
    file_path: str
    project_name: str
    project_dir: str
    conversation_count: int
    size_bytes: int
    last_modified: str


class ImportSelectedRequest(BaseModel):
    """Request to import selected files to a target project."""
    file_paths: list[str]
    target_project: Optional[str] = None


@router.get("/projects", response_model=list[ProjectInfo])
async def list_available_projects():
    """List all Claude Code projects available for ingestion.

    Returns project directories with conversation file counts.
    Use this to see what projects are available before filtering.
    """
    settings = get_settings()
    parser = ClaudeLogParser(settings.claude_logs_path)
    return parser.get_available_projects()


@router.get("/files", response_model=list[FileInfo])
async def list_files(
    project: Optional[str] = Query(
        None, description="Only include this project (partial match)"
    ),
):
    """List all Claude Code log files with metadata for selective import.

    Returns file information including path, project, conversation count, size, and timestamp.
    Use this to build a file browser UI for selective import.
    """
    settings = get_settings()
    parser = ClaudeLogParser(settings.claude_logs_path)

    if not parser.logs_path.exists():
        return []

    files_info = []

    # Find all JSONL files
    for file_path in parser.logs_path.glob("**/*.jsonl"):
        # Skip subagent files
        if "subagents" in str(file_path):
            continue

        project_name = parser._extract_project_name(file_path)
        project_dir = file_path.parent.name

        # Apply project filter if provided
        if project and project.lower() not in project_dir.lower():
            continue

        # Get file stats
        stat = file_path.stat()

        # Count conversations in file
        conversations = parser._parse_jsonl_file(file_path)

        files_info.append(
            FileInfo(
                file_path=str(file_path),
                project_name=project_name,
                project_dir=project_dir,
                conversation_count=len(conversations),
                size_bytes=stat.st_size,
                last_modified=datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
            )
        )

    # Sort by last modified (newest first)
    files_info.sort(key=lambda x: x.last_modified, reverse=True)

    return files_info


@router.get("/preview", response_model=PreviewResponse)
async def preview_ingestion(
    project: Optional[str] = Query(
        None, description="Only include this project (partial match)"
    ),
    exclude: Optional[str] = Query(
        None, description="Comma-separated list of projects to exclude"
    ),
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
    project: Optional[str] = Query(
        None, description="Only include this project (partial match)"
    ),
    exclude: Optional[str] = Query(
        None, description="Comma-separated list of projects to exclude"
    ),
    db: AsyncSession = Depends(get_db),
):
    """Trigger ingestion of Claude Code logs with optional filtering.

    Examples:
    - /api/ingest/trigger?project=continuum - Only import from continuum project
    - /api/ingest/trigger?exclude=CS5330,CS6120 - Exclude coursework
    - /api/ingest/trigger?project=continuum&exclude=test - Continuum except test files

    SEC-014: Proper error handling with specific exceptions and error details.
    """
    settings = get_settings()
    parser = ClaudeLogParser(settings.claude_logs_path)
    extractor = DecisionExtractor()

    exclude_list = [e.strip() for e in exclude.split(",")] if exclude else []

    files_processed = 0
    decisions_extracted = 0
    errors: list[str] = []

    try:
        async for file_path, conversations in parser.parse_all_logs(
            project_filter=project,
            exclude_projects=exclude_list,
        ):
            try:
                for conversation in conversations:
                    # Extract decisions from conversation
                    try:
                        decisions = await extractor.extract_decisions(conversation)
                        decisions_extracted += len(decisions)

                        # Save decisions to Neo4j with source tag and project name
                        for decision in decisions:
                            try:
                                await extractor.save_decision(
                                    decision,
                                    source="claude_logs",
                                    project_name=conversation.project_name if conversation else None
                                )
                            except Exception as save_error:
                                logger.error(
                                    f"Failed to save decision: {type(save_error).__name__}: {save_error}",
                                    exc_info=True,
                                )
                                errors.append(f"save_decision:{file_path}")
                    except Exception as extract_error:
                        logger.error(
                            f"Failed to extract decisions from {file_path}: "
                            f"{type(extract_error).__name__}: {extract_error}",
                            exc_info=True,
                        )
                        errors.append(f"extract:{file_path}")

                files_processed += 1
            except Exception as file_error:
                logger.error(
                    f"Error processing file {file_path}: {type(file_error).__name__}: {file_error}",
                    exc_info=True,
                )
                errors.append(f"file:{file_path}")

        ingestion_state["files_processed"] += files_processed
        ingestion_state["last_run"] = datetime.now(UTC)

        # Build status message
        if errors:
            status = f"completed with {len(errors)} errors"
            logger.warning(f"Ingestion completed with errors: {errors}")
        else:
            status = "completed"

        # SD-024: Invalidate caches since data changed
        # Using "anonymous" as default user since ingestion doesn't have auth context yet
        await invalidate_user_caches("anonymous")

        return IngestionResult(
            status=status,
            processed=files_processed,
            decisions_extracted=decisions_extracted,
        )
    except FileNotFoundError as e:
        logger.error(f"Ingestion path not found: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Claude logs path not found: {settings.claude_logs_path}",
        )
    except PermissionError as e:
        logger.error(f"Permission denied accessing logs: {e}")
        raise HTTPException(
            status_code=403, detail="Permission denied accessing Claude logs directory"
        )
    except Exception as e:
        logger.error(
            f"Unexpected error during ingestion: {type(e).__name__}: {e}", exc_info=True
        )
        return IngestionResult(
            status=f"error: {type(e).__name__}",
            processed=files_processed,
            decisions_extracted=decisions_extracted,
        )


@router.post("/import-selected", response_model=IngestionResult)
async def import_selected_files(
    request: ImportSelectedRequest,
    db: AsyncSession = Depends(get_db),
):
    """Import only selected files with optional target project assignment.

    This endpoint allows fine-grained control over which files to import
    and which project to assign them to. Useful for organizing imported
    decisions into specific projects.

    Examples:
    - Import specific files to a project: {"file_paths": [...], "target_project": "continuum"}
    - Import files with original project names: {"file_paths": [...], "target_project": null}
    """
    from pathlib import Path

    settings = get_settings()
    parser = ClaudeLogParser(settings.claude_logs_path)
    extractor = DecisionExtractor()

    files_processed = 0
    decisions_extracted = 0
    errors: list[str] = []

    try:
        for file_path_str in request.file_paths:
            file_path = Path(file_path_str)

            # Validate file exists and is within logs directory
            if not file_path.exists():
                errors.append(f"not_found:{file_path_str}")
                continue

            # Security: Ensure file is within logs directory (prevent path traversal)
            try:
                file_path.resolve().relative_to(parser.logs_path.resolve())
            except ValueError:
                logger.warning(f"Attempted to import file outside logs directory: {file_path}")
                errors.append(f"invalid_path:{file_path_str}")
                continue

            try:
                # Parse the file
                conversations = parser._parse_jsonl_file(file_path)

                for conversation in conversations:
                    try:
                        # Extract decisions from conversation
                        decisions = await extractor.extract_decisions(conversation)
                        decisions_extracted += len(decisions)

                        # Save decisions with target project or original project
                        project_name = request.target_project or conversation.project_name

                        for decision in decisions:
                            try:
                                await extractor.save_decision(
                                    decision,
                                    source="claude_logs",
                                    project_name=project_name,
                                )
                            except Exception as save_error:
                                logger.error(
                                    f"Failed to save decision: {type(save_error).__name__}: {save_error}",
                                    exc_info=True,
                                )
                                errors.append(f"save_decision:{file_path}")
                    except Exception as extract_error:
                        logger.error(
                            f"Failed to extract decisions from {file_path}: "
                            f"{type(extract_error).__name__}: {extract_error}",
                            exc_info=True,
                        )
                        errors.append(f"extract:{file_path}")

                files_processed += 1
            except Exception as file_error:
                logger.error(
                    f"Error processing file {file_path}: {type(file_error).__name__}: {file_error}",
                    exc_info=True,
                )
                errors.append(f"file:{file_path}")

        ingestion_state["files_processed"] += files_processed
        ingestion_state["last_run"] = datetime.now(UTC)

        # Build status message
        if errors:
            status = f"completed with {len(errors)} errors"
            logger.warning(f"Selective import completed with errors: {errors}")
        else:
            status = "completed"

        # Invalidate caches since data changed
        await invalidate_user_caches("anonymous")

        return IngestionResult(
            status=status,
            processed=files_processed,
            decisions_extracted=decisions_extracted,
        )
    except Exception as e:
        logger.error(
            f"Unexpected error during selective import: {type(e).__name__}: {e}",
            exc_info=True,
        )
        return IngestionResult(
            status=f"error: {type(e).__name__}",
            processed=files_processed,
            decisions_extracted=decisions_extracted,
        )


async def process_changed_file(file_path: str) -> None:
    """Process a changed Claude log file.

    This is called by the file watcher when a file changes.

    SEC-014: Proper error handling with specific exceptions and logging.
    """
    logger.info(f"Processing changed file: {file_path}")

    try:
        parser = ClaudeLogParser("")
        conversations = await parser.parse_file(file_path)

        extractor = DecisionExtractor()
        decisions_extracted = 0

        for conversation in conversations:
            try:
                decisions = await extractor.extract_decisions(conversation)
                decisions_extracted += len(decisions)

                for decision in decisions:
                    try:
                        await extractor.save_decision(
                            decision,
                            source="claude_logs",
                            project_name=conversation.project_name
                        )
                    except Exception as save_error:
                        logger.error(
                            f"Failed to save decision from {file_path}: "
                            f"{type(save_error).__name__}: {save_error}",
                            exc_info=True,
                        )
            except Exception as extract_error:
                logger.error(
                    f"Failed to extract decisions from {file_path}: "
                    f"{type(extract_error).__name__}: {extract_error}",
                    exc_info=True,
                )

        ingestion_state["files_processed"] += 1
        ingestion_state["last_run"] = datetime.now(UTC)
        logger.info(f"Processed {decisions_extracted} decisions from {file_path}")

    except FileNotFoundError:
        logger.warning(f"File not found (may have been deleted): {file_path}")
    except PermissionError as e:
        logger.error(f"Permission denied reading file {file_path}: {e}")
    except Exception as e:
        logger.error(
            f"Error processing file {file_path}: {type(e).__name__}: {e}", exc_info=True
        )


@router.post("/watch/start")
async def start_watching(background_tasks: BackgroundTasks):
    """Start watching Claude Code logs for new conversations.

    Uses watchdog to monitor the logs directory for new or modified
    JSONL files. When changes are detected, decisions are automatically
    extracted and saved to the knowledge graph.
    """
    settings = get_settings()
    watcher = get_file_watcher()

    if watcher.is_running:
        return {"status": "already watching", "path": settings.claude_logs_path}

    success = watcher.start(
        logs_path=settings.claude_logs_path,
        on_change=lambda path: background_tasks.add_task(process_changed_file, path),
    )

    if success:
        ingestion_state["is_watching"] = True
        return {"status": "watching started", "path": settings.claude_logs_path}
    else:
        return {"status": "failed to start", "error": "Could not start file watcher"}


@router.post("/watch/stop")
async def stop_watching():
    """Stop watching Claude Code logs."""
    watcher = get_file_watcher()

    if not watcher.is_running:
        return {"status": "not watching"}

    watcher.stop()
    ingestion_state["is_watching"] = False
    return {"status": "watching stopped"}
