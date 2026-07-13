"""
SIP Bridge — Asterisk ↔ AI Backend Audio Bridge
=================================================

Asterisk (SAN Software SIP PBX) se aane wali calls ko
AI backend ke WebSocket se connect karta hai.

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
                                ├─ G.711 μ-law → PCM16 16kHz (upstream)
                                ├─ PCM16 24kHz → G.711 8kHz  (downstream)
                                │
                        backend FastAPI (Port 8000)
                        WS /ws/call/{call_id}

Asterisk Setup:
    - AudioSocket channel (chan_audiosocket) — Asterisk 16.x+
    - Ya AGI script for older versions

Run:
    python sip_bridge.py
    # Listens on 0.0.0.0:5000
"""

import asyncio
import json
import base64
import array
import struct
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
import uvicorn
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse

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
BACKEND_BASE_URL = "http://localhost:8000"
BACKEND_WS_BASE  = "ws://localhost:8000"
BRIDGE_HOST      = "0.0.0.0"
BRIDGE_PORT      = 5000

app = FastAPI(title="SAN Software SIP Bridge", version="1.0.0")


# ──────────────────────────────────────────────────────────────────────────────
# Audio Codec Conversion Utilities
# G.711 μ-law (8kHz) ↔ PCM16 (16kHz)
# ──────────────────────────────────────────────────────────────────────────────

def mulaw_to_pcm16(mu_byte: int) -> int:
    """Decode a single G.711 μ-law byte to a 16-bit PCM sample."""
    mu = ~mu_byte & 0xFF
    sign = mu & 0x80
    exponent = (mu & 0x70) >> 4
    mantissa = mu & 0x0F
    sample = (mantissa << 3) + 132
    sample <<= exponent
    sample -= 132
    return -sample if sign else sample


def pcm16_to_mulaw(sample: int) -> int:
    """Encode a 16-bit PCM sample to G.711 μ-law byte."""
    sign = (sample >> 8) & 0x80
    if sample < 0:
        sample = -sample
    sample += 132
    if sample > 32635:
        sample = 32635
    exponent = 7
    while (sample & 0x4000) == 0 and exponent > 0:
        sample <<= 1
        exponent -= 1
    mantissa = (sample >> 7) & 0x0F
    return ~(sign | (exponent << 4) | mantissa) & 0xFF


def alaw_to_pcm16(a_byte: int) -> int:
    """Decode a single G.711 A-law byte to a 16-bit PCM sample."""
    a_byte ^= 0x55
    sign = a_byte & 0x80
    exponent = (a_byte & 0x70) >> 4
    mantissa = a_byte & 0x0F
    if exponent == 0:
        sample = (mantissa << 1) | 1
    else:
        sample = (mantissa | 0x10) << exponent
    return -sample if sign else sample


def decode_mulaw_bytes(mu_bytes: bytes) -> bytes:
    """Decode G.711 μ-law buffer → PCM16 8kHz (little-endian)."""
    samples = [mulaw_to_pcm16(b) for b in mu_bytes]
    return array.array('h', samples).tobytes()


def decode_alaw_bytes(a_bytes: bytes) -> bytes:
    """Decode G.711 A-law buffer → PCM16 8kHz (little-endian)."""
    samples = [alaw_to_pcm16(b) for b in a_bytes]
    return array.array('h', samples).tobytes()


def encode_pcm16_to_mulaw(pcm16_bytes: bytes) -> bytes:
    """Encode PCM16 buffer → G.711 μ-law bytes."""
    samples = array.array('h', pcm16_bytes)
    return bytes(pcm16_to_mulaw(s) for s in samples)


def upsample_8k_to_16k(pcm16_8k: bytes) -> bytes:
    """
    Upsample PCM16 from 8kHz → 16kHz using linear interpolation.
    Each sample is duplicated to double the sample rate.
    """
    samples_8k = array.array('h', pcm16_8k)
    out = array.array('h')
    for i, s in enumerate(samples_8k):
        out.append(s)
        # Linear interpolation with next sample
        if i + 1 < len(samples_8k):
            interpolated = (s + samples_8k[i + 1]) // 2
        else:
            interpolated = s
        out.append(interpolated)
    return out.tobytes()


def downsample_24k_to_8k(pcm16_24k: bytes) -> bytes:
    """
    Downsample PCM16 from 24kHz → 8kHz.
    24kHz / 8kHz = 3, so keep every 3rd sample.
    """
    samples_24k = array.array('h', pcm16_24k)
    samples_8k = samples_24k[::3]
    return samples_8k.tobytes()


