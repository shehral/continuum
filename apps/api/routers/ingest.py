from datetime import datetime
from pathlib import Path
from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from db.postgres import get_db
from services.parser import ClaudeLogParser
from services.extractor import DecisionExtractor
from models.schemas import IngestionStatus, IngestionResult

router = APIRouter()

# Track ingestion state
ingestion_state = {
    "is_watching": False,
    "last_run": None,
    "files_processed": 0,
}


async def run_ingestion(db: AsyncSession):
    """Background task to run ingestion."""
    settings = get_settings()
    parser = ClaudeLogParser(settings.claude_logs_path)
    extractor = DecisionExtractor()

    files_processed = 0
    decisions_extracted = 0

    async for file_path, conversations in parser.parse_all_logs():
        for conversation in conversations:
            # Extract decisions from conversation
            decisions = await extractor.extract_decisions(conversation)
            decisions_extracted += len(decisions)

            # Save decisions to Neo4j
            for decision in decisions:
                await extractor.save_decision(decision)

        files_processed += 1

    ingestion_state["files_processed"] += files_processed
    ingestion_state["last_run"] = datetime.utcnow()

    return files_processed, decisions_extracted


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
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a one-time ingestion of Claude Code logs."""
    settings = get_settings()
    parser = ClaudeLogParser(settings.claude_logs_path)
    extractor = DecisionExtractor()

    files_processed = 0
    decisions_extracted = 0

    try:
        async for file_path, conversations in parser.parse_all_logs():
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
