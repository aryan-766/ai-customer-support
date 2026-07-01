"""
Ollama LLM provider — wraps Qwen2.5 3B running locally via Ollama.
Supports streaming responses for real-time voice output.
"""

import asyncio
from typing import AsyncIterator, Optional

import httpx
import structlog

from app.config import settings
from app.core.llm.base import BaseLLMProvider, LLMResponse

logger = structlog.get_logger(__name__)


class OllamaLLM(BaseLLMProvider):
    """
    Calls Ollama REST API — fully async with streaming support.
    Ollama runs Qwen2.5 3B GGUF (Q4_K_M quantization).
    """

    def __init__(self):
        self.base_url = settings.LLM_BASE_URL
        self.model = settings.LLM_MODEL
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self.timeout = settings.LLM_TIMEOUT

    async def generate(
        self, prompt: str, system: Optional[str] = None
    ) -> LLMResponse:
        """Single-shot generation (non-streaming)."""
        messages = self._build_messages(prompt, system)
        return await self.chat(messages)

    async def generate_stream(
        self, prompt: str, system: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Streaming generation — yields text tokens as they arrive."""
        messages = self._build_messages(prompt, system)
        async for token in self.chat_stream(messages):
            yield token

    async def chat(
        self, messages: list[dict], system: Optional[str] = None
    ) -> LLMResponse:
        """Chat completion (non-streaming)."""
        if system:
            messages = [{"role": "system", "content": system}] + messages

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                    },
                },
            )
            response.raise_for_status()
            data = response.json()

        return LLMResponse(
            text=data["message"]["content"],
            model=data.get("model", self.model),
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
        )

    async def chat_stream(
        self, messages: list[dict], system: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Streaming chat — yields string tokens in real-time."""
        if system:
            messages = [{"role": "system", "content": system}] + messages

        import json
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "stream": True,
                    "options": {
                        "temperature": self.temperature,
                        "num_predict": self.max_tokens,
                    },
                },
            ) as response:
                async for line in response.aiter_lines():
                    if line:
                        try:
                            chunk = json.loads(line)
                            token = chunk.get("message", {}).get("content", "")
                            if token:
                                yield token
                        except json.JSONDecodeError:
                            continue

    async def is_available(self) -> bool:
        """Check if Ollama server is running."""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.get(f"{self.base_url}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    def _build_messages(self, prompt: str, system: Optional[str]) -> list[dict]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return messages
