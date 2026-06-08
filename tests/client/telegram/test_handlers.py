from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import ErrorEvent, Message, User
from src.client.telegram.handlers.commands import start_command
from src.client.telegram.handlers.errors import error_handler
from src.client.telegram.handlers.messages import handle_message
from src.config import Settings
from src.load.content_document import ContentDocument


@pytest.fixture
def mock_settings() -> Settings:
    settings = MagicMock(spec=Settings)
    settings.rate_limit_window_seconds = 10
    settings.telegram_bot_token = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    settings.openai_base_url = "https://api.openai.com/v1/"
    settings.openai_api_key = "test_key"
    settings.openai_model = "gpt-3.5-turbo"
    settings.valkey_url = None
    settings.cache_compression_method = "gzip"
    settings.yt_dlp_additional_options = ()
    settings.max_telegram_message_length = 4000
    return settings


@pytest.fixture
def mock_deps(mock_settings: Settings) -> Any:
    class Deps:
        loader = AsyncMock()
        summarizer = AsyncMock()
        rate_limiter = AsyncMock()
        settings = mock_settings

    return Deps()


@pytest.fixture
def mock_message() -> MagicMock:
    user = MagicMock(spec=User)
    user.id = 123
    user.username = "testuser"
    user.language_code = "en"
    user.is_bot = False

    message = AsyncMock(spec=Message)
    message.message_id = 1
    message.from_user = user
    message.text = "https://youtube.com/watch?v=123"
    message.reply = AsyncMock()
    return message


@pytest.mark.asyncio
async def test_bot_start(mock_message: MagicMock) -> None:
    # Need to mock translate since we aren't loading translations in unit tests by default
    with patch("src.client.telegram.handlers.commands.translate", return_value="Welcome"):
        await start_command(mock_message)
    mock_message.reply.assert_called_once_with("Welcome")


@pytest.mark.asyncio
async def test_bot_handle_message_no_text(mock_deps: MagicMock, mock_message: MagicMock) -> None:
    mock_message.text = None
    with (
        patch.object(mock_deps.rate_limiter, "is_limited", return_value=False),
        patch("src.client.telegram.handlers.messages.translate", return_value="No URL"),
    ):
        await handle_message(mock_message, mock_deps.loader, mock_deps.summarizer, mock_deps.rate_limiter, mock_deps.settings)
    assert mock_message.reply.call_count == 0


@pytest.mark.asyncio
async def test_bot_handle_message_rate_limited(mock_deps: MagicMock, mock_message: MagicMock) -> None:
    with (
        patch.object(mock_deps.rate_limiter, "is_limited", return_value=True),
        patch("src.client.telegram.handlers.messages.translate", return_value="Rate Limited"),
    ):
        await handle_message(mock_message, mock_deps.loader, mock_deps.summarizer, mock_deps.rate_limiter, mock_deps.settings)
    mock_message.reply.assert_called_once_with("Rate Limited")


@pytest.mark.asyncio
async def test_bot_handle_message_multiple_urls(mock_deps: MagicMock, mock_message: MagicMock) -> None:
    mock_message.text = "url1.com url2.com"
    with (
        patch.object(mock_deps.rate_limiter, "is_limited", return_value=False),
        patch("src.client.telegram.handlers.messages.extract_urls", return_value=["url1", "url2"]),
        patch("src.client.telegram.handlers.messages.translate", return_value="Error"),
    ):
        processing_msg_mock = AsyncMock()
        mock_message.reply.return_value = processing_msg_mock
        await handle_message(mock_message, mock_deps.loader, mock_deps.summarizer, mock_deps.rate_limiter, mock_deps.settings)
        processing_msg_mock.edit_text.assert_called_once_with("Error")


@pytest.mark.asyncio
async def test_bot_handle_message_success(mock_deps: MagicMock, mock_message: MagicMock) -> None:
    document = ContentDocument(
        id="123",
        source_type="video",
        url="https://youtube.com/watch?v=123",
        language="en",
        title="Test Video",
        thumbnail="",
        content="Test transcript",
        metadata={"uploader": "test"},
    )

    processing_msg_mock = AsyncMock()
    mock_message.reply.return_value = processing_msg_mock

    with (
        patch.object(mock_deps.rate_limiter, "is_limited", return_value=False),
        patch("src.client.telegram.handlers.messages.extract_urls", return_value=["https://youtube.com/watch?v=123"]),
        patch.object(mock_deps.loader, "load", return_value=document) as mock_load,
        patch.object(mock_deps.summarizer, "summarize", return_value="Test summary") as mock_summarize,
        patch("src.client.telegram.handlers.messages.translate", side_effect=lambda key, **kw: key),
    ):
        await handle_message(mock_message, mock_deps.loader, mock_deps.summarizer, mock_deps.rate_limiter, mock_deps.settings)

        mock_load.assert_called_once_with("https://youtube.com/watch?v=123")
        mock_summarize.assert_called_once_with(document, "en")

        # Original message reply for processing, and second reply for final result
        expected_calls = 2
        assert mock_message.reply.call_count == expected_calls
        processing_msg_mock.delete.assert_called_once()


@pytest.mark.asyncio
async def test_bot_handle_message_loader_fails(mock_deps: MagicMock, mock_message: MagicMock) -> None:
    processing_msg_mock = AsyncMock()
    mock_message.reply.return_value = processing_msg_mock

    with (
        patch.object(mock_deps.rate_limiter, "is_limited", return_value=False),
        patch("src.client.telegram.handlers.messages.extract_urls", return_value=["https://youtube.com/watch?v=123"]),
        patch.object(mock_deps.loader, "load", side_effect=Exception("Load error")),
        patch("src.client.telegram.handlers.messages.translate", return_value="Fail"),
    ):
        await handle_message(mock_message, mock_deps.loader, mock_deps.summarizer, mock_deps.rate_limiter, mock_deps.settings)
        processing_msg_mock.edit_text.assert_called_with("Fail")


@pytest.mark.asyncio
async def test_bot_handle_message_summarizer_fails(mock_deps: MagicMock, mock_message: MagicMock) -> None:
    document = ContentDocument(
        id="123",
        source_type="video",
        url="https://youtube.com/watch?v=123",
        language="en",
        title="Test Video",
        thumbnail="",
        content="Test transcript",
        metadata={"uploader": "test"},
    )
    processing_msg_mock = AsyncMock()
    mock_message.reply.return_value = processing_msg_mock

    with (
        patch.object(mock_deps.rate_limiter, "is_limited", return_value=False),
        patch("src.client.telegram.handlers.messages.extract_urls", return_value=["https://youtube.com/watch?v=123"]),
        patch.object(mock_deps.loader, "load", return_value=document),
        patch.object(mock_deps.summarizer, "summarize", side_effect=Exception("Summarize error")),
        patch("src.client.telegram.handlers.messages.translate", return_value="Fail"),
    ):
        await handle_message(mock_message, mock_deps.loader, mock_deps.summarizer, mock_deps.rate_limiter, mock_deps.settings)
        processing_msg_mock.edit_text.assert_called_with("Fail")


@pytest.mark.asyncio
async def test_bot_on_error(mock_message: MagicMock) -> None:
    event = MagicMock(spec=ErrorEvent)
    event.exception = Exception("General error")
    update = MagicMock()
    update.message = mock_message
    event.update = update

    with patch("src.client.telegram.handlers.errors.translate", return_value="Error handled"):
        await error_handler(event)
    mock_message.reply.assert_called_once_with("Error handled")
