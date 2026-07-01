"""
Redis manager — async client for cache, sessions, pub/sub, and transcript streaming.
"""

import json
from typing import Any, Optional, AsyncIterator
import redis.asyncio as aioredis
import structlog

from app.config import settings

logger = structlog.get_logger(__name__)


class RedisManager:
    """
    Centralized Redis client.
    Provides helpers for:
      - Call state (active call data)
      - Live transcript streaming (List + Pub/Sub)
      - Session management
      - Generic cache
    """

    def __init__(self):
        self._client: Optional[aioredis.Redis] = None
        self._pubsub_client: Optional[aioredis.Redis] = None

    async def connect(self):
        self._client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        self._pubsub_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        await self._client.ping()
        logger.info("redis_connected")

    async def disconnect(self):
        if self._client:
            await self._client.aclose()
        if self._pubsub_client:
            await self._pubsub_client.aclose()

    @property
    def client(self) -> aioredis.Redis:
        if not self._client:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    # ── Call State ─────────────────────────────────────────────────────────────

    async def save_call_state(self, call_id: str, state: dict) -> None:
        key = f"call:{call_id}:state"
        await self.client.set(key, json.dumps(state), ex=settings.REDIS_TTL_CALL_STATE)

    async def get_call_state(self, call_id: str) -> Optional[dict]:
        key = f"call:{call_id}:state"
        data = await self.client.get(key)
        return json.loads(data) if data else None

    async def update_call_state(self, call_id: str, updates: dict) -> dict:
        """Partial update: merges updates into existing state."""
        state = await self.get_call_state(call_id) or {}
        state.update(updates)
        await self.save_call_state(call_id, state)
        return state

    async def delete_call_state(self, call_id: str) -> None:
        await self.client.delete(f"call:{call_id}:state")

    # ── Live Transcript ────────────────────────────────────────────────────────

    async def append_transcript(self, call_id: str, entry: dict) -> None:
        """Append one transcript entry and publish for real-time streaming."""
        key = f"call:{call_id}:transcript"
        await self.client.rpush(key, json.dumps(entry))
        await self.client.expire(key, settings.REDIS_TTL_CALL_STATE)
        # Publish for WebSocket subscribers
        await self.publish(f"transcript.{call_id}", entry)

    async def get_transcript(self, call_id: str) -> list[dict]:
        key = f"call:{call_id}:transcript"
        entries = await self.client.lrange(key, 0, -1)
        return [json.loads(e) for e in entries]

    # ── Session Management ─────────────────────────────────────────────────────

    async def save_session(self, session_id: str, data: dict) -> None:
        key = f"session:{session_id}"
        await self.client.set(key, json.dumps(data), ex=settings.REDIS_TTL_SESSION)

    async def get_session(self, session_id: str) -> Optional[dict]:
        key = f"session:{session_id}"
        data = await self.client.get(key)
        return json.loads(data) if data else None

    async def delete_session(self, session_id: str) -> None:
        await self.client.delete(f"session:{session_id}")

    # ── Pub/Sub ────────────────────────────────────────────────────────────────

    async def publish(self, channel: str, message: dict) -> None:
        await self.client.publish(channel, json.dumps(message))

    async def subscribe(self, *channels: str):
        """Returns an active pubsub object for listening."""
        pubsub = self._pubsub_client.pubsub()
        await pubsub.subscribe(*channels)
        return pubsub

    # ── Generic Cache ──────────────────────────────────────────────────────────

    async def cache_set(self, key: str, value: Any, ttl: int = 300) -> None:
        await self.client.set(key, json.dumps(value), ex=ttl)

    async def cache_get(self, key: str) -> Optional[Any]:
        data = await self.client.get(key)
        return json.loads(data) if data else None


# Singleton instance
redis_manager = RedisManager()
