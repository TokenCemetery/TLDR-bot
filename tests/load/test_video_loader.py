from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.config import Settings
from src.load.content_document import ContentDocument
from src.load.video_loader import VideoDataLoader, VideoInfo, _is_safe_option_value


def build_settings(**overrides: object) -> Settings:
    settings = MagicMock(spec=Settings)
    settings.yt_dlp_additional_options = ()
    settings.cache_transcript_ttl_seconds = 3600
    settings.valkey_url = None
    settings.cache_compression_method = "gzip"
    for key, value in overrides.items():
        setattr(settings, key, value)
    return settings


def test_video_info_creation() -> None:
    info = VideoInfo(
        id="test_id",
        language="en",
        uploader="test_uploader",
        title="test_title",
        thumbnail="test_thumbnail",
        subtitles={"en": [{"url": "sub_url"}]},
    )

    assert info.id == "test_id"
    assert info.language == "en"
    assert info.uploader == "test_uploader"
    assert info.title == "test_title"
    assert info.thumbnail == "test_thumbnail"
    assert info.subtitles == {"en": [{"url": "sub_url"}]}


def test_content_document_creation() -> None:
    transcript = ContentDocument(
        id="test_id",
        source_type="video",
        url="https://example.com/video",
        language="en",
        title="test_title",
        thumbnail="test_thumbnail",
        content="test transcript",
        metadata={"uploader": "test_uploader"},
    )

    assert transcript.id == "test_id"
    assert transcript.source_type == "video"
    assert transcript.url == "https://example.com/video"
    assert transcript.language == "en"
    assert transcript.metadata["uploader"] == "test_uploader"
    assert transcript.title == "test_title"
    assert transcript.thumbnail == "test_thumbnail"
    assert transcript.content == "test transcript"


def test_video_data_loader_initialization() -> None:
    settings = build_settings()
    loader = VideoDataLoader(settings)

    assert loader.settings == settings
    assert loader.yt_dlp_additional_options == ()


def test_video_data_loader_initialization_with_options() -> None:
    loader = VideoDataLoader(
        build_settings(yt_dlp_additional_options=("--format", "mp4")),
    )

    assert loader.yt_dlp_additional_options == ("--format", "mp4")


@pytest.mark.asyncio
async def test_video_data_loader_maps_legacy_cached_transcript() -> None:
    loader = VideoDataLoader(build_settings())
    loader.cache_provider = AsyncMock()
    loader.cache_provider.get_dict.return_value = {
        "id": "test_id",
        "language": "en",
        "uploader": "test_uploader",
        "title": "test_title",
        "thumbnail": "test_thumbnail",
        "transcript": "test transcript",
    }

    document = await loader.load("https://youtu.be/test1234567")

    assert document == ContentDocument(
        id="test_id",
        source_type="video",
        url="https://www.youtube.com/watch?v=test1234567",
        title="test_title",
        language="en",
        content="test transcript",
        thumbnail="test_thumbnail",
        metadata={"uploader": "test_uploader"},
    )


def test_video_data_loader_subtitle_template_path() -> None:
    with patch("tempfile.gettempdir") as mock_temp:
        mock_temp.return_value = "/tmp"

        loader = VideoDataLoader(build_settings())
        expected_path = "/tmp/subtitles_test.%(ext)s"

        assert loader._get_subtitle_template_path("test") == expected_path


def test_video_data_loader_subtitle_prefix() -> None:
    with patch("tempfile.gettempdir") as mock_temp:
        mock_temp.return_value = "/tmp"

        loader = VideoDataLoader(build_settings())
        expected_prefix = Path("/tmp/subtitles_test")

        assert loader._get_subtitle_prefix("test") == expected_prefix


def test_detect_language_with_video_info_language() -> None:
    loader = VideoDataLoader(build_settings())

    info = VideoInfo(
        id="test_id",
        language="es-ES",  # Full language code with region
        uploader="test_uploader",
        title="test_title",
        thumbnail="test_thumbnail",
        subtitles={},
    )

    # Should return base language without region
    assert loader._detect_language(info) == "es"


