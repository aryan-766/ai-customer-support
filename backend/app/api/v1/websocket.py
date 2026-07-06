"""
WebSocket API — real-time audio streaming, transcript, agent assist.

WS /ws/call/{call_id}   ← receives binary PCM16 audio
                         → sends JSON events (transcript, agent response, etc.)

WS /ws/agent/{agent_id} ← human agent dashboard
                         → receives agent assist suggestions, customer context
"""

import asyncio
import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
import structlog

from app.agents.state import initial_state
from app.agents.graph import call_graph
from app.core.stt.faster_whisper import FasterWhisperSTT
from app.core.cache import redis_manager
from app.models import Call
from app.core.database import AsyncSessionLocal

router = APIRouter()
logger = structlog.get_logger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Customer Call WebSocket
# ─────────────────────────────────────────────────────────────────────────────

@router.websocket("/ws/call/{call_id}")
async def call_websocket(
    websocket: WebSocket,
    call_id: str,
    channel: str = Query(default="phone"),
):
    """
    Full duplex audio WebSocket:
    - Receives binary PCM16 audio frames from telephony gateway
    - Streams transcript chunks back via JSON events
    - Runs LangGraph agent graph
    - Sends AI TTS audio back
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    stt = FasterWhisperSTT()

    logger.info("call_ws_connected", call_id=call_id, session_id=session_id)

    # Initialize call state
    state = initial_state(call_id=call_id, session_id=session_id, channel=channel)

    # Initialize Zoho Desk ticket at start of call (before AI receptionist greets)
    from app.integrations.zoho_desk import ZohoDesk
    zoho = ZohoDesk()
    zoho_ticket_id = None
    try:
        zoho_ticket_id = await zoho.create_ticket(
            subject=f"Inbound Call - {call_id}",
            description="Call started. Customer authentication pending...",
            customer_email="caller@unknown.com",
            priority="medium",
            call_id=call_id,
        )
        if zoho_ticket_id:
            state["zoho_ticket_id"] = zoho_ticket_id
            logger.info("pre_call_zoho_ticket_created", call_id=call_id, ticket_id=zoho_ticket_id)
    except Exception as e:
        logger.error("pre_call_zoho_ticket_error", call_id=call_id, error=str(e))

    await redis_manager.save_call_state(call_id, state)

    # Save call to DB (including zoho_ticket_id)
    await _create_call_record(call_id, channel, zoho_ticket_id)

    # Send initial greeting immediately upon call connection
    try:
        response_text = "Welcome to Ambrane customer support. How can I help you today?"
        
        # Send greeting text event to websocket
        await websocket.send_text(json.dumps({
            "type": "agent_response",
            "text": response_text,
            "agent": "receptionist",
            "intent": None,
            "citations": [],
        }))
        
        # Save to Redis transcript
        await redis_manager.append_transcript(call_id, {
            "speaker": "receptionist",
            "text": response_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        # Publish to agent dashboard
        await redis_manager.publish(f"transcript.{call_id}", {
            "type": "transcript_chunk",
            "text": response_text,
            "speaker": "receptionist",
        })
        
        # Synthesize and send greeting audio
        from app.core.tts.factory import TTSFactory
        tts = TTSFactory.get_provider()
        async for audio_chunk in tts.synthesize_stream(response_text):
            await websocket.send_bytes(audio_chunk)
            
    except Exception as e:
        import traceback
        print("!!! INITIAL GREETING ERROR TRACEBACK !!!", flush=True)
        traceback.print_exc()
        logger.error("initial_greeting_error", call_id=call_id, error=str(e))

    # Audio queue: WebSocket → STT
    audio_queue: asyncio.Queue[bytes] = asyncio.Queue()

    async def audio_receiver():
        """Receive audio frames from client."""
        try:
            while True:
                data = await websocket.receive_bytes()
                await audio_queue.put(data)
        except WebSocketDisconnect:
            await audio_queue.put(None)   # sentinel to stop

    async def audio_stream_gen():
        """Async generator over queued audio frames."""
        while True:
            chunk = await audio_queue.get()
            if chunk is None:
                return
            yield chunk

    async def process_transcript():
        """STT → transcript event → LangGraph → TTS → send back."""
        full_text_buffer = ""

        async for chunk in stt.transcribe_stream(audio_stream_gen()):
            if not chunk.text or not chunk.text.strip():
                continue

            # Send transcript chunk to client
            await websocket.send_text(json.dumps({
                "type": "transcript_chunk",
                "text": chunk.text.strip(),
                "speaker": "customer",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "language": chunk.language,
            }))

            # Save to Redis
            await redis_manager.append_transcript(call_id, {
                "speaker": "customer",
                "text": chunk.text.strip(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # Publish for agent dashboard
            await redis_manager.publish(f"transcript.{call_id}", {
                "type": "transcript_chunk",
                "text": chunk.text.strip(),
                "speaker": "customer",
            })

            # Run agent graph on the user's input chunk in real-time
            await _run_agent_and_respond(
                call_id, chunk.text.strip(), state, websocket
            )

    # Run concurrently
    receiver_task = asyncio.create_task(audio_receiver())
    processor_task = asyncio.create_task(process_transcript())

    try:
        await asyncio.gather(receiver_task, processor_task)
    except WebSocketDisconnect:
        logger.info("call_ws_disconnected", call_id=call_id)
    finally:
        receiver_task.cancel()
        processor_task.cancel()
        logger.info("call_ws_cleanup", call_id=call_id)


async def _run_agent_and_respond(
    call_id: str, user_text: str, state: dict, websocket: WebSocket
):
    """Run LangGraph graph and send AI response back to client."""
    from langchain_core.messages import HumanMessage

    # Add user message to state
    state["messages"] = state.get("messages", []) + [
        HumanMessage(content=user_text)
    ]

    try:
        # Run the full agent graph
        result = await call_graph.ainvoke(state)

        # Get the last AI message
        last_ai_msg = None
        for msg in reversed(result.get("messages", [])):
            if hasattr(msg, "name") and msg.name != "user":
                last_ai_msg = msg
                break

        if last_ai_msg:
            response_text = last_ai_msg.content

            # Send agent response event
            await websocket.send_text(json.dumps({
                "type": "agent_response",
                "text": response_text,
                "agent": result.get("active_agent", "ai"),
                "intent": result.get("intent"),
                "citations": result.get("citations", [])[:2],
            }))

            # Add to transcript
            await redis_manager.append_transcript(call_id, {
                "speaker": result.get("active_agent", "ai"),
                "text": response_text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # Publish specifically for agent live dashboard with transcript_chunk type
            await redis_manager.publish(f"transcript.{call_id}", {
                "type": "transcript_chunk",
                "text": response_text,
                "speaker": result.get("active_agent", "ai"),
            })

            # Stream TTS response back to customer client as binary audio chunks
            try:
                from app.core.tts.factory import TTSFactory
                tts = TTSFactory.get_provider()
                async for audio_chunk in tts.synthesize_stream(response_text):
                    await websocket.send_bytes(audio_chunk)
            except Exception as tts_err:
                logger.error("tts_synthesis_error", call_id=call_id, error=str(tts_err))

        # Send intent detected event
        if result.get("intent"):
            await websocket.send_text(json.dumps({
                "type": "intent_detected",
                "intent": result.get("intent"),
                "confidence": result.get("intent_confidence", 0.0),
            }))

        # Send escalation event
        if result.get("escalate"):
            await websocket.send_text(json.dumps({
                "type": "escalating",
                "reason": result.get("escalation_context", {}).get("reason", ""),
            }))

        # Update Redis state
        await redis_manager.save_call_state(call_id, result)

    except Exception as e:
        logger.error("agent_graph_error", call_id=call_id, error=str(e))
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": "Processing error, please hold.",
        }))


async def _create_call_record(call_id: str, channel: str, zoho_ticket_id: str | None = None):
    """Create the call row in PostgreSQL when call starts."""
    try:
        async with AsyncSessionLocal() as db:
            call = Call(id=call_id, channel=channel, status="active")
            db.add(call)
            
            if zoho_ticket_id:
                from app.models import Ticket
                ticket = Ticket(zoho_ticket_id=zoho_ticket_id, call_id=call_id)
                db.add(ticket)
                
            await db.commit()
    except Exception as e:
        logger.error("create_call_record_error", error=str(e))


# ─────────────────────────────────────────────────────────────────────────────
# Human Agent Dashboard WebSocket
# ─────────────────────────────────────────────────────────────────────────────

@router.websocket("/ws/agent/{agent_id}")
async def agent_websocket(websocket: WebSocket, agent_id: str):
    """
    Human agent dashboard WebSocket.
    Receives: customer context, live transcript, AI assist suggestions.
    """
    await websocket.accept()
    logger.info("agent_ws_connected", agent_id=agent_id)

    # Subscribe to agent's assist channel, escalation channel, and live transcript updates
    pubsub = await redis_manager.subscribe(
        f"assist.{agent_id}",
        "human.escalation",
        f"transcript.{agent_id}",
    )

    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                data = json.loads(message["data"])
                await websocket.send_text(json.dumps(data))
    except WebSocketDisconnect:
        logger.info("agent_ws_disconnected", agent_id=agent_id)
    finally:
        await pubsub.unsubscribe()