def downsample_16k_to_8k(pcm16_16k: bytes) -> bytes:
    """Downsample PCM16 from 16kHz → 8kHz (keep every 2nd sample)."""
    samples = array.array('h', pcm16_16k)
    return samples[::2].tobytes()


# ──────────────────────────────────────────────────────────────────────────────
# In-memory call registry: sip_call_id → call_id
# ──────────────────────────────────────────────────────────────────────────────
_active_calls: dict[str, str] = {}   # sip_uniqueid → call_id


# ──────────────────────────────────────────────────────────────────────────────
# REST Endpoints for Asterisk Webhook / AGI
# ──────────────────────────────────────────────────────────────────────────────

@app.post("/sip/incoming")
async def handle_incoming_sip_call(request: Request):
    """
    Asterisk ne call receive ki — yeh endpoint call karta hai.

    Asterisk side (extensions.conf):
        exten => _X.,1,AGI(agi_notify.sh,${CALLERID(num)},${UNIQUEID})
        same  => n,AudioSocket(localhost:5000,${CALL_UUID})

    Ya ARI / CURL se:
        POST http://<bridge_host>:5000/sip/incoming
        {
            "caller_id":  "9876543210",
            "uniqueid":   "asterisk-1720859012.42",
            "channel":    "SIP/san-software-00000001",
            "exten":      "1000",
            "context":    "from-san-software"
        }

    Returns:
        {
            "status":        "ok",
            "call_id":       "uuid",
            "ws_url":        "ws://localhost:5000/ws/sip/<call_id>",
            "backend_ws":    "ws://localhost:8000/ws/call/<call_id>"
        }
    """
    try:
        body = await request.json()
    except Exception:
        # Form data fallback
        form = await request.form()
        body = dict(form)

    caller_id  = (body.get("caller_id") or body.get("From") or
                  body.get("callerid") or "unknown")
    sip_uniqueid = (body.get("uniqueid") or body.get("UniqueID") or
                    body.get("call_uuid") or "")
    channel    = body.get("channel", "SIP/unknown")

    logger.info(
        "incoming_sip_call",
        extra={
            "caller_id":   caller_id,
            "sip_uniqueid": sip_uniqueid,
            "channel":     channel,
        }
    )

    # Register call session on backend
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.post(
                f"{BACKEND_BASE_URL}/api/v1/calls/start",
                json={
                    "channel":         "phone",
                    "customer_mobile": caller_id,
                    "sip_call_id":     sip_uniqueid,
                    "sip_channel":     channel,
                }
            )
            resp.raise_for_status()
            call_data = resp.json()
        except httpx.HTTPError as exc:
            logger.error("backend_call_start_failed", extra={"error": str(exc)})
            raise HTTPException(status_code=502, detail=f"Backend unreachable: {exc}")

    call_id = call_data["call_id"]

    # Store mapping: sip_uniqueid → call_id
    if sip_uniqueid:
        _active_calls[sip_uniqueid] = call_id

    bridge_ws_url  = f"ws://localhost:{BRIDGE_PORT}/ws/sip/{call_id}"
    backend_ws_url = call_data.get("ws_url", f"{BACKEND_WS_BASE}/ws/call/{call_id}")

    logger.info("call_session_created", extra={"call_id": call_id, "caller_id": caller_id})

    return JSONResponse({
        "status":       "ok",
        "call_id":      call_id,
        "caller_id":    caller_id,
        "ws_url":       bridge_ws_url,       # Asterisk AudioSocket connects here
        "backend_ws":   backend_ws_url,      # For reference
        "action":       "connect_audiosocket",
    })


