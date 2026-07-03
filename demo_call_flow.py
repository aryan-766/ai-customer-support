"""
Ambrane AI Customer Support — FIXED DEMO
=========================================
Single persistent WebSocket per call.
Audio streaming + event collection happen SIMULTANEOUSLY.
STT transcribes during streaming (every 3s of buffered audio).
"""

import asyncio
import io
import json
import os
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import httpx
import websockets

backend_path = os.path.join(os.path.dirname(__file__), "backend")
sys.path.insert(0, backend_path)

DIVIDER = "─" * 62
SAMPLE_RATE_OUT  = 16000   # Whisper expects 16kHz
SAMPLE_RATE_TTS  = 24000   # Kokoro outputs 24kHz
STREAM_CHUNK_MS  = 100     # simulate 100ms mic chunks


# ─── Helpers ─────────────────────────────────────────────────────────────────

def resample(audio_bytes: bytes, from_hz: int, to_hz: int) -> bytes:
    samples = np.frombuffer(audio_bytes, dtype=np.int16)
    n_out   = int(len(samples) * to_hz / from_hz)
    idx     = np.linspace(0, len(samples) - 1, n_out)
    out     = np.interp(idx, np.arange(len(samples)), samples).astype(np.int16)
    return out.tobytes()


async def tts_synthesize(text: str) -> bytes:
    from app.core.tts.kokoro import KokoroTTS
    tts = KokoroTTS()
    chunks = []
    async for chunk in tts.synthesize_stream(text):
        chunks.append(chunk)
    return b"".join(chunks)


# ─── Core conversation turn ───────────────────────────────────────────────────

async def speak_and_listen(
    ws: websockets.WebSocketClientProtocol,
    audio_16k: bytes,
    label: str,
    listen_extra_secs: float = 15.0,
) -> list[dict]:
    """
    Stream audio in real-time while simultaneously collecting JSON events.
    After streaming finishes, keep listening for `listen_extra_secs` for
    any remaining STT / agent / TTS responses.
    """
    events = []

    chunk_bytes = int(SAMPLE_RATE_OUT * 2 * STREAM_CHUNK_MS / 1000)
    total_chunks = (len(audio_16k) + chunk_bytes - 1) // chunk_bytes
    stream_duration_s = total_chunks * STREAM_CHUNK_MS / 1000

    print(f"\n  👤  {label}")
    print(f"      Streaming {len(audio_16k):,} bytes "
          f"({stream_duration_s:.1f}s audio) at {STREAM_CHUNK_MS}ms chunks …")

    async def _stream():
        for i in range(0, len(audio_16k), chunk_bytes):
            await ws.send(audio_16k[i: i + chunk_bytes])
            await asyncio.sleep(STREAM_CHUNK_MS / 1000)

    async def _recv(stop_event: asyncio.Event, extra_secs: float):
        deadline = asyncio.get_event_loop().time()
        try:
            while True:
                # Keep extending deadline while audio is still streaming,
                # then wait extra_secs after stop_event is set
                if stop_event.is_set():
                    remaining = deadline - asyncio.get_event_loop().time()
                    if remaining <= 0:
                        break
                    timeout = remaining
                else:
                    timeout = 2.0  # short poll during streaming

                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=timeout)
                except asyncio.TimeoutError:
                    if stop_event.is_set():
                        break
                    continue

                if isinstance(msg, str):
                    evt = json.loads(msg)
                    events.append(evt)
                elif isinstance(msg, bytes):
                    events.append({"type": "audio_chunk", "bytes": len(msg)})

        except websockets.exceptions.ConnectionClosed:
            pass

    stop_event = asyncio.Event()

    # Launch receiver first, then stream audio
    recv_task = asyncio.create_task(_recv(stop_event, listen_extra_secs))

    await _stream()

    # Audio streaming done — let receiver keep listening for responses
    loop = asyncio.get_event_loop()
    stop_event.set()
    deadline_time = loop.time() + listen_extra_secs

    # Patch deadline into the closure (simpler: just run recv directly)
    recv_task.cancel()
    # Re-receive events for extra_secs
    try:
        deadline = asyncio.get_event_loop().time() + listen_extra_secs
        while True:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                break
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=min(remaining, 2.0))
                if isinstance(msg, str):
                    evt = json.loads(msg)
                    events.append(evt)
                    t = evt.get("type")
                    if t == "transcript_chunk":
                        print(f"\n  ✍️   [STT Transcript]  : {evt.get('text')}")
                    elif t == "agent_response":
                        print(f"  🤖  [AI Response]     : {evt.get('text')}")
                    elif t == "intent_detected":
                        print(f"  🎯  [Intent]          : {evt.get('intent')} ({evt.get('confidence', 0):.2f})")
                    elif t == "escalating":
                        print(f"  🚨  [Escalation]      : {evt.get('reason')}")
                elif isinstance(msg, bytes):
                    events.append({"type": "audio_chunk", "bytes": len(msg)})
                    print(f"  🔊  [TTS Voice Reply] : {len(msg):,} bytes PCM16 24kHz")
            except asyncio.TimeoutError:
                continue
            except websockets.exceptions.ConnectionClosed:
                break
    except Exception:
        pass

    return events


