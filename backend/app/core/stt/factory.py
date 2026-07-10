from app.config import settings
from app.core.stt.base import BaseSTTProvider

class STTFactory:
    _provider = None
    
    @classmethod
    def get_provider(cls) -> BaseSTTProvider:
        if cls._provider is None:
            provider_name = getattr(settings, "STT_PROVIDER", "faster_whisper").lower()
            if provider_name == "faster_whisper":
                from app.core.stt.faster_whisper import FasterWhisperSTT
                cls._provider = FasterWhisperSTT()
            elif provider_name == "deepgram":
                from app.core.stt.deepgram_stt import DeepgramSTT
                cls._provider = DeepgramSTT()
            else:
                raise ValueError(f"Unsupported STT provider: {provider_name}")
        return cls._provider
