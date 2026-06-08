"""
Text summarization module using OpenAI-compatible APIs.

Provides LLM-based text summarization with retry logic,
timeout handling, and localization support.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import time

from openai import APIStatusError, AsyncOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionMessageParam

from ..cache import CacheProvider, get_cache_provider
from ..config import Settings
from ..load.content_document import ContentDocument
from ..localization import translate

logger = logging.getLogger(__name__)
cache_prefix = "summary:"


class OpenAISummarizer:
    """
    Summarizes text using OpenAI-compatible API.

    Features:
    - Configurable base URL for custom LLM endpoints
    - Automatic retries with exponential backoff
    - Timeout handling
    - Locale-aware system prompts

    Attributes:
        settings: Application configuration.
        client: OpenAI API client instance.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the summarizer with API client.

        Args:
            settings: Application settings with API credentials.
        """
        self.settings = settings
        self.cache_provider: CacheProvider = get_cache_provider(settings)
        self.client = AsyncOpenAI(
            base_url=settings.openai_base_url,
            api_key=settings.openai_api_key,
            max_retries=settings.openai_max_retries,
        )

    async def summarize(self, document: ContentDocument, locale: str) -> str:
        """
        Summarize a content document.

        Args:
            document: Source-neutral document to summarize.
            locale: Target locale for system prompt localization.

        Returns:
            Generated summary text.
        """
        if not locale:
            raise ValueError("locale must be a non-empty string")
        if not document.content:
            raise ValueError("document content must be a non-empty string")

        content_hash = self._text_hash(document.content)
        cache_key = f"{cache_prefix}:{content_hash}:{locale}"
        cached_summary = await self.cache_provider.get(cache_key)
        if cached_summary:
            logger.debug("Summary loaded from cache", extra={"locale": locale})
            return cached_summary

        summary = await self._summarize(document, locale)
        await self.cache_provider.put(
            cache_key,
            summary,
            self.settings.cache_summary_ttl_seconds,
        )
        return summary

    async def _summarize(self, document: ContentDocument, locale: str) -> str:
        """
        Summarize a document using the configured LLM model.

        Args:
            document: Source-neutral document to summarize.
            locale: Target locale for system prompt localization.

        Returns:
            Generated summary text.

        Raises:
            RuntimeError: If summarization fails after all retries.
        """
        if not locale:
            raise ValueError("locale must be a non-empty string")

        logger.info(
            "Summarizing content",
            extra={
                "locale": locale,
                "content_length": len(document.content),
                "source_type": document.source_type,
                "model": self.settings.openai_model,
            },
        )
        system_prompt = translate("openai.system_prompt", locale=locale)
        user_prompt = translate("openai.user_prompt", locale=locale)

        if self.settings.openai_max_retries <= 0:
            raise ValueError("openai_max_retries must be greater than 0")

        try:
            start_time = time.monotonic()
            try:
                response = await self._create_completion(
                    self._file_messages(system_prompt, user_prompt, document.content),
                )
                request_mode = "file"
            except APIStatusError as exc:
                if not self._is_unsupported_file_error(exc):
                    raise
                logger.info(
                    "Provider does not support file content; retrying inline",
                    extra={"model": self.settings.openai_model},
                )
                response = await self._create_completion(
                    self._inline_messages(system_prompt, user_prompt, document.content),
                )
                request_mode = "inline"
            elapsed = time.monotonic() - start_time

            if not response or not response.choices:
                logger.warning(
                    "OpenAI returned no response",
                    extra={"response_id": getattr(response, "id", None), "model": getattr(response, "model", None)},
                )
                raise RuntimeError("no OpenAI response")

            content = response.choices[0].message.content
            if not content:
                logger.warning(
                    "OpenAI returned empty response",
                    extra={
                        "response_id": getattr(response, "id", None),
                        "model": getattr(response, "model", None),
                        "choices": getattr(response, "choices", None),
                    },
                )
                raise RuntimeError("empty OpenAI response")

            logger.info(
                "Summary received",
                extra={
                    "locale": locale,
                    "model": self.settings.openai_model,
                    "request_mode": request_mode,
                    "elapsed_ms": int(elapsed * 1000),
                    "content_length": len(content),
                },
            )
            return content
        except Exception as exc:
            logger.warning(
                "OpenAI summarization attempt failed",
                extra={"error": str(exc)},
            )
            raise RuntimeError(f"failed to summarize content: {exc}") from exc

    async def _create_completion(self, messages: list[ChatCompletionMessageParam]) -> ChatCompletion:
        """Create a chat completion using the configured model and timeout."""
        return await self.client.chat.completions.create(
            model=self.settings.openai_model,
            messages=messages,
            timeout=self.settings.openai_timeout_seconds,
        )

    @staticmethod
    def _file_messages(system_prompt: str, user_prompt: str, content: str) -> list[ChatCompletionMessageParam]:
        """Build messages with the source represented as a Markdown file."""
        encoded_content = base64.b64encode(content.encode("utf-8")).decode("ascii")
        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {
                        "type": "file",
                        "file": {
                            "filename": "source.md",
                            "file_data": encoded_content,
                        },
                    },
                ],
            },
        ]

    @staticmethod
    def _inline_messages(system_prompt: str, user_prompt: str, content: str) -> list[ChatCompletionMessageParam]:
        """Build compatible messages with the source Markdown inline."""
        return [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f'{user_prompt}\n\n<document filename="source.md">\n{content}\n</document>',
            },
        ]

    @staticmethod
    def _is_unsupported_file_error(exc: APIStatusError) -> bool:
        """Return whether a provider rejected the file content-part format."""
        if exc.status_code not in {400, 422}:
            return False

        details = " ".join(
            value
            for value in (
                exc.message,
                exc.code,
                exc.param,
                exc.type,
                OpenAISummarizer._error_body_text(exc.body),
            )
            if value
        ).lower()
        file_terms = ("file", "content part", "content_part", "content type", "input type")
        unsupported_terms = ("unsupported", "not supported", "unknown content part", "unknown content type")
        return any(term in details for term in file_terms) and any(term in details for term in unsupported_terms)

    @staticmethod
    def _error_body_text(body: object | None) -> str:
        """Extract scalar error details from a provider response body."""
        if isinstance(body, dict):
            return " ".join(OpenAISummarizer._error_body_text(value) for value in body.values())
        if isinstance(body, list):
            return " ".join(OpenAISummarizer._error_body_text(value) for value in body)
        return str(body) if isinstance(body, (str, int, float)) else ""

    @staticmethod
    def _text_hash(text: str) -> str:
        """Return a deterministic cache key for source content."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
