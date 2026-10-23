"""
Local in-memory cache provider implementation.
"""

import asyncio
import time
from typing import Any

from .base import CacheProvider


class InMemoryCacheProvider(CacheProvider):
    """
    In-memory cache provider using dictionaries.
    Used when Valkey is not configured or unavailable.
    """

    def __init__(self, compression_method: str = "gzip") -> None:
        super().__init__(compression_method)
        self._rate_limits: dict[int, float] = {}
        self._rate_limit_lock = asyncio.Lock()

        self._cache: dict[str, tuple[bytes, float]] = {}
        self._cache_dict: dict[str, tuple[bytes, float]] = {}
        self._cache_lock = asyncio.Lock()

    async def is_rate_limited(self, user_id: int, window_seconds: int) -> bool:
        async with self._rate_limit_lock:
            now = time.monotonic()
            last_request = self._rate_limits.get(user_id)
            if last_request is not None and (now - last_request) < window_seconds:
                return True

            self._rate_limits[user_id] = now
            return False
        return False

    async def get(self, key: str) -> str | None:
        async with self._cache_lock:
            cache_key = f"{key}:{self._compression_method.value}"
            cached = self._cache.get(cache_key)
            if cached is None:
                return None

            compressed, expires_at = cached
            if time.monotonic() > expires_at:
                self._cache.pop(cache_key, None)
                return None

            return self._decode_text(compressed)

    async def put(self, key: str, text: str, ttl_seconds: int) -> None:
        async with self._cache_lock:
            cache_key = f"{key}:{self._compression_method.value}"
            compressed = self._encode_text(text)
            self._cache[cache_key] = (compressed, time.monotonic() + ttl_seconds)

    async def get_dict(self, key: str) -> dict[str, Any] | None:
        async with self._cache_lock:
            cache_key = f"{key}:{self._compression_method.value}"
            cached = self._cache_dict.get(cache_key)
            if cached is None:
                return None

            compressed, expires_at = cached
            if time.monotonic() > expires_at:
                self._cache_dict.pop(cache_key, None)
                return None

            return self._decode_dict(compressed)

    async def put_dict(self, key: str, data: dict[str, Any], ttl_seconds: int) -> None:
        async with self._cache_lock:
            cache_key = f"{key}:{self._compression_method.value}"
            compressed = self._encode_dict(data)
            self._cache_dict[cache_key] = (compressed, time.monotonic() + ttl_seconds)
