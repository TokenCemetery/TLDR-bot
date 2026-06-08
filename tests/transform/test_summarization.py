import base64
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from openai import APIStatusError, BadRequestError, UnprocessableEntityError
from src.config import Settings
from src.load.content_document import ContentDocument
from src.transform.summarization import OpenAISummarizer

HTTP_UNPROCESSABLE_ENTITY = 422


def build_settings(**overrides: object) -> Settings:
    settings = MagicMock(spec=Settings)
    settings.openai_base_url = "https://api.openai.com/v1/"
    settings.openai_api_key = "test-key"
    settings.openai_model = "gpt-3.5-turbo"
    settings.openai_timeout_seconds = 300
    settings.openai_max_retries = 3
    settings.cache_summary_ttl_seconds = 3600
    settings.valkey_url = None
    settings.cache_compression_method = "gzip"
    for key, value in overrides.items():
        setattr(settings, key, value)
    return settings


def build_document(content: str = "Input text to summarize") -> ContentDocument:
    return ContentDocument(
        id="test",
        source_type="video",
        url="https://example.com/video",
        title="Test video",
        language="en",
        content=content,
    )


def build_status_error(
    message: str,
    *,
    status_code: int = 400,
    body: object | None = None,
) -> APIStatusError:
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    response = httpx.Response(status_code, request=request)
    if status_code == HTTP_UNPROCESSABLE_ENTITY:
        return UnprocessableEntityError(message, response=response, body=body)
    return BadRequestError(message, response=response, body=body)


@pytest.mark.asyncio
async def test_openai_summarizer_initialization() -> None:
    mock_settings = build_settings()

    with patch("src.transform.summarization.AsyncOpenAI") as mock_openai_class:
        mock_client_instance = MagicMock()
        mock_openai_class.return_value = mock_client_instance

        summarizer = OpenAISummarizer(mock_settings)

        # Verify the client was initialized with correct settings
        mock_openai_class.assert_called_once_with(
            base_url="https://api.openai.com/v1/",
            api_key="test-key",
            max_retries=3,
        )
        assert summarizer.settings == mock_settings


@pytest.mark.asyncio
async def test_summarizer_summarize_text_success() -> None:
    mock_settings = build_settings()

    with patch("src.transform.summarization.AsyncOpenAI") as mock_openai_class:
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()

        mock_choice.message.content = "This is the summary"
        mock_response.choices = [mock_choice]
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_response)

        mock_openai_class.return_value = mock_client_instance

        with patch("src.transform.summarization.translate") as mock_translate:
            mock_translate.side_effect = ["System style", "Summarize the document"]

            summarizer = OpenAISummarizer(mock_settings)
            result = await summarizer._summarize(build_document(), "en")

            mock_client_instance.chat.completions.create.assert_called_once_with(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "System style"},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Summarize the document"},
                            {
                                "type": "file",
                                "file": {
                                    "filename": "source.md",
                                    "file_data": base64.b64encode(b"Input text to summarize").decode("ascii"),
                                },
                            },
                        ],
                    },
                ],
                timeout=300,
            )
            assert mock_translate.call_args_list[0].args == ("openai.system_prompt",)
            assert mock_translate.call_args_list[1].args == ("openai.user_prompt",)
            assert result == "This is the summary"


@pytest.mark.asyncio
async def test_summarizer_summarize_text_empty_response() -> None:
    mock_settings = build_settings()

    with patch("src.transform.summarization.AsyncOpenAI") as mock_openai_class:
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()

        mock_message.content = None  # Empty response
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        # Set response attributes to avoid dynamic mock creation during logging
        mock_response.id = "test_response_id"
        mock_response.model = "gpt-3.5-turbo"
        mock_response.message = None  # Explicitly set to None to avoid mock creation
        mock_client_instance.chat.completions.create = AsyncMock(return_value=mock_response)

        mock_openai_class.return_value = mock_client_instance

        with patch("src.transform.summarization.translate") as mock_translate:
            mock_translate.side_effect = ["System style", "Summarize the document"]

            summarizer = OpenAISummarizer(mock_settings)

            with pytest.raises(RuntimeError, match="empty OpenAI response"):
                await summarizer._summarize(build_document(), "en")


@pytest.mark.asyncio
async def test_summarizer_summarize_text_with_retry_failure() -> None:
    mock_settings = build_settings(openai_max_retries=2)

    with patch("src.transform.summarization.AsyncOpenAI") as mock_openai_class:
        mock_client_instance = MagicMock()

        mock_client_instance.chat.completions.create = AsyncMock(
            side_effect=Exception("Network error"),
        )

        mock_openai_class.return_value = mock_client_instance

        with patch("src.transform.summarization.translate") as mock_translate:
            mock_translate.side_effect = ["System style", "Summarize the document"]

            summarizer = OpenAISummarizer(mock_settings)

            with pytest.raises(RuntimeError, match="failed to summarize content:"):
                await summarizer._summarize(build_document(), "en")

            expected_calls = 1
            assert mock_client_instance.chat.completions.create.call_count == expected_calls


