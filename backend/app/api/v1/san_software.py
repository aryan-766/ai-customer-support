"""San Software SIP Integration."""

import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import JSONResponse
import structlog

from app.core.database import get_db
from app.models import Call

router = APIRouter(prefix="/sip/san-software")
logger = structlog.get_logger(__name__)


@router.post("/incoming")
async def handle_incoming_call(request: Request, db: AsyncSession = Depends(get_db)):
    """
    Handle incoming call webhook from Asterisk (bridging San Software SIP).
    Asterisk intercepts the SIP call and asks this backend for the WebSocket URL.
    """
    # Parse payload (assuming JSON or form data based on standard SIP webhooks)
    try:
        body = await request.json()
    except:
        body = {}
        
    caller_id = body.get("caller_id") or body.get("From") or "unknown"
    call_uuid = uuid.uuid4()
    
    # Create call record
    call = Call(id=call_uuid, channel="phone", status="active")
    db.add(call)
    await db.commit()

    call_id_str = str(call_uuid)
    logger.info("san_software_call_started", call_id=call_id_str, caller_id=caller_id)
    
    ws_url = f"ws://localhost:8000/ws/call/{call_id_str}"
    
    # Return response for Asterisk to dial or bridge via AudioSocket/External Media.
    return JSONResponse({
        "status": "success",
        "action": "bridge_websocket",
        "websocket_url": ws_url,
        "call_id": call_id_str
    })
