"""
SIP Bridge — Asterisk ↔ ElevenLabs Conversational AI
=================================================

Asterisk (SAN Software SIP PBX) se aane wali calls ko
ElevenLabs Conversational AI Agent ke WebSocket se connect karta hai.

Architecture:
    SAN Software → Asterisk PBX
                        │
                        ├─ POST /sip/incoming    ← AGI/ARI webhook
                        │                          (call_id milta hai)
                        │
                        └─ WS /ws/sip/{call_id}  ← AudioSocket protocol
                                │  binary G.711 audio (8kHz, μ-law)
                                │
                        sip_bridge.py (Port 5000)
                                │
                                ├─ G.711 μ-law → PCM16 16kHz → Base64 JSON (to ElevenLabs)
                                ├─ ElevenLabs Base64 JSON → PCM16 16kHz → G.711 8kHz (to Asterisk)
                                │
                        ElevenLabs (wss://api.elevenlabs.io/v1/convai/conversation)

"""

import asyncio
import json
import base64
import struct
import logging
import os
import audioop
from datetime import datetime, timezone

import httpx
import uvicorn
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import JSONResponse

# ──────────────────────────────────────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"
)
logger = logging.getLogger("sip_bridge")

# ──────────────────────────────────────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────────────────────────────────────
BRIDGE_HOST = "0.0.0.0"
BRIDGE_PORT = 5000
ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID", "your_elevenlabs_agent_id_here")

app = FastAPI(title="SAN Software to ElevenLabs SIP Bridge", version="1.0.0")

# ──────────────────────────────────────────────────────────────────────────────
# Audio Codec Conversion Utilities (Audioop)
# G.711 μ-law (8kHz) ↔ PCM16 (16kHz)
# ──────────────────────────────────────────────────────────────────────────────

def decode_mulaw_bytes(mulaw_data: bytes) -> bytes:
    """Decode G.711 μ-law to 16-bit PCM (8kHz)."""
    return audioop.ulaw2lin(mulaw_data, 2)

def encode_pcm16_to_mulaw(pcm_data: bytes) -> bytes:
    """Encode 16-bit PCM (8kHz) to G.711 μ-law."""
    return audioop.lin2ulaw(pcm_data, 2)

def upsample_8k_to_16k(pcm_8k: bytes) -> bytes:
    """Upsample PCM 8kHz to 16kHz."""
    pcm_16k, _ = audioop.ratecv(pcm_8k, 2, 1, 8000, 16000, None)
    return pcm_16k

def downsample_16k_to_8k(pcm_16k: bytes) -> bytes:
    """Downsample PCM 16kHz to 8kHz."""
    pcm_8k, _ = audioop.ratecv(pcm_16k, 2, 1, 16000, 8000, None)
    return pcm_8k


# ──────────────────────────────────────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/sip/incoming")
async def sip_incoming(request: Request):
    """
    Asterisk AGI scripts POST call metadata here before opening AudioSocket.
    """
    try:
        body = await request.json()
    except Exception:
        form = await request.form()
        body = dict(form)

    caller_id  = (body.get("caller_id") or body.get("From") or body.get("callerid") or "unknown")
    sip_uniqueid = (body.get("uniqueid") or body.get("UniqueID") or body.get("call_uuid") or "")
    
    logger.info("incoming_sip_call", extra={"caller_id": caller_id, "sip_uniqueid": sip_uniqueid})

    # Return the AudioSocket bridge URL
    bridge_ws_url = f"ws://localhost:{BRIDGE_PORT}/ws/sip/{sip_uniqueid}"
    return JSONResponse(status_code=200, content={"status": "ok", "ws_url": bridge_ws_url})


@app.websocket("/ws/sip/{call_id}")
async def asterisk_audio_socket(websocket: WebSocket, call_id: str):
    """
    Asterisk AudioSocket connection. Streams audio to/from ElevenLabs.
    """
    await websocket.accept()
    logger.info("asterisk_audiosocket_connected", extra={"call_id": call_id})

    elevenlabs_url = f"wss://api.elevenlabs.io/v1/convai/conversation?agent_id={ELEVENLABS_AGENT_ID}"

    try:
        async with websockets.connect(elevenlabs_url) as eleven_ws:
            logger.info("elevenlabs_connected", extra={"call_id": call_id})

            async def forward_to_elevenlabs():
                try:
                    while True:
                        raw_data = await websocket.receive_bytes()
                        if len(raw_data) < 3:
                            continue

                        frame_type = raw_data[0]
                        payload_len = struct.unpack(">H", raw_data[1:3])[0]
                        payload = raw_data[3:3 + payload_len] if payload_len > 0 else b""

                        if frame_type == 0x10 and payload:
                            # Decode and upsample
                            pcm16_8k = decode_mulaw_bytes(payload)
                            pcm16_16k = upsample_8k_to_16k(pcm16_8k)
                            
                            # Encode to base64
                            b64_audio = base64.b64encode(pcm16_16k).decode("utf-8")
                            
                            # Send to ElevenLabs as JSON
                            await eleven_ws.send(json.dumps({"user_audio_chunk": b64_audio}))

                        elif frame_type == 0x00:
                            # Hangup
                            break
                except WebSocketDisconnect:
                    logger.info("asterisk_disconnected", extra={"call_id": call_id})
                except Exception as e:
                    logger.error("forward_to_eleven_error", extra={"error": str(e)})

            async def receive_from_elevenlabs():
                try:
                    async for message in eleven_ws:
                        data = json.loads(message)
                        if data.get("type") == "audio" and "audio_event" in data:
                            b64_audio = data["audio_event"].get("audio_base_64", "")
                            if b64_audio:
                                pcm16_16k = base64.b64decode(b64_audio)
                                # Downsample and encode
                                pcm16_8k = downsample_16k_to_8k(pcm16_16k)
                                mulaw_data = encode_pcm16_to_mulaw(pcm16_8k)
                                
                                # Send as AudioSocket frame
                                frame = bytes([0x10]) + struct.pack(">H", len(mulaw_data)) + mulaw_data
                                await websocket.send_bytes(frame)
                except Exception as e:
                    logger.error("receive_from_eleven_error", extra={"error": str(e)})

            await asyncio.gather(
                forward_to_elevenlabs(),
                receive_from_elevenlabs()
            )
    except Exception as e:
        logger.error("elevenlabs_connection_failed", extra={"error": str(e)})
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


if __name__ == "__main__":
    uvicorn.run(app, host=BRIDGE_HOST, port=BRIDGE_PORT)
