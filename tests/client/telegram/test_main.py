import inspect
import logging
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.client.telegram.main import main
from src.logger import configure_logging


def test_configure_logging_default() -> None:
    with (
        patch.dict(os.environ, {}, clear=True),
        patch("src.logger.logging.getLogger") as mock_get_logger,
        patch("src.logger.logging.StreamHandler") as mock_handler_class,
        patch("src.logger.os.getenv", return_value="INFO"),
    ):
        mock_root_logger = MagicMock()
        mock_httpx_logger = MagicMock()
        mock_handler = MagicMock()

        def get_logger_side_effect(name: str | None = None) -> MagicMock:
            if name == "httpx":
                return mock_httpx_logger
            return mock_root_logger

        mock_get_logger.side_effect = get_logger_side_effect
        mock_handler_class.return_value = mock_handler
        mock_root_logger.handlers = []

        configure_logging()

        mock_root_logger.setLevel.assert_called_with(logging.INFO)
        mock_root_logger.addHandler.assert_called_once_with(mock_handler)
        mock_handler.setLevel.assert_called_with(logging.INFO)
        mock_handler.setFormatter.assert_called_once()
        mock_httpx_logger.setLevel.assert_called_with(logging.WARNING)


def test_configure_logging_custom_level() -> None:
    with (
        patch.dict(os.environ, {"LOG_LEVEL": "DEBUG"}),
        patch("src.logger.logging.getLogger") as mock_get_logger,
        patch("src.logger.logging.StreamHandler") as mock_handler_class,
        patch("src.logger.os.getenv", return_value="DEBUG"),
    ):
        mock_root_logger = MagicMock()
        mock_httpx_logger = MagicMock()
        mock_handler = MagicMock()

        def get_logger_side_effect(name: str | None = None) -> MagicMock:
            if name == "httpx":
                return mock_httpx_logger
            return mock_root_logger

        mock_get_logger.side_effect = get_logger_side_effect
        mock_handler_class.return_value = mock_handler
        mock_root_logger.handlers = []

        configure_logging()

        mock_root_logger.setLevel.assert_called_with(logging.DEBUG)
        mock_root_logger.addHandler.assert_called_once_with(mock_handler)
        mock_handler.setLevel.assert_called_with(logging.DEBUG)


def test_configure_logging_invalid_level() -> None:
    with (
        patch.dict(os.environ, {"LOG_LEVEL": "INVALID_LEVEL"}),
        patch("src.logger.logging.getLogger") as mock_get_logger,
        patch("src.logger.logging.StreamHandler") as mock_handler_class,
        patch("src.logger.os.getenv", return_value="INVALID_LEVEL"),
    ):
        mock_root_logger = MagicMock()
        mock_httpx_logger = MagicMock()
        mock_handler = MagicMock()

        def get_logger_side_effect(name: str | None = None) -> MagicMock:
            if name == "httpx":
                return mock_httpx_logger
            return mock_root_logger

        mock_get_logger.side_effect = get_logger_side_effect
        mock_handler_class.return_value = mock_handler
        mock_root_logger.handlers = []

        configure_logging()

        mock_root_logger.setLevel.assert_called_with(logging.INFO)
        mock_root_logger.addHandler.assert_called_once_with(mock_handler)


def test_configure_logging_removes_existing_handlers() -> None:
    with (
        patch("src.logger.logging.getLogger") as mock_get_logger,
        patch("src.logger.logging.StreamHandler") as mock_handler_class,
        patch("src.logger.os.getenv", return_value="INFO"),
    ):
        mock_root_logger = MagicMock()
        mock_httpx_logger = MagicMock()
        mock_existing_handler = MagicMock()
        mock_handler = MagicMock()

        def get_logger_side_effect(name: str | None = None) -> MagicMock:
            if name == "httpx":
                return mock_httpx_logger
            return mock_root_logger

        mock_get_logger.side_effect = get_logger_side_effect
        mock_handler_class.return_value = mock_handler
        mock_root_logger.handlers = [mock_existing_handler]

        configure_logging()

        mock_root_logger.removeHandler.assert_called_with(mock_existing_handler)
        mock_root_logger.addHandler.assert_called_with(mock_handler)


def test_configure_logging_uses_custom_formatter() -> None:
    with (
        patch("src.logger.logging.getLogger") as mock_get_logger,
        patch("src.logger.logging.StreamHandler") as mock_handler_class,
        patch("src.logger.CustomFormatter") as mock_formatter_class,
        patch("src.logger.os.getenv", return_value="INFO"),
    ):
        mock_root_logger = MagicMock()
        mock_httpx_logger = MagicMock()
        mock_handler = MagicMock()
        mock_formatter = MagicMock()

        def get_logger_side_effect(name: str | None = None) -> MagicMock:
            if name == "httpx":
                return mock_httpx_logger
            return mock_root_logger

        mock_get_logger.side_effect = get_logger_side_effect
        mock_handler_class.return_value = mock_handler
        mock_formatter_class.return_value = mock_formatter
        mock_root_logger.handlers = []

        configure_logging()

        mock_formatter_class.assert_called_once()
        mock_handler.setFormatter.assert_called_once_with(mock_formatter)


def test_configure_logging_httpx_warning() -> None:
    with (
        patch("src.logger.logging.getLogger") as mock_get_logger,
        patch("src.logger.logging.StreamHandler") as mock_handler_class,
    ):
        mock_root_logger = MagicMock()
        mock_httpx_logger = MagicMock()
        mock_handler = MagicMock()

        def get_logger_side_effect(name: str | None = None) -> MagicMock:
            if name == "httpx":
                return mock_httpx_logger
            return mock_root_logger

        mock_get_logger.side_effect = get_logger_side_effect
        mock_handler_class.return_value = mock_handler
        mock_root_logger.handlers = []

        configure_logging()

        mock_httpx_logger.setLevel.assert_called_with(logging.WARNING)


@pytest.mark.asyncio
async def test_main_function_initializes_and_runs() -> None:
    with (
        patch("src.client.telegram.main.Settings") as mock_settings,
        patch("src.client.telegram.main.get_cache_provider") as mock_get_cache_provider,
        patch("src.client.telegram.main.UserRateLimiter") as mock_rate_limiter,
        patch("src.client.telegram.main.VideoDataLoader") as mock_loader,
        patch("src.client.telegram.main.OpenAISummarizer") as mock_summarizer,
        patch("src.client.telegram.main.Dispatcher") as mock_dispatcher_class,
        patch("src.client.telegram.main.Bot") as mock_bot_class,
    ):
        mock_settings_obj = MagicMock()
        mock_settings.from_env.return_value = mock_settings_obj

        mock_dp_obj = MagicMock()
        mock_dp_obj.start_polling = AsyncMock()
        mock_dispatcher_class.return_value = mock_dp_obj

        mock_bot_obj = MagicMock()
        mock_bot_class.return_value = mock_bot_obj

        await main()

        mock_settings.from_env.assert_called_once()
        mock_get_cache_provider.assert_called_once_with(mock_settings_obj)
        mock_dispatcher_class.assert_called_once()
        mock_dp_obj.include_routers.assert_called_once()
        mock_bot_class.assert_called_once()
        mock_dp_obj.start_polling.assert_called_once_with(
            mock_bot_obj,
            settings=mock_settings_obj,
            rate_limiter=mock_rate_limiter.return_value,
            loader=mock_loader.return_value,
            summarizer=mock_summarizer.return_value,
        )


def test_main_function_structure() -> None:
    assert callable(main)
    assert inspect.iscoroutinefunction(main)
    assert hasattr(main, "__name__")
    assert main.__name__ == "main"
