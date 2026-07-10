"""
Deepgram STT provider.
"""
import os
import httpx
import structlog
from typing import AsyncIterator
from app.config import settings
from app.core.stt.base import BaseSTTProvider, TranscriptChunk

logger = structlog.get_logger(__name__)

SAMPLE_RATE = 16000
CHUNK_DURATION_S = 3.0

class DeepgramSTT(BaseSTTProvider):
    def __init__(self):
        self.api_key = getattr(settings, "DEEPGRAM_API_KEY", os.environ.get("DEEPGRAM_API_KEY", ""))
        
    async def transcribe_stream(self, audio_stream: AsyncIterator[bytes]) -> AsyncIterator[TranscriptChunk]:
        buffer = b""
        chunk_size = int(SAMPLE_RATE * 2 * CHUNK_DURATION_S)
        
        async for raw_audio in audio_stream:
            buffer += raw_audio
            while len(buffer) >= chunk_size:
                chunk, buffer = buffer[:chunk_size], buffer[chunk_size:]
                chunks = await self._transcribe_chunk(chunk)
                for c in chunks:
                    yield c
                    
        if buffer:
            chunks = await self._transcribe_chunk(buffer)
            for c in chunks:
                yield c
                
    async def _transcribe_chunk(self, raw_bytes: bytes) -> list[TranscriptChunk]:
        url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true"
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "audio/x-raw;encoding=linear16;sample_rate=16000;channels=1"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, content=raw_bytes, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                # Check if results exist
                if not data.get("results") or not data["results"].get("channels"):
                    return []
                
                alternatives = data["results"]["channels"][0]["alternatives"]
                if not alternatives:
                    return []
                    
                transcript = alternatives[0]["transcript"]
                confidence = alternatives[0]["confidence"]
                
                if transcript.strip():
                    return [TranscriptChunk(
                        text=transcript.strip(),
                        start=0.0,
                        end=3.0,
                        confidence=confidence,
                        language="en"
                    )]
                return []
            except Exception as e:
                logger.error("deepgram_stt_chunk_error", error=str(e))
                return []
                
    async def transcribe_file(self, audio_path: str) -> list[TranscriptChunk]:
        url = "https://api.deepgram.com/v1/listen?model=nova-2&smart_format=true"
        headers = {
            "Authorization": f"Token {self.api_key}",
        }
        async with httpx.AsyncClient() as client:
            try:
                with open(audio_path, "rb") as f:
                    audio_data = f.read()
                response = await client.post(url, content=audio_data, headers=headers)
                response.raise_for_status()
                data = response.json()
                
                if not data.get("results") or not data["results"].get("channels"):
                    return []
                    
                alternatives = data["results"]["channels"][0]["alternatives"]
                if not alternatives:
                    return []
                    
                transcript = alternatives[0]["transcript"]
                confidence = alternatives[0]["confidence"]
                
                if transcript.strip():
                    return [TranscriptChunk(
                        text=transcript.strip(),
                        start=0.0,
                        end=0.0,
                        confidence=confidence,
                        language="en"
                    )]
                return []
            except Exception as e:
                logger.error("deepgram_stt_file_error", error=str(e))
                return []
