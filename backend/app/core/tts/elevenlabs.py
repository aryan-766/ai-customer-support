"""
ElevenLabs TTS provider.
"""

import os
import httpx
from typing import AsyncIterator
import structlog
from app.config import settings
from app.core.tts.base import BaseTTSProvider

logger = structlog.get_logger(__name__)

class ElevenLabsTTS(BaseTTSProvider):
    def __init__(self):
        self.api_key = getattr(settings, "ELEVENLABS_API_KEY", os.environ.get("ELEVENLABS_API_KEY", ""))
        self.voice_id = getattr(settings, "ELEVENLABS_VOICE_ID", os.environ.get("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")) # Default Rachel
        self.base_url = "https://api.elevenlabs.io/v1"
        self.model_id = "eleven_monolingual_v1"
        
    async def synthesize(self, text: str, voice: str = None) -> bytes:
        voice_id = voice or self.voice_id
        url = f"{self.base_url}/text-to-speech/{voice_id}?output_format=pcm_16000_16"
        
        headers = {
            "Accept": "audio/pcm",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        data = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=data, headers=headers)
                response.raise_for_status()
                return response.content
            except Exception as e:
                logger.error("elevenlabs_tts_error", error=str(e))
                return b""

    async def synthesize_stream(self, text: str, voice: str = None) -> AsyncIterator[bytes]:
        voice_id = voice or self.voice_id
        url = f"{self.base_url}/text-to-speech/{voice_id}/stream?output_format=pcm_16000_16"
        
        headers = {
            "Accept": "audio/pcm",
            "Content-Type": "application/json",
            "xi-api-key": self.api_key
        }
        
        data = {
            "text": text,
            "model_id": self.model_id,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                async with client.stream("POST", url, json=data, headers=headers) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        yield chunk
            except Exception as e:
                logger.error("elevenlabs_tts_stream_error", error=str(e))
