import asyncio
import json
import sys
import httpx
import websockets
import pyaudio

# Audio Configuration matching backend
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1024

BACKEND_URL = "http://localhost:8000"
WS_BASE_URL = "ws://localhost:8000"


async def main():
    print("📞 Starting Voice Call Session...")

    # 1. Start call via HTTP
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                f"{BACKEND_URL}/api/v1/calls/start",
                json={"channel": "phone", "customer_mobile": "9876543210"},
            )
            response.raise_for_status()
            call_data = response.json()
        except Exception as e:
            print(f"❌ Failed to start call session: {e}")
            print("Make sure the backend is running at http://localhost:8000")
            sys.exit(1)

    call_id = call_data["call_id"]
    ws_url = call_data["ws_url"]

    print("\n🚀 Call Connected Successfully!")
    print(f"🔹 Call ID: {call_id}")
    print(f"🔹 Dashboard Link: http://localhost:3000/calls/{call_id}")
    print("-----------------------------------------------------------------")
    print("🎤 Speak into your microphone. AI receptionist will answer.")
    print("Press Ctrl+C to hang up.")
    print("-----------------------------------------------------------------\n")

    # Initialize PyAudio
    p = pyaudio.PyAudio()

    # Input (Microphone) Stream
    input_stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK,
    )

    # Output (Speaker) Stream - Kokoro outputs 24kHz audio, so we set rate=24000
    output_stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=24000,
        output=True,
    )

    try:
        async with websockets.connect(ws_url) as ws:

            async def send_audio():
                """Reads from mic and sends PCM16 audio chunks to websocket."""
                loop = asyncio.get_event_loop()
                try:
                    while True:
                        # Non-blocking read from mic
                        data = await loop.run_in_executor(
                            None, input_stream.read, CHUNK, False
                        )
                        await ws.send(data)
                        await asyncio.sleep(0.01)
                except Exception as e:
                    print(f"\n[Mic Error]: {e}")

            async def receive_events_and_audio():
                """Receives transcripts and synthesised voice responses from websocket."""
                try:
                    async for message in ws:
                        # Binary message = synthesized audio response (TTS)
                        if isinstance(message, bytes):
                            output_stream.write(message)
                        # Text message = JSON event (transcription/intent/etc.)
                        else:
                            event = json.loads(message)
                            event_type = event.get("type")
                            if event_type == "transcript_chunk":
                                speaker = event.get("speaker", "unknown").upper()
                                print(f"🗣️  [{speaker}]: {event.get('text')}")
                            elif event_type == "agent_response":
                                print(f"🤖 [AI REPLY]: {event.get('text')}")
                            elif event_type == "intent_detected":
                                print(
                                    f"🎯 [Intent]: {event.get('intent')} ({event.get('confidence'):.2f})"
                                )
                            elif event_type == "escalating":
                                print(f"🚨 [Escalation Triggered]: {event.get('reason')}")
                except websockets.exceptions.ConnectionClosed:
                    print("\n🔌 Connection closed by server.")
                except Exception as e:
                    print(f"\n[Receiver Error]: {e}")

            # Run both send and receive tasks concurrently
            await asyncio.gather(send_audio(), receive_events_and_audio())

    except KeyboardInterrupt:
        print("\n🤙 Hanging up call...")
    finally:
        # Clean up audio streams
        input_stream.stop_stream()
        input_stream.close()
        output_stream.stop_stream()
        output_stream.close()
        p.terminate()
        print("🔴 Call disconnected.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
