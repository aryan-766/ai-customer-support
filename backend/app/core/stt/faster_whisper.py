"""
Faster-Whisper STT implementation.
Streaming: audio buffer → VAD → Whisper chunks → transcript events.
"""

import asyncio
import io
import tempfile
from typing import AsyncIterator

import numpy as np
import structlog

from app.config import settings
from app.core.stt.base import BaseSTTProvider, TranscriptChunk
from app.core.models_loader import ModelRegistry

logger = structlog.get_logger(__name__)

SAMPLE_RATE = 16000       # Whisper expects 16kHz
CHUNK_DURATION_S = 3.0    # Process every 3 seconds of audio


class FasterWhisperSTT(BaseSTTProvider):
    """
    Streams audio in chunks → transcribes each chunk with Faster-Whisper.
    Uses the pre-loaded model from ModelRegistry (no double loading).
    """

    def __init__(self):
        self._model = ModelRegistry().whisper

    async def transcribe_stream(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[TranscriptChunk]:
        """
        Accumulates audio into 3-second buffers, transcribes each buffer,
        yields TranscriptChunk events in real-time.
        """
        buffer = b""
        chunk_size = int(SAMPLE_RATE * 2 * CHUNK_DURATION_S)  # 16-bit samples

        async for raw_audio in audio_stream:
            buffer += raw_audio

            while len(buffer) >= chunk_size:
                chunk, buffer = buffer[:chunk_size], buffer[chunk_size:]

                chunks = await asyncio.get_event_loop().run_in_executor(
                    None, self._transcribe_chunk, chunk
                )
                for c in chunks:
                    yield c

        # Transcribe any remaining audio
        if buffer:
            chunks = await asyncio.get_event_loop().run_in_executor(
                None, self._transcribe_chunk, buffer
            )
            for c in chunks:
                yield c

    def _transcribe_chunk(self, raw_bytes: bytes) -> list[TranscriptChunk]:
        """Synchronous transcription of one audio chunk."""
        try:
            # Convert bytes to float32 numpy array (PCM16 → float32)
            audio_np = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)
            audio_np /= 32768.0   # normalize to [-1, 1]

            segments, info = self._model.transcribe(
                audio_np,
                language=None,              # auto-detect
                beam_size=5,
                vad_filter=True,            # skip silence
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    threshold=0.5,
                ),
            )

            result = []
            for seg in segments:
                if seg.text.strip():
                    result.append(TranscriptChunk(
                        text=seg.text.strip(),
                        start=seg.start,
                        end=seg.end,
                        confidence=float(getattr(seg, "avg_logprob", 0.0)),
                        language=info.language,
                    ))
            return result

        except Exception as e:
            logger.error("stt_chunk_error", error=str(e))
            return []

    async def transcribe_file(self, audio_path: str) -> list[TranscriptChunk]:
        """Transcribe a complete audio file (used for post-call processing)."""
        def _run():
            segments, info = self._model.transcribe(
                audio_path,
                language=None,
                beam_size=5,
                vad_filter=True,
            )
            return [
                TranscriptChunk(
                    text=seg.text.strip(),
                    start=seg.start,
                    end=seg.end,
                    confidence=float(getattr(seg, "avg_logprob", 0.0)),
                    language=info.language,
                )
                for seg in segments if seg.text.strip()
            ]

        return await asyncio.get_event_loop().run_in_executor(None, _run)
