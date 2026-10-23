"""
Video URL provider module.

Extracts and validates video URLs from supported platforms:
- YouTube (standard and Shorts)
- VK Video

Provides URL canonicalization and video ID extraction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RegexProvider:
    """
    URL pattern matcher and canonicalizer for video platforms.

    Attributes:
        pattern: Compiled regex pattern for URL matching.
        canonical_url: URL template for canonical form (with %s for video ID).
    """

    pattern: re.Pattern[str]
    canonical_url: str

    def is_valid_url(self, text: str) -> bool:
        """
        Check if text contains a valid URL for this provider.

        Args:
            text: Text to search for URLs.

        Returns:
            True if a valid URL is found, False otherwise.
        """
        return bool(self.pattern.search(text))

    def get_id(self, text: str) -> str:
        """
        Extract video ID from URL.

        Args:
            text: Text containing the URL.

        Returns:
            Video ID (e.g., 'dQw4w9WgXcQ').

        Raises:
            ValueError: If no valid URL is found.
        """
        match = self.pattern.search(text)
        if not match:
            raise ValueError("no valid URL found")
        return match.group(1)

    def extract_urls(self, text: str) -> list[str]:
        """
        Extract all matching URLs from text.

        Args:
            text: Text to search for URLs.

        Returns:
            List of matched URLs.
        """
        return [match.group(0) for match in self.pattern.finditer(text)]

    def canonicalize(self, text: str) -> tuple[str, str]:
        """
        Convert URL to canonical form and extract video ID.

        Args:
            text: Text containing the URL.

        Returns:
            Tuple of (canonical URL, video ID).
        """
        video_id = self.get_id(text)
        return self.canonical_url % video_id, video_id


# YouTube standard video URL pattern (youtube.com/watch?v=ID or youtu.be/ID)
YOUTUBE = RegexProvider(
    pattern=re.compile(r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?.*?v=|youtu\.be/)([a-zA-Z0-9_-]{11})"),
    canonical_url="https://www.youtube.com/watch?v=%s",
)

YOUTUBE_SHORT = RegexProvider(
    pattern=re.compile(r"(?:https?://)?(?:www\.)?youtube\.com/shorts/([A-Za-z0-9_-]{11})"),
    canonical_url="https://www.youtube.com/shorts/%s",
)

VKVIDEO = RegexProvider(
    pattern=re.compile(r"(?:https?://)?(?:www\.)?vkvideo\.ru/(video-\d+_\d+)"),
    canonical_url="https://vkvideo.ru/%s",
)

PROVIDERS: tuple[RegexProvider, ...] = (YOUTUBE, YOUTUBE_SHORT, VKVIDEO)


def extract_urls(text: str) -> list[str]:
    """
    Extract video URLs from text using all supported providers.

    Returns URLs from the first matching provider (priority order:
    YouTube standard, YouTube Shorts, VK Video).

    Args:
        text: Text to search for video URLs.

    Returns:
        List of extracted URLs (empty if none found).
    """
    for provider in PROVIDERS:
        if provider.is_valid_url(text):
            return provider.extract_urls(text)
    return []


def build_video_source(url: str) -> tuple[str, str]:
    """
    Validate URL and return canonical form with video ID.

    Args:
        url: Video URL to validate and canonicalize.

    Returns:
        Tuple of (canonical URL, video ID).

    Raises:
        ValueError: If URL doesn't match any supported provider.
    """
    for provider in PROVIDERS:
        if provider.is_valid_url(url):
            return provider.canonicalize(url)
    raise ValueError(f"no valid URL found: {url}")