@pytest.mark.asyncio
async def test_summarizer_falls_back_to_inline_content() -> None:
    mock_settings = build_settings()

    with patch("src.transform.summarization.AsyncOpenAI") as mock_openai_class:
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Fallback summary"
        mock_response.choices = [mock_choice]
        mock_client_instance.chat.completions.create = AsyncMock(
            side_effect=[
                build_status_error(
                    "Request rejected",
                    body={
                        "code": "unsupported_content_type",
                        "param": "messages.1.content.1.file",
                    },
                ),
                mock_response,
            ]
        )
        mock_openai_class.return_value = mock_client_instance

        with patch("src.transform.summarization.translate", side_effect=["System style", "Summarize the document"]):
            summarizer = OpenAISummarizer(mock_settings)
            result = await summarizer._summarize(build_document("# Source"), "en")

    assert result == "Fallback summary"
    expected_calls = 2
    assert mock_client_instance.chat.completions.create.call_count == expected_calls
    fallback_messages = mock_client_instance.chat.completions.create.call_args_list[1].kwargs["messages"]
    assert fallback_messages == [
        {"role": "system", "content": "System style"},
        {
            "role": "user",
            "content": 'Summarize the document\n\n<document filename="source.md">\n# Source\n</document>',
        },
    ]


@pytest.mark.asyncio
async def test_summarizer_falls_back_for_422_unsupported_file_content() -> None:
    mock_settings = build_settings()

    with patch("src.transform.summarization.AsyncOpenAI") as mock_openai_class:
        mock_client_instance = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Fallback summary"
        mock_response.choices = [mock_choice]
        mock_client_instance.chat.completions.create = AsyncMock(
            side_effect=[
                build_status_error(
                    "Request validation failed",
                    status_code=HTTP_UNPROCESSABLE_ENTITY,
                    body={
                        "error": {
                            "message": "Unknown content part type: file",
                            "param": "messages.1.content.1",
                        }
                    },
                ),
                mock_response,
            ]
        )
        mock_openai_class.return_value = mock_client_instance

        with patch("src.transform.summarization.translate", side_effect=["System style", "Summarize source.md"]):
            summarizer = OpenAISummarizer(mock_settings)
            result = await summarizer._summarize(build_document("# Source"), "en")

    assert result == "Fallback summary"
    expected_calls = 2
    assert mock_client_instance.chat.completions.create.call_count == expected_calls


@pytest.mark.asyncio
async def test_summarizer_does_not_fallback_for_unrelated_bad_request() -> None:
    mock_settings = build_settings()

    with patch("src.transform.summarization.AsyncOpenAI") as mock_openai_class:
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = AsyncMock(
            side_effect=build_status_error("Invalid model"),
        )
        mock_openai_class.return_value = mock_client_instance

        with patch("src.transform.summarization.translate", side_effect=["System style", "Summarize the document"]):
            summarizer = OpenAISummarizer(mock_settings)
            with pytest.raises(RuntimeError, match="Invalid model"):
                await summarizer._summarize(build_document(), "en")

    assert mock_client_instance.chat.completions.create.call_count == 1


@pytest.mark.asyncio
async def test_summarizer_does_not_fallback_for_invalid_file() -> None:
    mock_settings = build_settings()

    with patch("src.transform.summarization.AsyncOpenAI") as mock_openai_class:
        mock_client_instance = MagicMock()
        mock_client_instance.chat.completions.create = AsyncMock(
            side_effect=build_status_error(
                "Invalid file data",
                body={
                    "code": "invalid_value",
                    "param": "messages.1.content.1.file.file_data",
                },
            ),
        )
        mock_openai_class.return_value = mock_client_instance

        with patch("src.transform.summarization.translate", side_effect=["System style", "Summarize source.md"]):
            summarizer = OpenAISummarizer(mock_settings)
            with pytest.raises(RuntimeError, match="Invalid file data"):
                await summarizer._summarize(build_document(), "en")

    assert mock_client_instance.chat.completions.create.call_count == 1


@pytest.mark.asyncio
async def test_summarizer_invalid_args() -> None:
    mock_settings = build_settings()
    summarizer = OpenAISummarizer(mock_settings)

    with pytest.raises(ValueError, match="locale must be a non-empty string"):
        await summarizer.summarize(build_document(), "")

    with pytest.raises(ValueError, match="document content must be a non-empty string"):
        await summarizer.summarize(build_document(""), "en")


@pytest.mark.asyncio
async def test_summarize_cached() -> None:
    mock_settings = build_settings()
    summarizer = OpenAISummarizer(mock_settings)

    mock_provider = AsyncMock()
    mock_provider.get.return_value = "Cached summary"
    summarizer.cache_provider = mock_provider

    result = await summarizer.summarize(build_document("Input text"), "en")

    assert result == "Cached summary"
    mock_provider.get.assert_called_once()
    mock_provider.put.assert_not_called()


@pytest.mark.asyncio
async def test_summarize_uncached() -> None:
    mock_settings = build_settings()
    summarizer = OpenAISummarizer(mock_settings)

    mock_provider = AsyncMock()
    mock_provider.get.return_value = None
    summarizer.cache_provider = mock_provider

    with patch.object(summarizer, "_summarize", return_value="New summary"):
        result = await summarizer.summarize(build_document("Input text"), "en")

        assert result == "New summary"
        mock_provider.get.assert_called_once()
        mock_provider.put.assert_called_once_with(
            "summary::75b697462588792e2fc85fa00b5dc51992b25be2d780349f0827fea9311aea8b:en",
            "New summary",
            mock_settings.cache_summary_ttl_seconds,
        )
