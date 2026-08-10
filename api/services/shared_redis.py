"""Optional Redis/Valkey access shared by chatbot runtime features.

The chatbot remains fully functional without Redis. When ``CHAT_REDIS_URL``
or ``REDIS_URL`` is configured, cache, conversation memory and rate limiting
can be shared by multiple API workers.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

logger = logging.getLogger(__name__)

try:  # Optional locally; installed by the production API requirements.
    import redis.asyncio as redis_async
except ImportError:  # pragma: no cover - exercised only in minimal installs.
    redis_async = None


class SharedRedis:
    """Small fail-soft wrapper around redis-py asyncio."""

    def __init__(self) -> None:
        self.url = (os.getenv("CHAT_REDIS_URL") or os.getenv("REDIS_URL") or "").strip()
        self._client: Any | None = None
        self._disabled_until = 0.0

    @property
    def configured(self) -> bool:
        return bool(self.url and redis_async is not None)

    def _connection(self):
        if not self.configured or time.monotonic() < self._disabled_until:
            return None
        if self._client is None:
            self._client = redis_async.from_url(
                self.url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=1.5,
                socket_timeout=1.5,
                health_check_interval=30,
            )
        return self._client

    def _degrade(self, exc: Exception) -> None:
        self._disabled_until = time.monotonic() + 30
        logger.warning("chat_redis_degraded error=%s", type(exc).__name__)

    async def get_json(self, key: str) -> dict[str, Any] | list[Any] | None:
        client = self._connection()
        if client is None:
            return None
        try:
            raw = await client.get(key)
            if not raw:
                return None
            value = json.loads(raw)
            return value if isinstance(value, (dict, list)) else None
        except Exception as exc:  # Redis must never take the chatbot down.
            self._degrade(exc)
            return None

    async def set_json(self, key: str, value: Any, ttl_seconds: int) -> bool:
        client = self._connection()
        if client is None:
            return False
        try:
            await client.set(
                key,
                json.dumps(value, ensure_ascii=False, separators=(",", ":")),
                ex=max(1, ttl_seconds),
            )
            return True
        except Exception as exc:
            self._degrade(exc)
            return False

    async def delete(self, key: str) -> bool:
        client = self._connection()
        if client is None:
            return False
        try:
            await client.delete(key)
            return True
        except Exception as exc:
            self._degrade(exc)
            return False

    async def increment_window(self, key: str, ttl_seconds: int) -> int | None:
        """Atomically increment a fixed-window counter when Redis is available."""
        client = self._connection()
        if client is None:
            return None
        try:
            value = int(await client.incr(key))
            if value == 1:
                await client.expire(key, max(1, ttl_seconds))
            return value
        except Exception as exc:
            self._degrade(exc)
            return None


shared_redis = SharedRedis()
