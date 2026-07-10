"""
Application configuration — all settings from environment variables.
Uses pydantic-settings for validation and type safety.
"""

from functools import lru_cache
import os
os.environ["TTS_VOICE"] = "alba"
from typing import Literal, List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ────────────────────────────────────────────────────────────────────
    APP_NAME: str = "Ambrane AI Voice Support"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change_me_in_production"
    LOG_LEVEL: str = "INFO"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]

    # ── PostgreSQL ─────────────────────────────────────────────────────────────
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "ambrane_support"
    POSTGRES_USER: str = "ambrane"
    POSTGRES_PASSWORD: str = "ambrane_secret_password"
    DATABASE_URL: str = (
        "postgresql+asyncpg://ambrane:ambrane_secret_password@localhost:5432/ambrane_support"
    )

    # ── Redis ──────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_TTL_CALL_STATE: int = 86400      # 24 hours
    REDIS_TTL_SESSION: int = 1800          # 30 minutes

    # ── Qdrant ─────────────────────────────────────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "ambrane_kb"

    # ── STT ────────────────────────────────────────────────────────────────────
    STT_PROVIDER: str = "deepgram"
    DEEPGRAM_API_KEY: str = ""
    STT_MODEL_SIZE: str = "base"
    STT_DEVICE: str = "cpu"
    STT_COMPUTE_TYPE: str = "int8"

    # ── LLM ────────────────────────────────────────────────────────────────────
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "qwen2.5:3b-instruct-q4_K_M"
    LLM_BASE_URL: str = "http://localhost:11434"
    LLM_TEMPERATURE: float = 0.3
    LLM_MAX_TOKENS: int = 512
    LLM_TIMEOUT: int = 30

    # ── TTS ────────────────────────────────────────────────────────────────────
    TTS_PROVIDER: str = "elevenlabs"
    TTS_VOICE: str = "alba" # Forced value
    ELEVENLABS_API_KEY: str = ""
    ELEVENLABS_VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"

    # ── HuggingFace Models ─────────────────────────────────────────────────────
    EMBED_MODEL: str = "BAAI/bge-small-en-v1.5"
    RERANK_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    SENTIMENT_MODEL: str = "cardiffnlp/twitter-roberta-base-sentiment-latest"
    INTENT_MODEL: str = "cross-encoder/nli-MiniLM2-L6-H768"
    LANG_DETECT_MODEL: str = "papluca/xlm-roberta-base-language-detection"
    MODELS_CACHE_DIR: str = ".models"

    # ── RAG ────────────────────────────────────────────────────────────────────
    KB_CHUNK_SIZE: int = 500
    KB_CHUNK_OVERLAP: int = 50
    KB_TOP_K: int = 10
    KB_RERANK_TOP_N: int = 3

    # ── Zoho Desk ──────────────────────────────────────────────────────────────
    ZOHO_CLIENT_ID: str = ""
    ZOHO_CLIENT_SECRET: str = ""
    ZOHO_REFRESH_TOKEN: str = ""
    ZOHO_ORG_ID: str = ""
    ZOHO_DESK_URL: str = "https://desk.zoho.in/api/v1"



    # ── Shopify (Warranty) ────────────────────────────────────────────────────
    SHOPIFY_SHOP_URL: str = ""
    SHOPIFY_ACCESS_TOKEN: str = ""



    # ── Notifications ─────────────────────────────────────────────────────────
    MSG91_AUTH_KEY: str = ""
    MSG91_SENDER_ID: str = "AMBRNE"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Global settings instance
settings = get_settings()
