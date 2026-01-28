from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.postgres import get_db
from models.postgres import CaptureSession, CaptureMessage, SessionStatus
from models.schemas import (
    CaptureSession as CaptureSessionSchema,
    CaptureMessage as CaptureMessageSchema,
    Entity,
)
from agents.interview import InterviewAgent

router = APIRouter()


@router.post("/sessions", response_model=CaptureSessionSchema)
async def start_capture_session(db: AsyncSession = Depends(get_db)):
    """Start a new capture session."""
    session = CaptureSession(
        id=str(uuid4()),
        user_id="anonymous",  # TODO: Get from auth
        status=SessionStatus.ACTIVE,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return CaptureSessionSchema(
        id=session.id,
        status=session.status.value,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[],
    )


@router.get("/sessions/{session_id}", response_model=CaptureSessionSchema)
async def get_capture_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Get a capture session by ID."""
    result = await db.execute(
        select(CaptureSession).where(CaptureSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get messages
    result = await db.execute(
        select(CaptureMessage)
        .where(CaptureMessage.session_id == session_id)
        .order_by(CaptureMessage.timestamp)
    )
    messages = result.scalars().all()

    return CaptureSessionSchema(
        id=session.id,
        status=session.status.value,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[
            CaptureMessageSchema(
                id=m.id,
                role=m.role,
                content=m.content,
                timestamp=m.timestamp,
                extracted_entities=[
                    Entity(**e) for e in (m.extracted_entities or [])
                ],
            )
            for m in messages
        ],
    )


@router.post("/sessions/{session_id}/messages", response_model=CaptureMessageSchema)
async def send_capture_message(
    session_id: str,
    content: dict,
    db: AsyncSession = Depends(get_db),
):
    """Send a message in a capture session and get AI response."""
    # Verify session exists and is active
    result = await db.execute(
        select(CaptureSession).where(CaptureSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")

    # Save user message
    user_message = CaptureMessage(
        id=str(uuid4()),
        session_id=session_id,
        role="user",
        content=content.get("content", ""),
    )
    db.add(user_message)

    # Get conversation history
    result = await db.execute(
        select(CaptureMessage)
        .where(CaptureMessage.session_id == session_id)
        .order_by(CaptureMessage.timestamp)
    )
    history = result.scalars().all()

    # Generate AI response using interview agent
    interview_agent = InterviewAgent()
    response_content, extracted_entities = await interview_agent.process_message(
        user_message=content.get("content", ""),
        history=[{"role": m.role, "content": m.content} for m in history],
    )

    # Save AI response
    ai_message = CaptureMessage(
        id=str(uuid4()),
        session_id=session_id,
        role="assistant",
        content=response_content,
        extracted_entities=[e.model_dump() for e in extracted_entities],
    )
    db.add(ai_message)

    await db.commit()
    await db.refresh(ai_message)

    return CaptureMessageSchema(
        id=ai_message.id,
        role=ai_message.role,
        content=ai_message.content,
        timestamp=ai_message.timestamp,
        extracted_entities=extracted_entities,
    )


@router.post("/sessions/{session_id}/complete", response_model=CaptureSessionSchema)
async def complete_capture_session(session_id: str, db: AsyncSession = Depends(get_db)):
    """Complete a capture session and save the decision to the graph."""
    result = await db.execute(
        select(CaptureSession).where(CaptureSession.id == session_id)
    )
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status != SessionStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Session is not active")

    # Update session status
    session.status = SessionStatus.COMPLETED
    session.completed_at = datetime.utcnow()

    # Get all messages
    result = await db.execute(
        select(CaptureMessage)
        .where(CaptureMessage.session_id == session_id)
        .order_by(CaptureMessage.timestamp)
    )
    messages = result.scalars().all()

    # Extract decision from messages and save to Neo4j
    interview_agent = InterviewAgent()
    history = [{"role": m.role, "content": m.content} for m in messages]

    decision_data = await interview_agent.synthesize_decision(history)
    print(f"[Capture] Synthesized decision: {decision_data}")

    if decision_data and decision_data.get("trigger"):
        from services.extractor import DecisionExtractor
        from models.schemas import DecisionCreate

        extractor = DecisionExtractor()
        decision = DecisionCreate(
            trigger=decision_data.get("trigger", ""),
            context=decision_data.get("context", ""),
            options=decision_data.get("options", []),
            decision=decision_data.get("decision", ""),
            rationale=decision_data.get("rationale", ""),
            confidence=decision_data.get("confidence", 0.8),
            source="interview",  # Tag as human-captured via interview
        )
        decision_id = await extractor.save_decision(decision, source="interview")
        print(f"[Capture] Decision saved with ID: {decision_id} (source: interview)")
    else:
        print(f"[Capture] No valid decision to save - missing trigger or empty data")

    await db.commit()
    await db.refresh(session)

    return CaptureSessionSchema(
        id=session.id,
        status=session.status.value,
        created_at=session.created_at,
        updated_at=session.updated_at,
        messages=[
            CaptureMessageSchema(
                id=m.id,
                role=m.role,
                content=m.content,
                timestamp=m.timestamp,
                extracted_entities=[
                    Entity(**e) for e in (m.extracted_entities or [])
                ],
            )
            for m in messages
        ],
    )


@router.websocket("/sessions/{session_id}/ws")
async def capture_websocket(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time capture sessions."""
    await websocket.accept()

    interview_agent = InterviewAgent()
    history = []

    try:
        while True:
            data = await websocket.receive_json()
            user_message = data.get("content", "")

            # Stream response
            async for chunk, entities in interview_agent.stream_response(
                user_message, history
            ):
                await websocket.send_json(
                    {
                        "type": "chunk",
                        "content": chunk,
                        "entities": [e.model_dump() for e in entities],
                    }
                )

            # Send completion
            await websocket.send_json({"type": "complete"})

            # Update history
            history.append({"role": "user", "content": user_message})
            history.append({"role": "assistant", "content": chunk})

    except WebSocketDisconnect:
        pass
