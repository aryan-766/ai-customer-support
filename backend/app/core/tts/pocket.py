"""
Pocket TTS provider — Kyutai Labs' lightweight CPU-optimized TTS.
Supports voice cloning from a .wav sample and multiple built-in voices.

Built-in voices: alba, jessica, ...
Voice cloning: pass path to a .wav file as voice_sample
"""

import asyncio
import io
import numpy as np
import structlog
from typing import AsyncIterator, Optional

from app.config import settings
from app.core.tts.base import BaseTTSProvider

logger = structlog.get_logger(__name__)


# Built-in Pocket TTS voices
POCKET_VOICES = [
    "alba",       # Clear female
    "jessica",    # Warm female
]


class PocketTTS(BaseTTSProvider):
    """
    Synthesizes speech using Pocket TTS (CPU-optimized, low-latency).
    Supports voice cloning by passing a path to a .wav file as 'voice'.
    """

    def __init__(self):
        self._model = None
        self.default_voice = settings.TTS_VOICE or "alba"
        self.sample_rate = 24000   # Pocket TTS outputs at 24kHz

    def _load_model(self):
        if self._model is None:
            logger.info("pocket_tts_loading_model")
            from pocket_tts import TTSModel
            self._model = TTSModel.load_model()
            logger.info("pocket_tts_model_ready",
                        sample_rate=self._model.sample_rate)
        return self._model

    def _get_voice_state(self, voice: str):
        """Get voice state — either a built-in name or a .wav path for cloning."""
        model = self._load_model()
        try:
            # Built-in voice or voice cloning from .wav
            state = model.get_state_for_audio_prompt(voice)
            return state
        except Exception as e:
            logger.warning("pocket_tts_voice_fallback",
                           requested=voice, error=str(e))
            # Fallback to default built-in
            return model.get_state_for_audio_prompt("alba")

    def _synthesize_sync(self, text: str, voice: str) -> bytes:
        """Synchronous synthesis — runs in thread pool."""
        import scipy.io.wavfile
        model = self._load_model()
        voice_state = self._get_voice_state(voice)

        audio_tensor = model.generate_audio(voice_state, text)

        # Convert tensor → numpy → PCM16 bytes
        if hasattr(audio_tensor, "numpy"):
            audio_np = audio_tensor.numpy()
        elif hasattr(audio_tensor, "cpu"):
            audio_np = audio_tensor.cpu().numpy()
        else:
            audio_np = np.array(audio_tensor)

        # Normalize float32 → int16 if needed
        if audio_np.dtype == np.float32:
            audio_int16 = (audio_np * 32767).astype(np.int16)
        else:
            audio_int16 = audio_np.astype(np.int16)

        return audio_int16.tobytes()

    async def synthesize(self, text: str, voice: Optional[str] = None) -> bytes:
        """Synthesize full text → PCM16 bytes."""
        voice = voice or self.default_voice
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._synthesize_sync, text, voice)

    async def synthesize_stream(
        self, text: str, voice: Optional[str] = None
    ) -> AsyncIterator[bytes]:
        """
        Stream synthesized audio.
        Pocket TTS generates complete audio at once, so we yield it in
        one chunk (latency is still very low on CPU).
        """
        voice = voice or self.default_voice
        audio_bytes = await self.synthesize(text, voice)

        # Yield in ~50ms chunks to simulate streaming
        chunk_size = int(self.sample_rate * 2 * 0.05)   # 50ms of PCM16
        for i in range(0, len(audio_bytes), chunk_size):
            yield audio_bytes[i: i + chunk_size]
            await asyncio.sleep(0)   # yield control
