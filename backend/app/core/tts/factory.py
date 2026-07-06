"""
TTS Provider Factory.
"""

from app.config import settings
from app.core.tts.base import BaseTTSProvider


class TTSFactory:
    """Factory to fetch active TTS provider based on config."""
    
    _provider = None

    @classmethod
    def get_provider(cls) -> BaseTTSProvider:
        if cls._provider is None:
            provider_name = settings.TTS_PROVIDER.lower()
            if provider_name == "kokoro":
                from app.core.tts.kokoro import KokoroTTS
                cls._provider = KokoroTTS()
            elif provider_name == "pocket":
                from app.core.tts.pocket import PocketTTS
                cls._provider = PocketTTS()
            else:
                raise ValueError(f"Unsupported TTS provider: {settings.TTS_PROVIDER}")
        return cls._provider
