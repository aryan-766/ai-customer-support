"""
TTS Provider Factory.
"""

from app.config import settings
from app.core.tts.base import BaseTTSProvider
from app.core.tts.kokoro import KokoroTTS


class TTSFactory:
    """Factory to fetch active TTS provider based on config."""

    @staticmethod
    def get_provider() -> BaseTTSProvider:
        provider_name = settings.TTS_PROVIDER.lower()
        if provider_name == "kokoro":
            return KokoroTTS()
        else:
            raise ValueError(f"Unsupported TTS provider: {settings.TTS_PROVIDER}")
