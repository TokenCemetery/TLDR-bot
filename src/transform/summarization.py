"""
Text summarization module using OpenAI-compatible APIs.

Provides LLM-based text summarization with retry logic,
timeout handling, and localization support.
"""

from __future__ import annotations

import hashlib
import logging
import time

from openai import AsyncOpenAI

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
            response = await self.client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": user_prompt},
                            {"type": "text", "text": document.content},
                        ],
                    },
                ],
                timeout=self.settings.openai_timeout_seconds,
            )
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

    @staticmethod
    def _text_hash(text: str) -> str:
        """Return a deterministic cache key for source content."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()
