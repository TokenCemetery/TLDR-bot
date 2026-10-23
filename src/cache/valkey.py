"""
Valkey cache provider.

Supports multiple compression methods with automatic detection.
"""

import asyncio
import logging
from typing import Any

from valkey.asyncio import Valkey
from valkey.exceptions import ConnectionError as ValkeyConnectionError

from .base import CacheProvider

logger = logging.getLogger(__name__)


class ValkeyProvider(CacheProvider):
    """
    Valkey-based cache provider, utilizing atomic operations and TTL.
    Logs warnings on connection errors without throwing exceptions.

    Supports multiple compression methods with automatic detection via prefix.
    """

    def __init__(self, valkey_url: str, compression_method: str = "gzip") -> None:
        super().__init__(compression_method)
        self.valkey_url = valkey_url
        self._valkey: Valkey | None = None
        self._timeout = 0.200
        self._init_lock = asyncio.Lock()

    async def _get_client(self) -> Valkey:
        """Lazy initialization of the Valkey client with double-checked locking."""
        if self._valkey is None:
            async with self._init_lock:
                if self._valkey is None:
                    self._valkey = Valkey.from_url(self.valkey_url)
        return self._valkey

    async def _safe_execute(self, coro_fn: Any) -> Any:
        try:
            return await asyncio.wait_for(coro_fn(), timeout=self._timeout)
        except TimeoutError:
            logger.warning("Valkey timeout")
            return None
        except (ValkeyConnectionError, ConnectionError, OSError) as e:
            logger.warning(f"Valkey connection error: {e}")
            return None
        except Exception as e:
            logger.warning(f"Valkey operation failed: {e}")
            return None

    async def is_rate_limited(self, user_id: int, window_seconds: int) -> bool:
        """Atomic rate limiter using INCR and EXPIRE."""

        async def _valkey_rate_limit() -> bool:
            client = await self._get_client()
            key = f"user:{user_id}:limit"

            pipeline = client.pipeline()
            pipeline.incr(key)
            pipeline.expire(key, window_seconds, nx=True)
            result = await pipeline.execute()

            count = result[0]
            if count > 1:
                return True
            return False

        return await self._safe_execute(_valkey_rate_limit) or False

    async def get(self, key: str) -> str | None:
        async def _valkey_get() -> str | None:
            client = await self._get_client()
            cache_key = f"{key}:{self._compression_method.value}"
            val = await client.get(cache_key)
            if val is not None:
                return self._decode_text(val)
            return None

        res: str | None = await self._safe_execute(_valkey_get)
        return res

    async def put(self, key: str, text: str, ttl_seconds: int) -> None:
        async def _valkey_set() -> None:
            client = await self._get_client()
            cache_key = f"{key}:{self._compression_method.value}"
            compressed = self._encode_text(text)
            await client.setex(cache_key, ttl_seconds, compressed)

        await self._safe_execute(_valkey_set)

    async def get_dict(self, key: str) -> dict[str, Any] | None:
        async def _valkey_get() -> dict[str, Any] | None:
            client = await self._get_client()
            cache_key = f"{key}:{self._compression_method.value}"
            val = await client.get(cache_key)
            if val is not None:
                return self._decode_dict(val)
            return None

        res: dict[str, Any] | None = await self._safe_execute(_valkey_get)
        return res

    async def put_dict(self, key: str, data: dict[str, Any], ttl_seconds: int) -> None:
        async def _valkey_set() -> None:
            client = await self._get_client()
            cache_key = f"{key}:{self._compression_method.value}"
            compressed = self._encode_dict(data)
            await client.setex(cache_key, ttl_seconds, compressed)

        await self._safe_execute(_valkey_set)
