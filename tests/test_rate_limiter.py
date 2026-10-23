import asyncio

import pytest
from src.cache import InMemoryCacheProvider
from src.rate_limiter import UserRateLimiter


@pytest.mark.asyncio
async def test_user_rate_limiter_not_limited() -> None:
    limiter = UserRateLimiter(provider=InMemoryCacheProvider(), cooldown_seconds=1)

    is_limited = await limiter.is_limited(123)
    assert is_limited is False

    is_limited = await limiter.is_limited(123)
    assert is_limited is True


@pytest.mark.asyncio
async def test_user_rate_limiter_different_users() -> None:
    limiter = UserRateLimiter(provider=InMemoryCacheProvider(), cooldown_seconds=1)

    is_limited_user1 = await limiter.is_limited(123)
    is_limited_user2 = await limiter.is_limited(456)

    assert is_limited_user1 is False
    assert is_limited_user2 is False


@pytest.mark.asyncio
async def test_user_rate_limiter_after_cooldown() -> None:
    limiter = UserRateLimiter(provider=InMemoryCacheProvider(), cooldown_seconds=1)

    is_limited = await limiter.is_limited(123)
    assert is_limited is False

    is_limited = await limiter.is_limited(123)
    assert is_limited is True

    await asyncio.sleep(1.1)

    is_limited = await limiter.is_limited(123)
    assert is_limited is False
