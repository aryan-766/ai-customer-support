"""
Deepgram STT provider — nova-3 model
=====================================
- Real-time WebSocket streaming (wss://api.deepgram.com/v1/listen)
- Batch REST API (https://api.deepgram.com/v1/listen)
- Config: nova-3, linear16, 16kHz, endpointing configurable
"""
import os
import json
import asyncio
import structlog
import httpx
import websockets
from typing import AsyncIterator, Optional, Callable
from app.config import settings
from app.core.stt.base import BaseSTTProvider, TranscriptChunk

logger = structlog.get_logger(__name__)

DEEPGRAM_WS_URL = "wss://api.deepgram.com/v1/listen"
DEEPGRAM_REST_URL = "https://api.deepgram.com/v1/listen"


class DeepgramSTT(BaseSTTProvider):
    def __init__(self):
        self.api_key = (
            getattr(settings, "DEEPGRAM_API_KEY", None)
            or os.environ.get("DEEPGRAM_API_KEY", "")
        )
        self.model = getattr(settings, "DEEPGRAM_MODEL", "nova-3")
        self.language = getattr(settings, "DEEPGRAM_LANGUAGE", "en")
        self.encoding = getattr(settings, "DEEPGRAM_ENCODING", "linear16")
        self.sample_rate = getattr(settings, "DEEPGRAM_SAMPLE_RATE", 16000)
        self.endpointing = getattr(settings, "DEEPGRAM_ENDPOINTING", False)

        if not self.api_key:
            logger.warning("deepgram_api_key_missing")

    # ── WebSocket Streaming (real-time, low-latency) ──────────────────────────

    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
        on_interim: Optional[Callable[[str], None]] = None,
    ) -> AsyncIterator[TranscriptChunk]:
        """
        Real-time transcription via Deepgram WebSocket.

        Yields TranscriptChunk for every final transcript.
        on_interim: optional callback for interim (partial) results.

        Audio format: PCM16, mono, 16kHz (linear16)
        """
        # Build WebSocket URL with query params
        ws_url = (
            f"{DEEPGRAM_WS_URL}"
            f"?model={self.model}"
            f"&language={self.language}"
            f"&encoding={self.encoding}"
            f"&sample_rate={self.sample_rate}"
            f"&endpointing={'false' if not self.endpointing else 'true'}"
            f"&interim_results=true"
            f"&smart_format=true"
            f"&channels=1"
        )

        headers = {"Authorization": f"Token {self.api_key}"}

        results_queue: asyncio.Queue = asyncio.Queue()

        async def _send_audio(ws):
            """Audio chunks bhejo Deepgram ko."""
            try:
                async for chunk in audio_stream:
                    await ws.send(chunk)
                # Signal end of stream
                await ws.send(json.dumps({"type": "CloseStream"}))
            except Exception as e:
                logger.error("deepgram_send_error", error=str(e))

        async def _recv_transcripts(ws):
            """Transcripts receive karo Deepgram se."""
            try:
                async for message in ws:
                    data = json.loads(message)
                    msg_type = data.get("type", "")

                    if msg_type == "Results":
                        is_final = data.get("is_final", False)
                        speech_final = data.get("speech_final", False)

                        try:
                            alt = data["channel"]["alternatives"][0]
                            transcript = alt.get("transcript", "").strip()
                            confidence = alt.get("confidence", 0.0)
                            words = alt.get("words", [])

                            start = words[0]["start"] if words else 0.0
                            end = words[-1]["end"] if words else 0.0
                        except (KeyError, IndexError):
                            continue

                        if not transcript:
                            continue

                        if is_final or speech_final:
                            await results_queue.put(
                                TranscriptChunk(
                                    text=transcript,
                                    start=start,
                                    end=end,
                                    confidence=confidence,
                                    language=self.language,
                                )
                            )
                        else:
                            # Interim result — callback bhejo
                            if on_interim:
                                try:
                                    on_interim(transcript)
                                except Exception:
                                    pass

                    elif msg_type == "Metadata":
                        logger.debug("deepgram_metadata", data=data)

                    elif msg_type == "UtteranceEnd":
                        logger.debug("deepgram_utterance_end")

            except Exception as e:
                logger.error("deepgram_recv_error", error=str(e))
            finally:
                await results_queue.put(None)  # Sentinel

        try:
            async with websockets.connect(
                ws_url,
                additional_headers=headers,
                ping_interval=20,
                ping_timeout=10,
            ) as ws:
                # Send + receive concurrently
                send_task = asyncio.create_task(_send_audio(ws))
                recv_task = asyncio.create_task(_recv_transcripts(ws))

                while True:
                    item = await results_queue.get()
                    if item is None:
                        break
                    yield item

                await asyncio.gather(send_task, recv_task, return_exceptions=True)

        except Exception as e:
            logger.error("deepgram_ws_connect_error", error=str(e))

    # ── REST API (batch, single chunk) ───────────────────────────────────────

    async def _transcribe_chunk(self, raw_bytes: bytes) -> list[TranscriptChunk]:
        """Batch REST transcription — short audio clips ke liye."""
        url = (
            f"{DEEPGRAM_REST_URL}"
            f"?model={self.model}"
            f"&language={self.language}"
            f"&smart_format=true"
            f"&channels=1"
        )
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": (
                f"audio/x-raw;encoding={self.encoding};"
                f"sample_rate={self.sample_rate};channels=1"
            ),
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(url, content=raw_bytes, headers=headers)
                response.raise_for_status()
                data = response.json()

                if not data.get("results") or not data["results"].get("channels"):
                    return []

                alternatives = data["results"]["channels"][0]["alternatives"]
                if not alternatives:
                    return []

                transcript = alternatives[0].get("transcript", "").strip()
                confidence = alternatives[0].get("confidence", 0.0)
                words = alternatives[0].get("words", [])

                start = words[0]["start"] if words else 0.0
                end = words[-1]["end"] if words else 0.0

                if transcript:
                    return [
                        TranscriptChunk(
                            text=transcript,
                            start=start,
                            end=end,
                            confidence=confidence,
                            language=self.language,
                        )
                    ]
                return []

            except Exception as e:
                logger.error("deepgram_rest_error", error=str(e))
                return []

    async def transcribe_file(self, audio_path: str) -> list[TranscriptChunk]:
        """File se transcription karo."""
        try:
            with open(audio_path, "rb") as f:
                audio_data = f.read()
            return await self._transcribe_chunk(audio_data)
        except Exception as e:
            logger.error("deepgram_file_read_error", error=str(e))
            return []
