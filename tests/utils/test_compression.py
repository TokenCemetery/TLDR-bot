"""
Tests for cache compression utilities.
"""

import pytest
from src.utils.compression import (
    COMPRESSION_PREFIXES,
    CompressionError,
    CompressionMethod,
    compress,
    decompress,
    get_compression_stats,
)


class TestCompressionMethods:
    """Test compression and decompression for all supported methods."""

    @pytest.mark.parametrize(
        "method",
        [
            CompressionMethod.NONE,
            CompressionMethod.GZIP,
            CompressionMethod.ZLIB,
            CompressionMethod.LZMA,
        ],
    )
    def test_compress_decompress_roundtrip(self, method: CompressionMethod) -> None:
        """Test that data can be compressed and decompressed back to original."""
        original_data = b"Hello, World! This is a test string for compression."
        compressed = compress(original_data, method)
        decompressed = decompress(compressed)
        assert decompressed == original_data

    @pytest.mark.parametrize(
        "method",
        [
            CompressionMethod.GZIP,
            CompressionMethod.ZLIB,
            CompressionMethod.LZMA,
        ],
    )
    def test_compression_savings(self, method: CompressionMethod) -> None:
        """Test that compression actually reduces data size for reasonable input."""
        original_data = b"A" * 1000 + b"B" * 1000 + b"C" * 1000
        compressed = compress(original_data, method)
        assert len(compressed) < len(original_data)

    def test_none_compression_no_savings(self) -> None:
        """Test that NONE method adds only prefix byte."""
        original_data = b"Test data"
        compressed = compress(original_data, CompressionMethod.NONE)
        assert len(compressed) == len(original_data) + 1  # +1 for prefix

    def test_empty_data(self) -> None:
        """Test compression of empty data."""
        original_data = b""
        compressed = compress(original_data, CompressionMethod.GZIP)
        decompressed = decompress(compressed)
        assert decompressed == original_data

    def test_large_data(self) -> None:
        """Test compression of larger data."""
        original_data = b"Hello World! " * 10000
        compressed = compress(original_data, CompressionMethod.GZIP)
        decompressed = decompress(compressed)
        assert decompressed == original_data
        assert len(compressed) < len(original_data) * 0.1

    def test_binary_data(self) -> None:
        """Test compression of binary data."""
        original_data = bytes(range(256)) * 100
        compressed = compress(original_data, CompressionMethod.GZIP)
        decompressed = decompress(compressed)
        assert decompressed == original_data

    def test_unicode_text(self) -> None:
        """Test compression of Unicode text."""
        original_data = "Привет мир! Hello world! 你好世界!".encode()
        compressed = compress(original_data, CompressionMethod.GZIP)
        decompressed = decompress(compressed)
        assert decompressed == original_data


class TestCompressionPrefixes:
    """Test compression method prefixes."""

    def test_all_methods_have_unique_prefixes(self) -> None:
        """Test that each compression method has a unique prefix."""
        prefixes = list(COMPRESSION_PREFIXES.values())
        assert len(prefixes) == len(set(prefixes)), "Duplicate prefixes found"

    def test_prefix_is_first_byte(self) -> None:
        """Test that prefix is stored as first byte."""
        for method, expected_prefix in COMPRESSION_PREFIXES.items():
            compressed = compress(b"test data", method)
            assert compressed[0:1] == expected_prefix


class TestDecompressionErrors:
    """Test decompression error handling."""

    def test_unknown_prefix_raises_error(self) -> None:
        """Test that unknown prefix raises CompressionError."""
        with pytest.raises(CompressionError, match="Unknown compression prefix"):
            decompress(b"\xffinvalid data")

    def test_empty_data_returns_empty(self) -> None:
        """Test that empty data returns empty."""
        assert decompress(b"") == b""

    def test_corrupted_data_raises_error(self) -> None:
        """Test that corrupted data raises CompressionError."""
        original = b"test data"
        compressed = compress(original, CompressionMethod.GZIP)
        # Corrupt the payload (keep prefix intact)
        corrupted = compressed[0:1] + b"corrupted" + compressed[5:]
        with pytest.raises(CompressionError, match="Decompression failed"):
            decompress(corrupted)


class TestCompressionStats:
    """Test compression statistics calculation."""

    def test_stats_calculation(self) -> None:
        """Test compression stats are calculated correctly."""
        original = b"A" * 1000
        compressed = compress(original, CompressionMethod.GZIP)
        stats = get_compression_stats(original, compressed)

        assert "ratio" in stats
        assert "savings_percent" in stats
        assert "original_size" in stats
        assert "compressed_size" in stats
        expected_original_size = 1000
        assert stats["original_size"] == expected_original_size
        assert stats["compressed_size"] == len(compressed)
        assert 0 < stats["ratio"] < 1
        assert stats["savings_percent"] > 0

    def test_empty_original_data(self) -> None:
        """Test stats with empty original data."""
        stats = get_compression_stats(b"", b"compressed")
        assert stats["ratio"] == 0.0
        assert stats["savings_percent"] == 0.0
        assert stats["original_size"] == 0

    def test_compression_ratio_for_different_methods(self) -> None:
        """Test that different methods achieve different compression ratios."""
        original = b"Hello World! " * 1000

        gzip_compressed = compress(original, CompressionMethod.GZIP)
        zlib_compressed = compress(original, CompressionMethod.ZLIB)
        lzma_compressed = compress(original, CompressionMethod.LZMA)

        gzip_stats = get_compression_stats(original, gzip_compressed)
        zlib_stats = get_compression_stats(original, zlib_compressed)
        lzma_stats = get_compression_stats(original, lzma_compressed)

        max_ratio = 0.1
        assert gzip_stats["ratio"] < max_ratio
        assert zlib_stats["ratio"] < max_ratio
        assert lzma_stats["ratio"] < max_ratio