# ─── Main Demo ────────────────────────────────────────────────────────────────

async def demo():
    print(DIVIDER)
    print("  🔊  AMBRANE AI — CALL FLOW LIVE DEMO")
    print(DIVIDER)

    # ── Synthesize customer voice queries ─────────────────────────────────────
    queries = [
        "My customer ID is CUST-10001. I want to check my order status.",
        "What is the warranty on my power bank?",
    ]

    print(f"\n[STEP 1] Synthesizing {len(queries)} customer queries via Kokoro TTS …")
    audio_16k_list = []
    for i, q in enumerate(queries, 1):
        print(f"  Synthesizing query {i}: '{q[:50]}…'")
        raw_24k = await tts_synthesize(q)
        audio_16k = resample(raw_24k, SAMPLE_RATE_TTS, SAMPLE_RATE_OUT)
        audio_16k_list.append(audio_16k)
        print(f"  ✓  {len(raw_24k):,} bytes (24kHz TTS) → {len(audio_16k):,} bytes (16kHz for STT)")

    # ── Start call session ────────────────────────────────────────────────────
    print(f"\n[STEP 2] Starting call session via REST API …")
    async with httpx.AsyncClient() as client:
        res = await client.post(
            "http://localhost:8000/api/v1/calls/start",
            json={"channel": "web", "customer_mobile": "9876543210"},
        )
        res.raise_for_status()
        data = res.json()

    call_id = data["call_id"]
    ws_url  = data["ws_url"]
    print(f"  ✓  Call ID : {call_id}")
    print(f"  ✓  WS URL  : {ws_url}")

    # ── Single persistent WebSocket for the ENTIRE call ───────────────────────
    print(f"\n[STEP 3] Opening WebSocket — waiting for Receptionist greeting …")

    async with websockets.connect(ws_url) as ws:

        # Collect greeting
        greeting_text  = None
        greeting_audio = 0
        try:
            while True:
                msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                if isinstance(msg, str):
                    evt = json.loads(msg)
                    if evt.get("type") == "agent_response":
                        greeting_text = evt.get("text")
                elif isinstance(msg, bytes):
                    greeting_audio += len(msg)
                    if greeting_text:
                        # Give 1.5s for any trailing audio bytes
                        await asyncio.sleep(1.5)
                        break
        except asyncio.TimeoutError:
            pass

        print(f"\n  🤖  Receptionist  : {greeting_text}")
        print(f"  🔊  Greeting audio : {greeting_audio:,} bytes PCM16 24kHz")
        print(DIVIDER)

        # ── Multi-turn conversation on the SAME WebSocket ─────────────────────
        print(f"\n[STEP 4] Multi-turn conversation on single call session …\n")

        for turn, (query_text, audio_16k) in enumerate(
            zip(queries, audio_16k_list), start=1
        ):
            print(DIVIDER)
            print(f"  TURN {turn}")
            events = await speak_and_listen(
                ws,
                audio_16k,
                label=f'Customer: "{query_text}"',
                listen_extra_secs=20.0,
            )

            n_audio = sum(1 for e in events if e.get("type") == "audio_chunk")
            n_text  = sum(1 for e in events if e.get("type") != "audio_chunk")
            print(f"\n  Summary: {n_text} text events + {n_audio} audio chunks received")
            print()

    # ── Done ─────────────────────────────────────────────────────────────────
    print(DIVIDER)
    print("  ✅  Demo complete!  Pipeline exercised:")
    print("      Kokoro TTS  →  WS Stream  →  Whisper STT")
    print("      →  LangGraph Agents (Auth / Intent / CRM / RAG)")
    print("      →  Qwen 2.5 3B LLM  →  Kokoro TTS  →  Client")
    print(DIVIDER)


if __name__ == "__main__":
    asyncio.run(demo())
