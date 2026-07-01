"""
Abstract STT provider — swap Faster-Whisper for any cloud provider later.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator


@dataclass
class TranscriptChunk:
    text: str
    start: float
    end: float
    confidence: float
    language: str


class BaseSTTProvider(ABC):
    """
    All STT providers must implement this interface.
    Swapping providers = change one env variable.
    """

    @abstractmethod
    async def transcribe_stream(
        self, audio_stream: AsyncIterator[bytes]
    ) -> AsyncIterator[TranscriptChunk]:
        """Streaming transcription — yields chunks as they're ready."""
        ...

    @abstractmethod
    async def transcribe_file(self, audio_path: str) -> list[TranscriptChunk]:
        """Transcribe an entire audio file."""
        ...
