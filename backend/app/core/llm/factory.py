from app.config import settings
from app.core.llm.base import BaseLLMProvider
from app.core.llm.ollama import OllamaLLM

class LLMFactory:
    _instance: BaseLLMProvider = None

    @classmethod
    def get_provider(cls) -> BaseLLMProvider:
        if cls._instance is None:
            if settings.LLM_PROVIDER == "ollama":
                cls._instance = OllamaLLM()
            else:
                raise ValueError(f"Unknown LLM provider: {settings.LLM_PROVIDER}")
        return cls._instance
