import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.cache import ValkeyProvider
from src.utils import CompressionMethod, compress


@pytest.fixture
def provider() -> ValkeyProvider:
    return ValkeyProvider("valkey://localhost:6379", compression_method="none")


@pytest.fixture
def provider_with_compression() -> ValkeyProvider:
    return ValkeyProvider("valkey://localhost:6379", compression_method="gzip")


@pytest.mark.asyncio
async def test_valkey_rate_limit_success(provider: ValkeyProvider) -> None:
    with patch("src.cache.valkey.Valkey") as mock_valkey:
        mock_client = AsyncMock()
        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[1])
        mock_client.pipeline = MagicMock(return_value=mock_pipeline)
        mock_valkey.from_url.return_value = mock_client

        is_limited = await provider.is_rate_limited(123, 10)

        assert not is_limited
        mock_client.pipeline.assert_called_once()
        mock_pipeline.incr.assert_called_with("user:123:limit")
        mock_pipeline.expire.assert_called_with("user:123:limit", 10, nx=True)


@pytest.mark.asyncio
async def test_valkey_rate_limit_exceeded(provider: ValkeyProvider) -> None:
    with patch("src.cache.valkey.Valkey") as mock_valkey:
        mock_client = AsyncMock()
        mock_pipeline = MagicMock()
        mock_pipeline.execute = AsyncMock(return_value=[2])
        mock_client.pipeline = MagicMock(return_value=mock_pipeline)
        mock_valkey.from_url.return_value = mock_client

        is_limited = await provider.is_rate_limited(123, 10)

        assert is_limited


@pytest.mark.asyncio
async def test_valkey_set_get_summary(provider: ValkeyProvider) -> None:
    with patch("src.cache.valkey.Valkey") as mock_valkey:
        mock_client = AsyncMock()
        # With compression_method="none", data is stored with \x00 prefix
        expected_value = b"\x00test summary"
        mock_client.get.return_value = expected_value
        mock_valkey.from_url.return_value = mock_client

        await provider.put("summary:hash123:en", "test summary", 3600)
        mock_client.setex.assert_called_with("summary:hash123:en:none", 3600, expected_value)

        text = await provider.get("summary:hash123:en")
        assert text == "test summary"
        mock_client.get.assert_called_with("summary:hash123:en:none")


@pytest.mark.asyncio
async def test_valkey_set_get_summary_with_compression(provider_with_compression: ValkeyProvider) -> None:
    """Test that summary is compressed when stored and decompressed when retrieved."""
    with patch("src.cache.valkey.Valkey") as mock_valkey:
        mock_client = AsyncMock()

        original_summary = "test summary with compression"
        compressed_data = compress(original_summary.encode("utf-8"), CompressionMethod.GZIP)
        mock_client.get.return_value = compressed_data
        mock_valkey.from_url.return_value = mock_client

        text = await provider_with_compression.get("summary:hash123:en")
        assert text == original_summary
        mock_client.get.assert_called_with("summary:hash123:en:gzip")


@pytest.mark.asyncio
async def test_valkey_set_get_summary_multiple_languages(provider: ValkeyProvider) -> None:
    with patch("src.cache.valkey.Valkey") as mock_valkey:
        mock_client = AsyncMock()

        def mock_get(key: str) -> bytes | None:
            if key == "summary:hash123:en:none":
                return b"\x00english summary"
            elif key == "summary:hash123:es:none":
                return b"\x00spanish summary"
            return None

        mock_client.get.side_effect = mock_get
        mock_valkey.from_url.return_value = mock_client

        await provider.put("summary:hash123:en", "english summary", 3600)
        mock_client.setex.assert_any_call("summary:hash123:en:none", 3600, b"\x00english summary")

        await provider.put("summary:hash123:es", "spanish summary", 3600)
        mock_client.setex.assert_any_call("summary:hash123:es:none", 3600, b"\x00spanish summary")

        summary_en = await provider.get("summary:hash123:en")
        assert summary_en == "english summary"

        summary_es = await provider.get("summary:hash123:es")
        assert summary_es == "spanish summary"


@pytest.mark.asyncio
async def test_valkey_set_get_transcript(provider: ValkeyProvider) -> None:
    with patch("src.cache.valkey.Valkey") as mock_valkey:
        mock_client = AsyncMock()
        transcript_json = '{"text": "hello"}'
        expected_value = b"\x00" + transcript_json.encode("utf-8")
        mock_client.get.return_value = expected_value
        mock_valkey.from_url.return_value = mock_client

        await provider.put_dict("transcript:hash123", {"text": "hello"}, 3600)
        mock_client.setex.assert_called_with("transcript:hash123:none", 3600, expected_value)

        data = await provider.get_dict("transcript:hash123")
        assert data == {"text": "hello"}
        mock_client.get.assert_called_with("transcript:hash123:none")


@pytest.mark.asyncio
async def test_valkey_set_get_transcript_with_compression(provider_with_compression: ValkeyProvider) -> None:
    """Test that transcript is compressed when stored and decompressed when retrieved."""
    with patch("src.cache.valkey.Valkey") as mock_valkey:
        mock_client = AsyncMock()

        original_transcript = {"text": "hello world", "duration": 120}
        compressed_data = compress(
            json.dumps(original_transcript).encode("utf-8"),
            CompressionMethod.GZIP,
        )
        mock_client.get.return_value = compressed_data
        mock_valkey.from_url.return_value = mock_client

        data = await provider_with_compression.get_dict("transcript:hash123")
        assert data == original_transcript
        mock_client.get.assert_called_with("transcript:hash123:gzip")