@app.post("/sip/hangup")
async def handle_sip_hangup(request: Request):
    """
    Asterisk hangup event — call khatam ho gayi.

    POST body:
        { "uniqueid": "asterisk-xxx", "call_id": "uuid" }
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    sip_uniqueid = body.get("uniqueid", "")
    call_id = body.get("call_id") or _active_calls.pop(sip_uniqueid, None)

    if call_id:
        logger.info("sip_hangup_received", extra={"call_id": call_id})
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                await client.post(f"{BACKEND_BASE_URL}/api/v1/calls/{call_id}/end")
            except Exception as e:
                logger.warning("call_end_failed", extra={"call_id": call_id, "error": str(e)})

    return JSONResponse({"status": "ok", "call_id": call_id})


@app.get("/health")
async def health_check():
    """Bridge health check."""
    return JSONResponse({
        "status":       "healthy",
        "bridge":       "sip_asterisk",
        "active_calls": len(_active_calls),
        "timestamp":    datetime.now(timezone.utc).isoformat(),
    })


# ──────────────────────────────────────────────────────────────────────────────
# Asterisk AudioSocket WebSocket Bridge
# ──────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws/sip/{call_id}")
async def asterisk_audiosocket(asterisk_ws: WebSocket, call_id: str):
    """
    Asterisk AudioSocket WebSocket bridge.

    Asterisk ka AudioSocket protocol is format mein data bhejta hai:
        - Binary frames: raw PCM16 audio (8kHz, mono, little-endian)
        - Ya G.711 μ-law frames (8kHz) agar codec ULAW configure hai

    Asterisk extensions.conf:
        exten => _X.,1,AudioSocket(bridge_host:5000,<call_uuid>)

    Note: AudioSocket UUID directly call_id ke roop mein pass hota hai.
    """
    await asterisk_ws.accept()
    logger.info("audiosocket_connected", extra={"call_id": call_id})

    # Backend WebSocket se connect karo
    backend_ws_url = f"{BACKEND_WS_BASE}/ws/call/{call_id}?channel=phone"
    try:
        backend_ws = await websockets.connect(
            backend_ws_url,
            ping_interval=20,
            ping_timeout=10,
        )
        logger.info("backend_ws_connected", extra={"call_id": call_id})
    except Exception as e:
        logger.error("backend_ws_connect_failed", extra={"call_id": call_id, "error": str(e)})
        await asterisk_ws.close()
        return

    # ── Asterisk → Backend (customer audio) ───────────────────────────────────
    async def forward_audio_to_backend():
        """
        Asterisk se audio receive karke backend ko bhejo.

        AudioSocket frames:
            [1 byte: type][2 bytes: length][N bytes: payload]
            type=0x10: audio data
            type=0x01: UUID (first frame)
            type=0x00: hangup
        """
        try:
            audio_buffer = bytearray()
            CHUNK_MS = 20  # 20ms chunks to backend (320 bytes at 8kHz PCM16)
            CHUNK_SIZE_8K = 320  # 20ms * 8000 Hz * 2 bytes = 320 bytes PCM16 @ 8kHz

            async for raw_data in asterisk_ws.iter_bytes():
                # AudioSocket protocol: parse frame header
                if len(raw_data) < 3:
                    continue

                frame_type   = raw_data[0]
                payload_len  = struct.unpack(">H", raw_data[1:3])[0]
                payload      = raw_data[3:3 + payload_len] if payload_len > 0 else b""

                if frame_type == 0x01:
                    # UUID frame — first frame, contains AudioSocket UUID
                    uuid_str = payload.decode("utf-8", errors="ignore")
                    logger.info("audiosocket_uuid", extra={"call_id": call_id, "uuid": uuid_str})
                    continue

                elif frame_type == 0x00:
                    # Hangup signal from Asterisk
                    logger.info("audiosocket_hangup", extra={"call_id": call_id})
                    break

                elif frame_type == 0x10:
                    # Audio data frame
                    if not payload:
                        continue

                    # Payload G.711 μ-law → PCM16 8kHz → upsample → PCM16 16kHz
                    pcm16_8k  = decode_mulaw_bytes(payload)
                    pcm16_16k = upsample_8k_to_16k(pcm16_8k)

                    # Buffer karo aur 20ms chunks mein backend ko bhejo
                    audio_buffer.extend(pcm16_16k)

                    # 20ms @ 16kHz = 640 bytes PCM16
                    CHUNK_16K = 640
                    while len(audio_buffer) >= CHUNK_16K:
                        chunk = bytes(audio_buffer[:CHUNK_16K])
                        audio_buffer = audio_buffer[CHUNK_16K:]
                        await backend_ws.send(chunk)

                else:
                    # Unknown frame type — ignore karo
                    logger.debug("unknown_audiosocket_frame", extra={"type": frame_type})

        except WebSocketDisconnect:
            logger.info("asterisk_ws_disconnected", extra={"call_id": call_id})
        except Exception as e:
            logger.error("forward_to_backend_error", extra={"call_id": call_id, "error": str(e)})
        finally:
            try:
                await backend_ws.close()
            except Exception:
                pass

    # ── Backend → Asterisk (TTS audio) ────────────────────────────────────────
    async def forward_audio_to_asterisk():
        """
        Backend se TTS audio receive karke Asterisk ko bhejo.
        Backend 24kHz PCM16 bhejta hai → 8kHz PCM16 → G.711 μ-law → AudioSocket frame.
        """
        try:
            async for message in backend_ws:
                if isinstance(message, bytes):
                    # Backend Kokoro/ElevenLabs 24kHz PCM16 bhejta hai
                    pcm16_8k   = downsample_24k_to_8k(message)
                    mulaw_data = encode_pcm16_to_mulaw(pcm16_8k)

                    # AudioSocket audio frame: [type=0x10][len 2B big-endian][payload]
                    frame = (
                        bytes([0x10]) +
                        struct.pack(">H", len(mulaw_data)) +
                        mulaw_data
                    )
                    await asterisk_ws.send_bytes(frame)

                elif isinstance(message, str):
                    # JSON event (transcript, agent_response) — log karo, audio ignore
                    try:
                        event = json.loads(message)
                        event_type = event.get("type", "")
                        logger.debug("backend_event", extra={
                            "call_id": call_id,
                            "event_type": event_type,
                        })
                    except json.JSONDecodeError:
                        pass

        except Exception as e:
            logger.error("forward_to_asterisk_error", extra={"call_id": call_id, "error": str(e)})
        finally:
            try:
                await asterisk_ws.close()
            except Exception:
                pass

    # ── Dono directions concurrently chalao ───────────────────────────────────
    logger.info("bridge_started", extra={"call_id": call_id})
    await asyncio.gather(
        forward_audio_to_backend(),
        forward_audio_to_asterisk(),
    )
    logger.info("bridge_closed", extra={"call_id": call_id})

    # Call end karo backend pe
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.post(f"{BACKEND_BASE_URL}/api/v1/calls/{call_id}/end")
        except Exception:
            pass


# ──────────────────────────────────────────────────────────────────────────────
# Plain PCM WebSocket (Asterisk ExternalMedia / older setups)
# ──────────────────────────────────────────────────────────────────────────────

@app.websocket("/ws/sip-pcm/{call_id}")
async def asterisk_pcm_socket(asterisk_ws: WebSocket, call_id: str):
    """
    Fallback WebSocket for Asterisk ExternalMedia (plain binary PCM16 8kHz).
    Asterisk ExternalMedia app directly sends raw PCM without AudioSocket framing.

    Asterisk dialplan (ARI):
        "external_media": {
            "channel": "...",
            "app": "your_ari_app",
            "external_host": "bridge_host:5000",
            "format": "slin"
        }
    """
    await asterisk_ws.accept()
    logger.info("pcm_socket_connected", extra={"call_id": call_id})

    backend_ws_url = f"{BACKEND_WS_BASE}/ws/call/{call_id}?channel=phone"
    try:
        backend_ws = await websockets.connect(backend_ws_url)
    except Exception as e:
        logger.error("backend_ws_failed", extra={"error": str(e)})
        await asterisk_ws.close()
        return

    async def recv_from_asterisk():
        try:
            async for chunk in asterisk_ws.iter_bytes():
                # Raw PCM16 8kHz → upsample → PCM16 16kHz → backend
                pcm16_16k = upsample_8k_to_16k(chunk)
                await backend_ws.send(pcm16_16k)
        except Exception as e:
            logger.error("pcm_recv_error", extra={"error": str(e)})
        finally:
            await backend_ws.close()

    async def send_to_asterisk():
        try:
            async for msg in backend_ws:
                if isinstance(msg, bytes):
                    # 24kHz → 8kHz → Asterisk
                    pcm16_8k = downsample_24k_to_8k(msg)
                    await asterisk_ws.send_bytes(pcm16_8k)
        except Exception as e:
            logger.error("pcm_send_error", extra={"error": str(e)})
        finally:
            await asterisk_ws.close()

    await asyncio.gather(recv_from_asterisk(), send_to_asterisk())
    logger.info("pcm_bridge_closed", extra={"call_id": call_id})


# ──────────────────────────────────────────────────────────────────────────────
# Entry Point
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    uvicorn.run(
        "sip_bridge:app",
        host=BRIDGE_HOST,
        port=BRIDGE_PORT,
        log_level="info",
        reload=False,
    )
