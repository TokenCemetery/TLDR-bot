"""
Compression utilities for cache data.

Supports multiple compression algorithms with automatic detection
via method prefix stored alongside the data.
"""

import gzip
import lzma
import zlib
from enum import Enum
from typing import Any


class CompressionMethod(Enum):
    """Supported compression methods."""

    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"
    LZMA = "lzma"


# Prefix byte to identify compression method (stored as first byte of compressed data)
COMPRESSION_PREFIXES = {
    CompressionMethod.NONE: b"\x00",
    CompressionMethod.GZIP: b"\x01",
    CompressionMethod.ZLIB: b"\x02",
    CompressionMethod.LZMA: b"\x03",
}

PREFIX_TO_METHOD = {v: k for k, v in COMPRESSION_PREFIXES.items()}


class CompressionError(Exception):
    """Raised when compression/decompression fails."""

    pass


def compress(data: bytes, method: CompressionMethod = CompressionMethod.GZIP) -> bytes:
    """
    Compress data with the specified method.

    Args:
        data: Raw bytes to compress.
        method: Compression algorithm to use.

    Returns:
        Compressed bytes with method prefix.

    Raises:
        CompressionError: If compression fails.
    """
    if method == CompressionMethod.NONE:
        return COMPRESSION_PREFIXES[CompressionMethod.NONE] + data

    try:
        if method == CompressionMethod.GZIP:
            compressed = gzip.compress(data, compresslevel=6)
        elif method == CompressionMethod.ZLIB:
            compressed = zlib.compress(data, level=6)
        elif method == CompressionMethod.LZMA:
            compressed = lzma.compress(data, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64)
        else:
            raise CompressionError(f"Unknown compression method: {method}")

        return COMPRESSION_PREFIXES[method] + compressed
    except Exception as e:
        raise CompressionError(f"Compression failed with {method.value}: {e}") from e


def decompress(data: bytes) -> bytes:
    """
    Decompress data, automatically detecting the compression method.

    Args:
        data: Compressed bytes with method prefix.

    Returns:
        Decompressed raw bytes.

    Raises:
        CompressionError: If decompression fails or method is unknown.
    """
    if not data:
        return data

    prefix = data[0:1]
    method = PREFIX_TO_METHOD.get(prefix)

    if method is None:
        raise CompressionError(f"Unknown compression prefix: {prefix!r}")

    payload = data[1:]

    try:
        if method == CompressionMethod.NONE:
            return payload
        elif method == CompressionMethod.GZIP:
            return gzip.decompress(payload)
        elif method == CompressionMethod.ZLIB:
            return zlib.decompress(payload)
        elif method == CompressionMethod.LZMA:
            return lzma.decompress(payload)
        else:
            raise CompressionError(f"Unknown compression method: {method}")
    except Exception as e:
        raise CompressionError(f"Decompression failed: {e}") from e


def get_compression_stats(original: bytes, compressed: bytes) -> dict[str, Any]:
    """
    Calculate compression statistics.

    Args:
        original: Original data size in bytes.
        compressed: Compressed data size in bytes.

    Returns:
        Dictionary with compression ratio and savings.
    """
    if len(original) == 0:
        return {"ratio": 0.0, "savings_percent": 0.0, "original_size": 0, "compressed_size": len(compressed)}

    ratio = len(compressed) / len(original)
    savings_percent = (1 - ratio) * 100

    return {
        "ratio": round(ratio, 3),
        "savings_percent": round(savings_percent, 2),
        "original_size": len(original),
        "compressed_size": len(compressed),
    }
