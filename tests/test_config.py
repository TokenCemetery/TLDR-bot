import dataclasses
import os
from unittest.mock import MagicMock, patch

import pytest
from src.config import (
    DEFAULT_CACHE_COMPRESSION_METHOD,
    DEFAULT_CACHE_TTL_NO_VALKEY,
    DEFAULT_CACHE_TTL_WITH_VALKEY,
    DEFAULT_MAX_TELEGRAM_MESSAGE_LENGTH,
    DEFAULT_OPENAI_BASE_URL,
    DEFAULT_OPENAI_MAX_RETRIES,
    DEFAULT_OPENAI_TIMEOUT_SECONDS,
    DEFAULT_RATE_LIMIT_WINDOW_SECONDS,
    Settings,
)


def test_settings_from_env_success() -> None:
    with patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_MODEL": "gpt-3.5-turbo",
            "OPENAI_BASE_URL": "https://api.openai.com/v1/",
            "YT_DLP_ADDITIONAL_OPTIONS": "--format mp4 --proxy http://proxy.example.com",
            "MAX_TELEGRAM_MESSAGE_LENGTH": "4000",
        },
    ):
        settings = Settings.from_env()

        expected_msg_len = 4000
        assert settings.telegram_bot_token == "test_token"
        assert settings.openai_api_key == "test_api_key"
        assert settings.openai_model == "gpt-3.5-turbo"
        assert settings.openai_base_url == "https://api.openai.com/v1/"
        assert settings.max_telegram_message_length == expected_msg_len
        assert settings.yt_dlp_additional_options == (
            "--format",
            "mp4",
            "--proxy",
            "http://proxy.example.com",
        )


@patch("src.config.load_dotenv")
def test_settings_from_env_missing_required_variables(mock_load_dotenv: MagicMock) -> None:
    with patch.dict(
        os.environ,
        {"OPENAI_API_KEY": "test_api_key", "OPENAI_MODEL": "gpt-3.5-turbo"},
        clear=True,
    ):
        with pytest.raises(RuntimeError, match="TELEGRAM_BOT_TOKEN"):
            Settings.from_env()

    with patch.dict(
        os.environ,
        {"TELEGRAM_BOT_TOKEN": "test_token", "OPENAI_MODEL": "gpt-3.5-turbo"},
        clear=True,
    ):
        with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
            Settings.from_env()

    with patch.dict(
        os.environ,
        {"TELEGRAM_BOT_TOKEN": "test_token", "OPENAI_API_KEY": "test_api_key"},
        clear=True,
    ):
        with pytest.raises(RuntimeError, match="OPENAI_MODEL"):
            Settings.from_env()


@patch("src.config.load_dotenv")
def test_settings_from_env_default_values(mock_load_dotenv: MagicMock) -> None:
    with patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_MODEL": "gpt-3.5-turbo",
        },
        clear=True,
    ):
        settings = Settings.from_env()

        expected_rate_limit = DEFAULT_RATE_LIMIT_WINDOW_SECONDS
        expected_msg_len = DEFAULT_MAX_TELEGRAM_MESSAGE_LENGTH
        expected_timeout = DEFAULT_OPENAI_TIMEOUT_SECONDS
        expected_retries = DEFAULT_OPENAI_MAX_RETRIES
        assert settings.openai_base_url == DEFAULT_OPENAI_BASE_URL
        assert settings.rate_limit_window_seconds == expected_rate_limit
        assert settings.max_telegram_message_length == expected_msg_len
        assert settings.openai_timeout_seconds == expected_timeout
        assert settings.openai_max_retries == expected_retries
        assert settings.yt_dlp_additional_options == ()


def test_settings_from_env_custom_values() -> None:
    with patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "custom_token",
            "OPENAI_BASE_URL": "https://custom.openai.api/v1/",
            "OPENAI_API_KEY": "custom_api_key",
            "OPENAI_MODEL": "gpt-4",
            "YT_DLP_ADDITIONAL_OPTIONS": "--format best --extract-audio",
            "RATE_LIMIT_WINDOW_SECONDS": "30",
            "MAX_TELEGRAM_MESSAGE_LENGTH": "2000",
        },
    ):
        settings = Settings.from_env()

        expected_rate_limit = 30
        expected_msg_len = 2000
        assert settings.telegram_bot_token == "custom_token"
        assert settings.openai_base_url == "https://custom.openai.api/v1/"
        assert settings.openai_api_key == "custom_api_key"
        assert settings.openai_model == "gpt-4"
        assert settings.rate_limit_window_seconds == expected_rate_limit
        assert settings.max_telegram_message_length == expected_msg_len
        assert settings.yt_dlp_additional_options == (
            "--format",
            "best",
            "--extract-audio",
        )


