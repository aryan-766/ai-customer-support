import asyncio
import json
import base64
import array
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response, Request
import uvicorn
import httpx
import websockets

app = FastAPI()

# G.711 mu-law decoding and encoding logic
def mulaw_to_pcm(mu_byte):
    mu = ~mu_byte & 0xFF
    sign = (mu & 0x80)
    exponent = (mu & 0x70) >> 4
    mantissa = mu & 0x0F
    sample = (mantissa << 3) + 132
    sample <<= exponent
    sample -= 132
    return -sample if sign else sample

def pcm16_to_mulaw(sample):
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

def decode_mulaw_to_pcm16_8k(mu_bytes: bytes) -> bytes:
    samples = [mulaw_to_pcm(b) for b in mu_bytes]
    return array.array('h', samples).tobytes()

def encode_pcm16_8k_to_mulaw(pcm16_8k: bytes) -> bytes:
    # Every 2 bytes is a 16-bit sample
    samples = array.array('h', pcm16_8k)
    mulaw_bytes = [pcm16_to_mulaw(s) for s in samples]
    return bytes(mulaw_bytes)

def upsample_8k_to_16k_pcm16(pcm16_8k: bytes) -> bytes:
    out = bytearray(len(pcm16_8k) * 2)
    for i in range(0, len(pcm16_8k), 2):
        sample = pcm16_8k[i:i+2]
        out[i*2:i*2+2] = sample
        out[i*2+2:i*2+4] = sample
    return bytes(out)

def downsample_24k_to_8k_pcm16(pcm16_24k: bytes) -> bytes:
    # 24kHz to 8kHz downsampling = keep 1 sample out of every 3
    # 1 sample is 2 bytes
    samples_24k = array.array('h', pcm16_24k)
    samples_8k = samples_24k[::3]
    return samples_8k.tobytes()

@app.post("/twilio-voice")
async def twilio_voice(request: Request):
    # Dynamically read host and scheme to support any ngrok subdomain automatically
    host = request.headers.get("host")
    scheme = "wss" if request.url.scheme == "https" else "ws"
    
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Connecting to Ambrane AI Voice Assistant.</Say>
    <Connect>
        <Stream url="{scheme}://{host}/ws/twilio" />
    </Connect>
</Response>
"""
    return Response(content=xml, media_type="application/xml")

@app.websocket("/ws/twilio")
async def ws_twilio(twilio_ws: WebSocket):
    await twilio_ws.accept()
    print("Twilio WebSocket connected!")

    # Start a call session on the local backend
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post("http://localhost:8000/api/v1/calls/start", json={"channel": "phone", "customer_mobile": "9876543210"})
            res.raise_for_status()
            call_data = res.json()
            local_ws_url = call_data["ws_url"]
            print(f"Call session started successfully on backend! WS URL: {local_ws_url}")
        except Exception as e:
            print(f"Failed to start call session on backend: {e}")
            await twilio_ws.close()
            return

    # Connect to the local backend WebSocket
    try:
        local_ws = await websockets.connect(local_ws_url)
        print("Connected to backend voice agent WebSocket.")
    except Exception as e:
        print(f"Failed to connect to local backend WebSocket: {e}")
        await twilio_ws.close()
        return

    stream_sid = None

    async def forward_to_backend():
        nonlocal stream_sid
        try:
            async for message in twilio_ws.iter_text():
                data = json.loads(message)
                event = data.get("event")
                if event == "start":
                    stream_sid = data.get("start", {}).get("streamSid")
                    print(f"Received Twilio start event. StreamSid: {stream_sid}")
                elif event == "media":
                    payload = data.get("media", {}).get("payload")
                    if payload:
                        # Decode base64 mulaw
                        mu_bytes = base64.b64decode(payload)
                        # Convert G.711 mulaw to PCM16
                        pcm16_8k = decode_mulaw_to_pcm16_8k(mu_bytes)
                        # Resample 8kHz to 16kHz for STT
                        pcm16_16k = upsample_8k_to_16k_pcm16(pcm16_8k)
                        # Send binary PCM16 to local backend
                        await local_ws.send(pcm16_16k)
                elif event == "stop":
                    print("Received Twilio stop event.")
                    break
        except Exception as e:
            print(f"Error in forward_to_backend: {e}")
        finally:
            await local_ws.close()

    async def forward_to_twilio():
        nonlocal stream_sid
        try:
            async for message in local_ws:
                # Local backend sends binary audio (synthesized TTS)
                if isinstance(message, bytes):
                    if stream_sid:
                        # Backend Kokoro outputs 24kHz PCM16 audio
                        # Downsample 24kHz to 8kHz for Twilio
                        pcm16_8k = downsample_24k_to_8k_pcm16(message)
                        # Encode PCM16 to G.711 mulaw
                        mu_bytes = encode_pcm16_8k_to_mulaw(pcm16_8k)
                        # Base64 encode
                        payload = base64.b64encode(mu_bytes).decode("utf-8")
                        # Send media event to Twilio
                        await twilio_ws.send_text(json.dumps({
                            "event": "media",
                            "streamSid": stream_sid,
                            "media": {
                                "payload": payload
                            }
                        }))
                else:
                    # Message is JSON event (e.g. transcript_chunk)
                    pass
        except Exception as e:
            print(f"Error in forward_to_twilio: {e}")
        finally:
            await twilio_ws.close()

    # Run tasks concurrently
    await asyncio.gather(forward_to_backend(), forward_to_twilio())
    print("Call session closed.")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