def test_detect_language_with_subtitles_en_priority() -> None:
    loader = VideoDataLoader(build_settings())

    info = VideoInfo(
        id="test_id",
        language="",  # No language specified
        uploader="test_uploader",
        title="test_title",
        thumbnail="test_thumbnail",
        subtitles={"en": [], "es": []},  # English available
    )

    # Should prefer English when available
    assert loader._detect_language(info) == "en"


def test_detect_language_with_subtitles_first_available() -> None:
    loader = VideoDataLoader(build_settings())

    info = VideoInfo(
        id="test_id",
        language="",  # No language specified
        uploader="test_uploader",
        title="test_title",
        thumbnail="test_thumbnail",
        subtitles={"fr-FR": [], "de": []},  # No English available
    )

    # Should return first available language (fr)
    assert loader._detect_language(info) == "fr"


def test_detect_language_no_subtitles_or_language() -> None:
    loader = VideoDataLoader(build_settings())

    info = VideoInfo(
        id="test_id",
        language="",  # No language specified
        uploader="test_uploader",
        title="test_title",
        thumbnail="test_thumbnail",
        subtitles={},  # No subtitles available
    )

    # Should raise RuntimeError when no subtitles available
    with pytest.raises(RuntimeError, match="no subtitles available"):
        loader._detect_language(info)


def test_find_subtitle_file_exact_match() -> None:
    with patch("tempfile.gettempdir") as mock_temp:
        mock_temp.return_value = "/tmp"

        loader = VideoDataLoader(build_settings())

        with patch("tempfile.gettempdir", return_value="/tmp"):
            with patch.object(Path, "exists", return_value=True):
                result = loader._find_subtitle_file("test", "en")
                expected_path = Path("/tmp") / "subtitles_test.en.srt"
                assert result == expected_path


def test_build_ydl_opts_base_options() -> None:
    loader = VideoDataLoader(build_settings())
    opts = loader._build_ydl_opts()

    assert opts["quiet"] is True
    assert opts["no_warnings"] is True
    assert opts["extract_flat"] is False


def test_build_ydl_opts_with_extra_options() -> None:
    loader = VideoDataLoader(build_settings())
    opts = loader._build_ydl_opts({"dumpjson": True, "skip_download": True})

    assert opts["dumpjson"] is True
    assert opts["skip_download"] is True


def test_build_ydl_opts_with_user_options() -> None:
    loader = VideoDataLoader(
        build_settings(yt_dlp_additional_options=("--format", "mp4", "--cookies", "cookies.txt")),
    )
    opts = loader._build_ydl_opts()

    assert opts["format"] == "mp4"
    assert opts["cookies"] == "cookies.txt"


@patch("yt_dlp.YoutubeDL")
def test_load_success(mock_youtube_dl_class: MagicMock) -> None:
    # Mock the context manager
    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_youtube_dl_class.return_value = mock_ydl

    # First call: extract_info for video info
    # Second call: extract_info for subtitles
    mock_ydl.extract_info.side_effect = [
        {
            "id": "test_id",
            "language": "en",
            "uploader": "test_uploader",
            "title": "test_title",
            "thumbnail": "test_thumbnail",
            "subtitles": {"en": []},
        },
        None,  # Download returns None
    ]

    # Mock subtitle file
    mock_subtitle_file = MagicMock()
    mock_subtitle_file.read_text.return_value = "1\n00:00:00,000 --> 00:00:01,000\nTest subtitle"
    mock_subtitle_file.exists.return_value = True

    with patch.object(VideoDataLoader, "_find_subtitle_file", return_value=mock_subtitle_file):
        with patch("src.load.video_loader.clean_srt", return_value="Test subtitle"):
            loader = VideoDataLoader(build_settings())
            transcript = loader._load("https://youtu.be/test", "test")

            assert transcript is not None
            assert transcript.id == "test_id"
            assert transcript.content == "Test subtitle"


