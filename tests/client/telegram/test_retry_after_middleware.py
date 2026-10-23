from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.exceptions import TelegramRetryAfter
from aiogram.methods import SendMessage
from src.client.telegram.retry_after_middleware import RetryAfterMiddleware

FLOOD_RETRY_AFTER = 8
MAX_RETRIES = 2


def _retry_after(method: SendMessage, seconds: int) -> TelegramRetryAfter:
    return TelegramRetryAfter(method=method, message="Too Many Requests", retry_after=seconds)


@pytest.mark.asyncio
async def test_retries_after_flood_control() -> None:
    method = SendMessage(chat_id=1, text="hi")
    response = MagicMock()
    make_request = AsyncMock(side_effect=[_retry_after(method, FLOOD_RETRY_AFTER), response])

    with patch("src.client.telegram.retry_after_middleware.asyncio.sleep", new=AsyncMock()) as sleep:
        result = await RetryAfterMiddleware()(make_request, MagicMock(), method)

    assert result is response
    sleep.assert_awaited_once_with(FLOOD_RETRY_AFTER)


@pytest.mark.asyncio
async def test_gives_up_after_max_retries() -> None:
    method = SendMessage(chat_id=1, text="hi")
    make_request = AsyncMock(side_effect=_retry_after(method, 1))

    with (
        patch("src.client.telegram.retry_after_middleware.asyncio.sleep", new=AsyncMock()),
        pytest.raises(TelegramRetryAfter),
    ):
        await RetryAfterMiddleware(max_retries=MAX_RETRIES)(make_request, MagicMock(), method)

    assert make_request.await_count == MAX_RETRIES + 1
