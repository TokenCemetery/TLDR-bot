"""Telegram request middleware that waits out Bot API flood control."""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from aiogram.client.session.middlewares.base import BaseRequestMiddleware, NextRequestMiddlewareType
from aiogram.exceptions import TelegramRetryAfter
from aiogram.methods.base import TelegramType

if TYPE_CHECKING:
    from aiogram import Bot
    from aiogram.methods import Response, TelegramMethod

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 3


class RetryAfterMiddleware(BaseRequestMiddleware):
    """Retries Bot API requests rejected with ``TelegramRetryAfter`` after the requested delay.

    Without it a flood-control response on the final reply discards a summary that was already generated.
    """

    def __init__(self, max_retries: int = DEFAULT_MAX_RETRIES) -> None:
        self.max_retries = max_retries

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        """Send the request, sleeping and retrying while Telegram answers with flood control."""
        for attempt in range(1, self.max_retries + 1):
            try:
                return await make_request(bot, method)
            except TelegramRetryAfter as exc:
                logger.warning(
                    "Telegram flood control, retrying",
                    extra={
                        "method": type(method).__name__,
                        "retry_after": exc.retry_after,
                        "attempt": attempt,
                    },
                )
                await asyncio.sleep(exc.retry_after)
        return await make_request(bot, method)