@patch("yt_dlp.YoutubeDL")
def test_load_retry_on_info_failure(mock_youtube_dl_class: MagicMock) -> None:
    # Mock the context manager
    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_youtube_dl_class.return_value = mock_ydl

    # Fail twice, succeed on third
    mock_ydl.extract_info.side_effect = [
        Exception("Network error"),
        Exception("Network error"),
        {
            "id": "test_id",
            "language": "en",
            "uploader": "test_uploader",
            "title": "test_title",
            "thumbnail": "test_thumbnail",
            "subtitles": {"en": []},
        },
        None,  # Download returns None
    ]

    # Mock subtitle file
    mock_subtitle_file = MagicMock()
    mock_subtitle_file.read_text.return_value = "1\n00:00:00,000 --> 00:00:01,000\nTest subtitle"
    mock_subtitle_file.exists.return_value = True

    with patch.object(VideoDataLoader, "_find_subtitle_file", return_value=mock_subtitle_file):
        with patch("src.load.video_loader.clean_srt", return_value="Test subtitle"):
            loader = VideoDataLoader(build_settings())
            loader._load("https://youtu.be/test", "test")

            # Should have been called 4 times (2 info failures + 1 info success + 1 subtitle download)
            expected_calls = 4
            assert mock_ydl.extract_info.call_count == expected_calls


@patch("yt_dlp.YoutubeDL")
def test_load_failure_all_attempts(mock_youtube_dl_class: MagicMock) -> None:
    # Mock the context manager
    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_youtube_dl_class.return_value = mock_ydl

    # Always fail
    mock_ydl.extract_info.side_effect = Exception("Network error")

    loader = VideoDataLoader(build_settings())
    with pytest.raises(RuntimeError, match="Failed to load video info after 3 attempts"):
        loader._load("https://youtu.be/test", "test")


@patch("yt_dlp.YoutubeDL")
def test_load_no_subtitles_found(mock_youtube_dl_class: MagicMock) -> None:
    # Mock the context manager
    mock_ydl = MagicMock()
    mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
    mock_ydl.__exit__ = MagicMock(return_value=False)
    mock_youtube_dl_class.return_value = mock_ydl

    # Info succeeds, download succeeds but no file found
    mock_ydl.extract_info.side_effect = [
        {
            "id": "test_id",
            "language": "en",
            "uploader": "test_uploader",
            "title": "test_title",
            "thumbnail": "test_thumbnail",
            "subtitles": {"en": []},
        },
        None,
    ]

    with patch.object(VideoDataLoader, "_find_subtitle_file", return_value=None):
        loader = VideoDataLoader(build_settings())
        with pytest.raises(FileNotFoundError, match="no subtitles found"):
            loader._load("https://youtu.be/test", "test")


def test_is_safe_option_value() -> None:
    assert _is_safe_option_value("safe_value") is True
    assert _is_safe_option_value("--option") is True
    assert _is_safe_option_value("https://example.com") is True

    # Path traversal
    assert _is_safe_option_value("../unsafe") is False
    assert _is_safe_option_value("/etc/passwd") is False

    # Shell injection
    assert _is_safe_option_value("val; rm -rf /") is False
    assert _is_safe_option_value("val|ls") is False
    assert _is_safe_option_value("val&ls") is False
    assert _is_safe_option_value("$(rm -rf /)") is False
    assert _is_safe_option_value("`rm -rf /`") is False
    assert _is_safe_option_value("val>out.txt") is False


def test_ydl_opts_filters_unsafe_values() -> None:
    # Include an unsafe option value
    unsafe_settings = build_settings(yt_dlp_additional_options=("--format", "mp4", "--outtmpl", "/etc/passwd"))
    loader = VideoDataLoader(unsafe_settings)
    opts = loader._build_ydl_opts()

    # The safe format should be included, but the unsafe outtmpl should be omitted
    assert opts.get("format") == "mp4"
    assert "outtmpl" not in opts
