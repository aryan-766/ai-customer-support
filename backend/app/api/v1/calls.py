"""Calls REST API — start, end, get transcript, list calls."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from typing import Optional
import structlog

from app.core.database import get_db
from app.core.cache import redis_manager
from app.models import Call, Customer

router = APIRouter(prefix="/calls")
logger = structlog.get_logger(__name__)


class StartCallRequest(BaseModel):
    customer_mobile: Optional[str] = None
    channel: str = "phone"


class StartCallResponse(BaseModel):
    call_id: str
    session_id: str
    status: str
    ws_url: str


@router.post("/start", response_model=StartCallResponse)
async def start_call(body: StartCallRequest, db: AsyncSession = Depends(get_db)):
    """Start a new call session. Returns call_id and WebSocket URL."""
    call_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())

    # Create call record
    call = Call(id=call_id, channel=body.channel, status="active")

    # Link customer if mobile provided
    if body.customer_mobile:
        result = await db.execute(
            select(Customer).where(Customer.mobile == body.customer_mobile)
        )
        customer = result.scalar_one_or_none()
        if customer:
            call.customer_id = customer.id

    db.add(call)
    await db.commit()

    logger.info("call_started", call_id=call_id, channel=body.channel)

    return StartCallResponse(
        call_id=call_id,
        session_id=session_id,
        status="active",
        ws_url=f"ws://localhost:8000/ws/call/{call_id}",
    )


@router.get("/{call_id}")
async def get_call(call_id: str, db: AsyncSession = Depends(get_db)):
    """Get call details including intent, sentiment, routing path."""
    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    return {
        "call_id": str(call.id),
        "status": call.status,
        "channel": call.channel,
        "language": call.language,
        "intent": call.detected_intent,
        "sentiment": call.sentiment,
        "priority": call.priority,
        "resolved": call.resolved,
        "started_at": call.started_at.isoformat() if call.started_at else None,
        "ended_at": call.ended_at.isoformat() if call.ended_at else None,
        "routing_path": call.routing_path or [],
        "zoho_ticket_id": call.zoho_ticket_id,
    }


@router.get("/{call_id}/transcript")
async def get_transcript(call_id: str):
    """Get full transcript from Redis (live) or PostgreSQL (archived)."""
    # Try Redis first (live call)
    transcript = await redis_manager.get_transcript(call_id)
    if transcript:
        return {"call_id": call_id, "source": "live", "transcript": transcript}

    # Fall back to DB
    async with get_db() as db:
        result = await db.execute(select(Call).where(Call.id == call_id))
        call = result.scalar_one_or_none()
        if call:
            return {"call_id": call_id, "source": "archived", "transcript": call.transcript or []}

    raise HTTPException(status_code=404, detail="Call not found")


@router.get("/{call_id}/summary")
async def get_summary(call_id: str, db: AsyncSession = Depends(get_db)):
    """Get AI-generated call summary."""
    # Check Redis first
    state = await redis_manager.get_call_state(call_id)
    if state and state.get("call_summary"):
        return {"call_id": call_id, "summary": state["call_summary"]}

    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    return {"call_id": call_id, "summary": {"resolution": call.ai_summary}}


@router.post("/{call_id}/end")
async def end_call(call_id: str, db: AsyncSession = Depends(get_db)):
    """End a call and trigger post-call automation."""
    from datetime import datetime, timezone
    from sqlalchemy import update

    await db.execute(
        update(Call)
        .where(Call.id == call_id)
        .values(status="completed", ended_at=datetime.now(timezone.utc))
    )
    await db.commit()

    # Publish end event
    await redis_manager.publish(f"transcript.{call_id}", {"type": "call_ended"})

    logger.info("call_ended", call_id=call_id)
    return {"call_id": call_id, "status": "completed"}


@router.get("")
async def list_calls(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, le=100),
    status: Optional[str] = None,
    intent: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List calls with pagination and filtering."""
    query = select(Call).order_by(desc(Call.started_at))

    if status:
        query = query.where(Call.status == status)
    if intent:
        query = query.where(Call.detected_intent == intent)

    query = query.offset((page - 1) * limit).limit(limit)
    result = await db.execute(query)
    calls = result.scalars().all()

    return {
        "page": page,
        "limit": limit,
        "calls": [
            {
                "call_id": str(c.id),
                "status": c.status,
                "intent": c.detected_intent,
                "sentiment": c.sentiment,
                "priority": c.priority,
                "resolved": c.resolved,
                "started_at": c.started_at.isoformat() if c.started_at else None,
            }
            for c in calls
        ],
    }
