"""Async Redis cache client (infra/CLAUDE.md §캐싱 규칙).

Wraps redis.asyncio with graceful degradation: if REDIS_URL is unset or the
`redis` package is not installed, all operations silently no-op so that the
rest of the application continues without a cache.

All SET calls must provide an explicit TTL (ex=) — TTL-less keys are
forbidden per demo/CLAUDE.md §캐싱 규칙.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)


class RedisCache:
    """Minimal async key-value cache backed by Redis.

    Time: O(1) per get/set
    Edge: REDIS_URL unset or redis package absent → get() returns None, set() no-ops.
    Edge: connection failure during operation → logged at DEBUG, caller unaffected.
    """

    def __init__(self, url: str | None = None) -> None:
        self._url = url or os.getenv("REDIS_URL", "")
        self._client: object | None = None  # lazy
        self._unavailable = False  # set True once we know Redis is not reachable

    async def _ensure_client(self) -> object | None:
        if self._unavailable:
            return None
        if self._client is not None:
            return self._client
        if not self._url:
            self._unavailable = True
            return None
        try:
            import redis.asyncio as aioredis  # type: ignore[import-not-found]
        except ImportError:
            logger.debug("redis package not installed; cache disabled")
            self._unavailable = True
            return None
        self._client = aioredis.from_url(self._url, decode_responses=True)
        return self._client

    async def get(self, key: str) -> str | None:
        """Return the cached value for `key`, or None on miss / unavailable."""
        client = await self._ensure_client()
        if client is None:
            return None
        try:
            return await client.get(key)  # type: ignore[attr-defined]
        except Exception:
            logger.debug("redis.get failed key=%s", key, exc_info=True)
            return None

    async def set(self, key: str, value: str, *, ex: int) -> None:
        """Store `value` under `key` with TTL of `ex` seconds.

        No-ops silently when Redis is unavailable — callers never need to
        handle the failure, since caching is always best-effort.
        """
        client = await self._ensure_client()
        if client is None:
            return
        try:
            await client.set(key, value, ex=ex)  # type: ignore[attr-defined]
        except Exception:
            logger.debug("redis.set failed key=%s", key, exc_info=True)

    async def aclose(self) -> None:
        if self._client is not None:
            await self._client.aclose()  # type: ignore[attr-defined]
            self._client = None
