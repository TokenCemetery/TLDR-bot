import pytest
from src.load.video_provider import (
    PROVIDERS,
    VKVIDEO,
    YOUTUBE,
    YOUTUBE_SHORT,
    build_video_source,
    extract_urls,
)


def test_extract_urls_youtube() -> None:
    text = "text https://youtu.be/validID1234 and https://www.youtube.com/watch?v=anotherID12"
    assert extract_urls(text) == [
        "https://youtu.be/validID1234",
        "https://www.youtube.com/watch?v=anotherID12",
    ]


def test_build_video_source_canonicalizes_short_link() -> None:
    canonical, video_id = build_video_source("youtu.be/abcdefghijk")
    assert video_id == "abcdefghijk"
    assert canonical == "https://www.youtube.com/watch?v=abcdefghijk"


def test_extract_urls_youtube_full_urls() -> None:
    text = "Check out https://www.youtube.com/watch?v=dQw4w9WgXcQ and https://youtube.com/watch?v=abc123def45"
    assert extract_urls(text) == [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=abc123def45",
    ]


def test_extract_urls_youtube_with_params() -> None:
    text = "Video: https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=1s&ab_channel=Channel"
    result = extract_urls(text)
    assert len(result) == 1
    assert result[0] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_extract_urls_youtube_shorts() -> None:
    text = "Short: https://www.youtube.com/shorts/abcdefghijk and https://youtube.com/shorts/xyz123"
    extracted = extract_urls(text)
    # Only the first one should match since the pattern doesn't include non-www youtube.com/shorts
    assert len(extracted) == 1
    assert extracted[0] == "https://www.youtube.com/shorts/abcdefghijk"


def test_extract_urls_vkvideo() -> None:
    text = "VK: https://vkvideo.ru/video-123456_789012 and http://www.vkvideo.ru/video-987654_321098"
    assert extract_urls(text) == [
        "https://vkvideo.ru/video-123456_789012",
        "http://www.vkvideo.ru/video-987654_321098",
    ]


def test_extract_urls_mixed_providers() -> None:
    # Since PROVIDERS = (YOUTUBE, YOUTUBE_SHORT, VKVIDEO), it will match YouTube URLs first
    text = "YouTube: https://youtu.be/abcdefghijk, Shorts: https://www.youtube.com/shorts/klmnopqrstu, VK: https://vkvideo.ru/video-123_456"
    extracted = extract_urls(text)
    assert len(extracted) == 1
    assert extracted[0] == "https://youtu.be/abcdefghijk"


def test_extract_urls_no_urls() -> None:
    text = "This text contains no video URLs"
    assert extract_urls(text) == []


def test_extract_urls_invalid_urls() -> None:
    text = "Invalid: https://youtube.com/invalid, https://youtu.be/, https://vkvideo.ru/"
    assert extract_urls(text) == []


def test_build_video_source_youtube_full_url() -> None:
    canonical, video_id = build_video_source("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert video_id == "dQw4w9WgXcQ"
    assert canonical == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"


def test_build_video_source_youtube_with_params() -> None:
    canonical, video_id = build_video_source("https://www.youtube.com/watch?v=abc123def45&t=30s")
    assert video_id == "abc123def45"
    assert canonical == "https://www.youtube.com/watch?v=abc123def45"


def test_build_video_source_youtube_shorts() -> None:
    canonical, video_id = build_video_source("https://www.youtube.com/shorts/abcdefghijk")
    assert video_id == "abcdefghijk"
    assert canonical == "https://www.youtube.com/shorts/abcdefghijk"


def test_build_video_source_vkvideo() -> None:
    canonical, video_id = build_video_source("https://vkvideo.ru/video-123456_789012")
    assert video_id == "video-123456_789012"
    assert canonical == "https://vkvideo.ru/video-123456_789012"


def test_build_video_source_invalid_url() -> None:
    with pytest.raises(ValueError, match="no valid URL found"):
        build_video_source("https://invalid.com/video")


def test_youtube_provider_is_valid_url() -> None:
    assert YOUTUBE.is_valid_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert YOUTUBE.is_valid_url("https://youtu.be/abc123def45")
    assert not YOUTUBE.is_valid_url("https://www.twitch.tv/user")


def test_youtube_short_provider_is_valid_url() -> None:
    assert YOUTUBE_SHORT.is_valid_url("https://www.youtube.com/shorts/abcdefghijk")
    # The pattern doesn't match non-www youtube.com/shorts URLs
    assert not YOUTUBE_SHORT.is_valid_url("http://youtube.com/shorts/xyz123")
    assert not YOUTUBE_SHORT.is_valid_url("https://www.youtube.com/watch?v=abc123")


def test_vkvideo_provider_is_valid_url() -> None:
    assert VKVIDEO.is_valid_url("https://vkvideo.ru/video-123456_789012")
    assert VKVIDEO.is_valid_url("http://www.vkvideo.ru/video-987654_321098")
    assert not VKVIDEO.is_valid_url("https://vk.com/video-123456_789012")


def test_youtube_provider_get_id() -> None:
    assert YOUTUBE.get_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"
    assert YOUTUBE.get_id("https://youtu.be/abc123def45") == "abc123def45"


def test_youtube_short_provider_get_id() -> None:
    assert YOUTUBE_SHORT.get_id("https://www.youtube.com/shorts/abcdefghijk") == "abcdefghijk"


def test_vkvideo_provider_get_id() -> None:
    assert VKVIDEO.get_id("https://vkvideo.ru/video-123456_789012") == "video-123456_789012"


def test_all_providers_defined() -> None:
    expected_provider_count = 3
    assert len(PROVIDERS) == expected_provider_count
    assert YOUTUBE in PROVIDERS
    assert YOUTUBE_SHORT in PROVIDERS
    assert VKVIDEO in PROVIDERS
