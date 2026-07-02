"""
Kokoro TTS provider — wraps hexgrad's Kokoro models locally.
Supports both English and Hindi voice synthesis.
"""

import asyncio
import numpy as np
import structlog
from typing import AsyncIterator, Optional
from kokoro import KPipeline

from app.config import settings
from app.core.tts.base import BaseTTSProvider

logger = structlog.get_logger(__name__)


class KokoroTTS(BaseTTSProvider):
    """
    Synthesizes speech using Kokoro models.
    Automatically chooses the appropriate language pipeline (English or Hindi).
    """

    def __init__(self):
        self.default_voice = settings.TTS_VOICE
        self.sample_rate = settings.TTS_SAMPLE_RATE
        # Lazy initialization of pipelines to save memory
        self._pipelines = {}

    def _get_pipeline(self, lang: str) -> KPipeline:
        if lang not in self._pipelines:
            logger.info("initializing_kokoro_pipeline", lang=lang)
            # lang_code='a' for American English, 'h' for Hindi
            lang_code = "h" if lang == "hi" else "a"
            self._pipelines[lang] = KPipeline(lang_code=lang_code)
            logger.info("kokoro_pipeline_initialized", lang=lang)
        return self._pipelines[lang]

    def _detect_lang_from_text_or_voice(self, text: str, voice: str) -> tuple[str, str]:
        """Detect if we should use Hindi or English pipeline & voice packs."""
        # If voice starts with 'h', it's a Hindi voice pack
        if voice.startswith("h"):
            return "hi", voice

        # Search for Devanagari (Hindi) characters in the text (Unicode block U+0900 to U+097F)
        for char in text:
            if "\u0900" <= char <= "\u097f":
                # Default Hindi female voice if current voice pack is English-based
                target_voice = voice if voice.startswith("h") else "hf_alpha"
                return "hi", target_voice

        return "en", voice

    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """Synthesize text to complete PCM16 audio bytes."""
        voice = voice or self.default_voice
        lang, active_voice = self._detect_lang_from_text_or_voice(text, voice)
        pipeline = self._get_pipeline(lang)

        loop = asyncio.get_event_loop()

        def _run():
            generator = pipeline(text, voice=active_voice, speed=1.0)
            audio_segments = []
            for _, _, audio in generator:
                if audio is not None and len(audio) > 0:
                    audio_segments.append(audio)
            if not audio_segments:
                return b""
            full_audio = np.concatenate(audio_segments)
            # Scale float32 [-1.0, 1.0] to int16 PCM
            audio_int16 = (full_audio * 32767).astype(np.int16)
            return audio_int16.tobytes()

        return await loop.run_in_executor(None, _run)

    async def synthesize_stream(
        self, text: str, voice: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """Stream synthesized PCM16 audio chunks in real-time."""
        voice = voice or self.default_voice
        lang, active_voice = self._detect_lang_from_text_or_voice(text, voice)
        pipeline = self._get_pipeline(lang)

        loop = asyncio.get_event_loop()

        def _run_generator():
            return pipeline(text, voice=active_voice, speed=1.0)

        # Initialize the synchronous generator in executor
        generator = await loop.run_in_executor(None, _run_generator)

        def _get_next():
            try:
                return next(generator)
            except StopIteration:
                return None

        while True:
            # Yield items block-free by fetching them in the thread pool
            item = await loop.run_in_executor(None, _get_next)
            if item is None:
                break

            _, _, audio = item
            if audio is not None and len(audio) > 0:
                audio_int16 = (audio * 32767).astype(np.int16)
                yield audio_int16.tobytes()
