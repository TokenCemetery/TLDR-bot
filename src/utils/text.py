"""
Text processing utilities.

Provides functions for chunking text into smaller segments
at natural breakpoints (paragraphs, sentences, words).
"""

from __future__ import annotations


def to_lexical_chunks(text: str, chunk_size: int) -> list[str]:
    """
    Split text into chunks at natural breakpoints.

    Breakpoint priority:
    1. Paragraph boundaries (newlines)
    2. Sentence endings (. ! ?)
    3. Word boundaries (spaces)

    Args:
        text: Input text to split.
        chunk_size: Maximum characters per chunk.

    Returns:
        List of text chunks, each <= chunk_size characters.
    """
    if chunk_size <= 0 or len(text) <= chunk_size:
        return [text.strip()]

    chunks: list[str] = []
    left = 0
    text_length = len(text)

    while left < text_length:
        right = min(left + chunk_size, text_length)
        if right == text_length:
            chunk = text[left:right].strip()
            if chunk:
                chunks.append(chunk)
            break

        right = _find_natural_breakpoint(text, left, right)
        right = min(right, text_length)

        chunk = text[left:right].strip()
        if chunk:
            chunks.append(chunk)

        left = right
        while left < text_length and text[left] in {" ", "\n"}:
            left += 1

    return chunks or [""]


def _find_natural_breakpoint(text: str, left: int, right: int) -> int:
    """
    Find a natural breakpoint in text for chunking.

    Searches for breakpoints in this order:
    1. Newline at right boundary
    2. Last paragraph break (newline)
    3. Last sentence boundary (. ! ?)
    4. Last word boundary (space)
    5. Right boundary as fallback

    Args:
        text: The full text being chunked.
        left: Start index of current chunk.
        right: End index of current chunk.

    Returns:
        Index of the best breakpoint.
    """
    if right < len(text) and text[right] == "\n":
        return right

    piece = text[left:right]

    paragraph_idx = piece.rfind("\n")
    if paragraph_idx > 0:
        return left + paragraph_idx + 1

    sentence_idx = max(piece.rfind("."), piece.rfind("!"), piece.rfind("?"))
    if sentence_idx > 0:
        return left + sentence_idx + 1

    if right < len(text) and text[right] != " ":
        word_idx = piece.rfind(" ")
        if word_idx > 0:
            return left + word_idx + 1

    return right
