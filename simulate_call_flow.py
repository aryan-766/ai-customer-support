import asyncio
import json
import os
import sys
import io

# Force UTF-8 stdout encoding to support printing emojis on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import numpy as np
import httpx
import websockets

# Add backend directory to sys.path so we can import app models and config
backend_path = os.path.join(os.path.dirname(__file__), "backend")
sys.path.append(backend_path)

from app.core.tts.kokoro import KokoroTTS

def resample_24k_to_16k(audio_bytes: bytes) -> bytes:
    """Resample PCM16 24kHz audio from Kokoro to PCM16 16kHz for Whisper STT."""
    samples_24k = np.frombuffer(audio_bytes, dtype=np.int16)
    num_samples_16k = int(len(samples_24k) * 16000 / 24000)
    indices = np.linspace(0, len(samples_24k) - 1, num_samples_16k)
    samples_16k = np.interp(indices, np.arange(len(samples_24k)), samples_24k).astype(np.int16)
    return samples_16k.tobytes()

async def run_simulation():
    print("=" * 60)
    print("🔊 AMBRANE AI CUSTOMER SUPPORT — END-TO-END CALL SIMULATION")
    print("=" * 60)
    
    # 1. Synthesize customer speech locally
    print("\n[1/5] Synthesizing customer voice query locally...")
    tts = KokoroTTS()
    customer_text = "My customer ID is CUST-10001. I want to check my order status."
    
    audio_chunks = []
    async for chunk in tts.synthesize_stream(customer_text):
        audio_chunks.append(chunk)
    raw_24k_audio = b"".join(audio_chunks)
    
    # Resample to 16kHz (which the STT expects)
    customer_audio_16k = resample_24k_to_16k(raw_24k_audio)
    print(f"  - Generated customer speech: '{customer_text}'")
    print(f"  - Generated audio: {len(raw_24k_audio)} bytes (24kHz) -> Resampled: {len(customer_audio_16k)} bytes (16kHz)")

    # 2. Start Call Session
    print("\n[2/5] Initiating call session via backend API...")
    async with httpx.AsyncClient() as client:
        res = await client.post("http://localhost:8000/api/v1/calls/start", json={"channel": "phone", "customer_mobile": "9876543210"})
        res.raise_for_status()
        call_data = res.json()
        call_id = call_data["call_id"]
        ws_url = call_data["ws_url"]
        print(f"  - Call ID: {call_id}")
        print(f"  - WebSocket Connection URL: {ws_url}")

    # 3. Connect to WebSocket & Listen for Receptionist Greeting
    print("\n[3/5] Connecting to WebSocket & listening for receptionist greeting...")
    async with websockets.connect(ws_url) as ws:
        greeting_text = None
        greeting_audio_bytes = 0
        
        # Read WebSocket messages until greeting completes
        while True:
            msg = await ws.recv()
            if isinstance(msg, str):
                event = json.loads(msg)
                if event.get("type") == "agent_response":
                    greeting_text = event.get("text")
                    print(f"\n🗣️  [AI Event]: {event}")
            elif isinstance(msg, bytes):
                greeting_audio_bytes += len(msg)
                # Wait for the complete stream to arrive
                if greeting_text:
                    await asyncio.sleep(1.5)
                    break
        
        print(f"\n🤖 [AI Receptionist]: {greeting_text}")
        print(f"🔊 [Voice Stream]: Received {greeting_audio_bytes} bytes of greeting voice audio (PCM16 24kHz).")

        # 4. Stream Customer Voice Query (Simulated Microphone)
        print("\n[4/5] Streaming customer speech to agent (Simulating Microphone input)...")
        # Stream in 100ms chunks (3200 bytes at 16kHz PCM16)
        chunk_size = 3200
        for i in range(0, len(customer_audio_16k), chunk_size):
            chunk = customer_audio_16k[i:i+chunk_size]
            await ws.send(chunk)
            await asyncio.sleep(0.1) # Simulate real-time mic streaming
        
        print("  - Streaming finished. Processing speech...")

        # 5. Listen for STT transcription, LangGraph agents processing, and reply
        print("\n[5/5] Listening for STT transcription, CRM logic, and AI response...")
        print("-" * 60)
        
        try:
            while True:
                # Stop if no messages arrive for 15 seconds after user finished speaking
                msg = await asyncio.wait_for(ws.recv(), timeout=15.0)
                if isinstance(msg, str):
                    event = json.loads(msg)
                    event_type = event.get("type")
                    if event_type == "transcript_chunk":
                        print(f"\n✍️  [STT Transcript]: {event.get('text')} (Language: {event.get('language')})")
                    elif event_type == "agent_response":
                        print(f"\n🤖 [AI Reply]: {event.get('text')}")
                    elif event_type == "intent_detected":
                        print(f"🎯 [Intent Match]: {event.get('intent')} (Confidence: {event.get('confidence')})")
                    elif event_type == "escalating":
                        print(f"🚨 [Escalation Triggered]: {event.get('reason')}")
                    else:
                        print(f"📢 [Event]: {event}")
                elif isinstance(msg, bytes):
                    print(f"🔊 [Voice Stream]: Received {len(msg)} bytes of reply voice audio (PCM16 24kHz).")
        except asyncio.TimeoutError:
            print("-" * 60)
            print("📞 Call simulation ended (silence timeout).")

if __name__ == "__main__":
    asyncio.run(run_simulation())
