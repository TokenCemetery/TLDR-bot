"""
Video loader module for downloading and extracting video transcripts.

This module provides functionality to:
- Extract video information from URLs (YouTube, VK Video)
- Download subtitles/transcripts using yt-dlp
- Clean and process SRT subtitle format
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yt_dlp

from ..cache import CacheProvider, get_cache_provider
from ..config import Settings
from .content_document import ContentDocument
from .transcripts import clean_srt
from .video_provider import build_video_source
from .yt_dlp_logger import YtDlpCaptureLogger

logger = logging.getLogger(__name__)
max_attempts = 3
cache_prefix = "transcript:"


def _is_safe_option_value(value: str) -> bool:
    """
    Check if an option value is safe (no shell injection or path traversal).

    Args:
        value: The option value to validate.

    Returns:
        True if safe, False otherwise.
    """
    # Block path traversal
    if ".." in value or value.startswith("/"):
        return False
    # Block shell metacharacters
    if any(char in value for char in (";", "|", "&", "$", "`", "(", ")", "<", ">", "\\", "\n", "\r")):
        return False
    return True


@dataclass(frozen=True)
class VideoInfo:
    """
    Video metadata extracted from the source.

    Attributes:
        id: Unique video identifier.
        language: Detected language code.
        uploader: Channel/user who uploaded the video.
        title: Video title.
        thumbnail: URL to video thumbnail.
        subtitles: Dictionary of available subtitle tracks.
    """

    id: str
    language: str
    uploader: str
    title: str
    thumbnail: str
    subtitles: dict[str, list[dict[str, str]]]


class VideoDataLoader:
    """
    Loads video information and transcripts from supported platforms.

    Supports YouTube and VK Video platforms. Handles retries,
    temporary file management, and subtitle cleaning.
    """

    def __init__(self, settings: Settings) -> None:
        """
        Initialize the video loader.

        Args:
            settings: Application settings with cache and yt-dlp configuration.
        """
        self.settings = settings
        self.cache_provider: CacheProvider = get_cache_provider(settings)
        self.yt_dlp_additional_options = settings.yt_dlp_additional_options

    async def load(self, url: str) -> ContentDocument:
        """
        Load transcript.

        Args:
            url: Video URL to process.

        Returns:
            ContentDocument containing the video transcript and metadata.

        Throws:
            - `RuntimeError` - video info/subtitles failed
            - `FileNotFoundError` - no subtitles
            - `ValueError` - URL is not valid
            - `OSError` - failed to clean up temporary files
        """
        url, video_id = build_video_source(url)
        cache_key = f"{cache_prefix}:{self._get_video_hash(url)}"
        cached_transcript = await self.cache_provider.get_dict(cache_key)
        if cached_transcript:
            if "content" in cached_transcript:
                transcript = ContentDocument(**cached_transcript)
            else:
                transcript = ContentDocument(
                    id=str(cached_transcript.get("id", video_id)),
                    source_type="video",
                    url=url,
                    title=str(cached_transcript.get("title", "")),
                    language=str(cached_transcript.get("language", "")),
                    content=str(cached_transcript.get("transcript", "")),
                    thumbnail=str(cached_transcript.get("thumbnail", "")),
                    metadata={"uploader": str(cached_transcript.get("uploader", ""))},
                )
            logger.debug("Transcript loaded from cache", extra={"url": url})
            return transcript

        transcript = await asyncio.to_thread(self._load, url, video_id)

        await self.cache_provider.put_dict(
            cache_key,
            asdict(transcript),
            self.settings.cache_transcript_ttl_seconds,
        )

        return transcript

    def _load(self, url: str, video_id: str) -> ContentDocument:
        """
        Load video info and download transcript.

        Performs the following steps:
        1. Extract video metadata with retries
        2. Detect subtitle language
        3. Download subtitles with retries
        4. Clean and process SRT content
        5. Cleanup temporary files

        Raises:
            RuntimeError: If video info or subtitles cannot be loaded after retries.
            FileNotFoundError: If no subtitles are available.
        """
        logger.info(
            "Loading video info",
            extra={
                "url": url,
                "video_id": video_id,
            },
        )

        # Extract video info with retries
        last_error: Exception | None = None
        for attempt in range(max_attempts):
            try:
                ydl_opts = self._build_ydl_opts(
                    {
                        "dumpjson": True,
                    }
                )
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    raw_info = ydl.extract_info(url, download=False)
                    info = VideoInfo(
                        id=str(raw_info.get("id", "")),
                        language=str(raw_info.get("language", "") or ""),
                        uploader=str(raw_info.get("uploader", "") or ""),
                        title=str(raw_info.get("title", "") or ""),
                        thumbnail=str(raw_info.get("thumbnail", "") or ""),
                        subtitles=dict(raw_info.get("subtitles", {}) or {}),
                    )
                break
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Failed to load video info",
                    extra={"attempt": attempt + 1, "url": url, "error": str(exc)},
                )
        else:
            raise RuntimeError(f"Failed to load video info after {max_attempts} attempts: {last_error}")

        language = self._detect_language(info)
        logger.debug("Detected transcript language", extra={"url": url, "language": language})

        # Download subtitles with retries
        ydl_logger = YtDlpCaptureLogger()
        for attempt in range(max_attempts):
            try:
                ydl_logger.messages.clear()
                ydl_opts = self._build_ydl_opts(
                    {
                        "no_progress": True,
                        "skip_download": True,
                        "writesubtitles": True,
                        "writeautomaticsub": True,
                        "subtitleslangs": [language, f"{language}_auto", "-live_chat"],
                        "subtitlesformat": "srt/vtt/best",
                        "outtmpl": self._get_subtitle_template_path(video_id),
                        "logger": ydl_logger,
                        "quiet": False,
                        "no_warnings": False,
                    }
                )
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.extract_info(url, download=True)
                break
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Failed to download subtitles",
                    extra={
                        "attempt": attempt + 1,
                        "url": url,
                        "error": str(exc),
                        "yt_dlp_output": "\n".join(ydl_logger.messages),
                    },
                )
        else:
            raise RuntimeError(f"Failed to download subtitles after {max_attempts} attempts: {last_error}")

        subtitle_file = self._find_subtitle_file(video_id, language)
        if subtitle_file is None:
            logger.warning(
                "No subtitles found",
                extra={
                    "url": url,
                    "language": language,
                    "yt_dlp_output": "\n".join(ydl_logger.messages),
                },
            )
            raise FileNotFoundError("no subtitles found")

        raw_transcript = subtitle_file.read_text(encoding="utf-8", errors="ignore")
        transcript_text = clean_srt(raw_transcript)

        transcript = ContentDocument(
            id=info.id,
            source_type="video",
            url=url,
            language=language,
            title=info.title,
            thumbnail=info.thumbnail,
            content=transcript_text,
            metadata={"uploader": info.uploader},
        )

        logger.info("Transcript loaded successfully", extra={"url": url, "length": len(transcript_text)})

        self._cleanup_subtitle_files(video_id)

        return transcript

    def _build_ydl_opts(self, extra_options: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Build yt-dlp options with additional user options.

        Args:
            extra_options: Additional options to merge with defaults.

        Returns:
            Dictionary of yt-dlp options.

        Note:
            User-provided options are filtered to prevent injection attacks.
            Only safe options (starting with --) are allowed.
        """
        opts: dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
        }
        if extra_options:
            opts.update(extra_options)
        # Add user-provided options as keyword arguments
        i = 0
        while i < len(self.yt_dlp_additional_options):
            opt = self.yt_dlp_additional_options[i]
            if opt.startswith("--"):
                key = opt[2:].replace("-", "_")
                # Check if next option is a value (not another flag)
                if i + 1 < len(self.yt_dlp_additional_options) and not self.yt_dlp_additional_options[i + 1].startswith("--"):
                    value = self.yt_dlp_additional_options[i + 1]
                    # Validate value to prevent injection attacks
                    if not _is_safe_option_value(value):
                        logger.warning(
                            "Skipping unsafe yt-dlp option value",
                            extra={"key": key, "value_length": len(value)},
                        )
                        i += 2
                        continue
                    opts[key] = value
                    i += 1
                else:
                    opts[key] = True
            i += 1
        return opts

    def _get_video_hash(self, url: str) -> str:
        """Return the cache key for this video URL."""
        return hashlib.sha256(url.encode("utf-8")).hexdigest()

    def _get_subtitle_template_path(self, video_id: str) -> str:
        """Generate template path for subtitle files in temp directory."""
        temp_dir = Path(tempfile.gettempdir())
        return str(temp_dir / f"subtitles_{video_id}.%(ext)s")

    def _get_subtitle_prefix(self, video_id: str) -> Path:
        """Get prefix for subtitle file names in temp directory."""
        return Path(tempfile.gettempdir()) / f"subtitles_{video_id}"

    def _detect_language(self, info: VideoInfo) -> str:
        """
        Detect the best available subtitle language.

        Priority:
        1. Video's native language
        2. English if available
        3. First available subtitle track

        Args:
            info: VideoInfo object with subtitle information.

        Returns:
            Language code (e.g., 'en', 'ru').

        Raises:
            RuntimeError: If no subtitles are available.
        """
        if info.language:
            return info.language.split("-", maxsplit=1)[0]

        if not info.subtitles:
            raise RuntimeError("no subtitles available")

        # Fallback to English if exists
        if "en" in info.subtitles:
            return "en"

        # Get first available language from subtitles
        return next(iter(info.subtitles.keys())).split("-", maxsplit=1)[0]

    def _find_subtitle_file(self, video_id: str, language: str) -> Path | None:
        """
        Find downloaded subtitle file for the given language.

        Searches in order:
        1. Exact language match (.en.srt or .en.vtt)
        2. Auto-generated subtitles (.en_auto.srt or .en_auto.vtt)
        3. Any matching file (.srt or .vtt)

        Args:
            language: Language code to search for.

        Returns:
            Path to subtitle file or None if not found.
        """
        for ext in (".srt", ".vtt"):
            exact = self._get_subtitle_prefix(video_id).with_suffix(f".{language}{ext}")
            if exact.exists():
                return exact

            auto = self._get_subtitle_prefix(video_id).with_suffix(f".{language}_auto{ext}")
            if auto.exists():
                return auto

        candidates: list[Path] = []
        for ext in (".srt", ".vtt"):
            candidates.extend(Path(tempfile.gettempdir()).glob(f"subtitles_{video_id}*{ext}"))

        if candidates:
            return sorted(candidates)[0]

        return None

    def _cleanup_subtitle_files(self, video_id: str) -> None:
        """Remove temporary subtitle files for this video."""
        for path in Path(tempfile.gettempdir()).glob(f"subtitles_{video_id}*"):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Failed to cleanup temp subtitle file", extra={"path": str(path)})