def test_settings_immutability() -> None:
    with patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_MODEL": "gpt-3.5-turbo",
        },
    ):
        settings = Settings.from_env()

        with pytest.raises(dataclasses.FrozenInstanceError):
            settings.telegram_bot_token = "new_token"  # type: ignore[misc]


@patch("src.config.load_dotenv")
def test_settings_from_env_invalid_proxy_url(mock_load_dotenv: MagicMock) -> None:
    with patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_MODEL": "gpt-3.5-turbo",
            "TELEGRAM_PROXY_URL": "http://localhost",
        },
        clear=True,
    ):
        with pytest.raises(RuntimeError, match="Invalid TELEGRAM_PROXY_URL format"):
            Settings.from_env()


@patch("src.config.load_dotenv")
def test_settings_from_env_valid_proxy_url(mock_load_dotenv: MagicMock) -> None:
    with patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_MODEL": "gpt-3.5-turbo",
            "TELEGRAM_PROXY_URL": "socks5://proxy.example.com:1080",
        },
        clear=True,
    ):
        settings = Settings.from_env()

        assert settings.telegram_proxy_url == "socks5://proxy.example.com:1080"


@patch("src.config.load_dotenv")
def test_settings_from_env_valid_proxy_url_with_auth(mock_load_dotenv: MagicMock) -> None:
    with patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_MODEL": "gpt-3.5-turbo",
            "TELEGRAM_PROXY_URL": "socks5://user:pass@proxy.example.com:1080",
        },
        clear=True,
    ):
        settings = Settings.from_env()

        assert settings.telegram_proxy_url == "socks5://user:pass@proxy.example.com:1080"


@patch("src.config.load_dotenv")
def test_settings_from_env_unsupported_proxy_protocol(mock_load_dotenv: MagicMock) -> None:
    with patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_MODEL": "gpt-3.5-turbo",
            "TELEGRAM_PROXY_URL": "ftp://user:pass@proxy.example.com:1080",
        },
        clear=True,
    ):
        with pytest.raises(RuntimeError, match="Unsupported proxy protocol"):
            Settings.from_env()


@patch("src.config.load_dotenv")
def test_settings_from_env_compression_method_fallback(mock_load_dotenv: MagicMock) -> None:
    with patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_MODEL": "gpt-3.5-turbo",
            "CACHE_COMPRESSION_METHOD": "invalid",
        },
        clear=True,
    ):
        settings = Settings.from_env()

        assert settings.cache_compression_method == DEFAULT_CACHE_COMPRESSION_METHOD


@patch("src.config.load_dotenv")
def test_settings_from_env_compression_method_normalized(mock_load_dotenv: MagicMock) -> None:
    with patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_MODEL": "gpt-3.5-turbo",
            "CACHE_COMPRESSION_METHOD": "LZMA",
        },
        clear=True,
    ):
        settings = Settings.from_env()

        assert settings.cache_compression_method == "lzma"


@patch("src.config.load_dotenv")
def test_settings_from_env_invalid_ints_fall_back(mock_load_dotenv: MagicMock) -> None:
    with patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_MODEL": "gpt-3.5-turbo",
            "OPENAI_TIMEOUT_SECONDS": "not-a-number",
            "MAX_TELEGRAM_MESSAGE_LENGTH": "nope",
        },
        clear=True,
    ):
        settings = Settings.from_env()

        assert settings.openai_timeout_seconds == DEFAULT_OPENAI_TIMEOUT_SECONDS
        assert settings.max_telegram_message_length == DEFAULT_MAX_TELEGRAM_MESSAGE_LENGTH


@patch("src.config.load_dotenv")
def test_settings_from_env_cache_ttl_defaults_depend_on_valkey(mock_load_dotenv: MagicMock) -> None:
    with patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_MODEL": "gpt-3.5-turbo",
        },
        clear=True,
    ):
        settings = Settings.from_env()

        assert settings.cache_summary_ttl_seconds == DEFAULT_CACHE_TTL_NO_VALKEY
        assert settings.cache_transcript_ttl_seconds == DEFAULT_CACHE_TTL_NO_VALKEY

    with patch.dict(
        os.environ,
        {
            "TELEGRAM_BOT_TOKEN": "test_token",
            "OPENAI_API_KEY": "test_api_key",
            "OPENAI_MODEL": "gpt-3.5-turbo",
            "VALKEY_URL": "redis://localhost:6379/0",
        },
        clear=True,
    ):
        settings = Settings.from_env()

        assert settings.cache_summary_ttl_seconds == DEFAULT_CACHE_TTL_WITH_VALKEY
        assert settings.cache_transcript_ttl_seconds == DEFAULT_CACHE_TTL_WITH_VALKEY
