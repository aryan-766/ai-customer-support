"""
Abstract TTS provider — swap Kokoro for any cloud provider (Google/ElevenLabs/etc.) later.
"""

from abc import ABC, abstractmethod
from typing import AsyncIterator


class BaseTTSProvider(ABC):
    """
    All TTS providers must implement this interface.
    Swapping providers = change one env variable.
    """

    @abstractmethod
    async def synthesize(self, text: str, voice: str) -> bytes:
        """
        Synthesize text into complete audio bytes.
        Returns PCM16 audio bytes.
        """
        ...

    @abstractmethod
    async def synthesize_stream(
        self, text: str, voice: str
    ) -> AsyncIterator[bytes]:
        """
        Stream synthesized audio chunks.
        Yields PCM16 audio byte chunks.
        """
        ...
