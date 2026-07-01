"""
LLM abstract base + Ollama (Qwen2.5) implementation.
Swap to OpenAI/Gemini by changing LLM_PROVIDER env variable.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Optional


@dataclass
class LLMResponse:
    text: str
    model: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    finish_reason: str = "stop"


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system: Optional[str] = None) -> LLMResponse:
        ...

    @abstractmethod
    async def generate_stream(
        self, prompt: str, system: Optional[str] = None
    ) -> AsyncIterator[str]:
        ...

    @abstractmethod
    async def chat(
        self, messages: list[dict], system: Optional[str] = None
    ) -> LLMResponse:
        ...
