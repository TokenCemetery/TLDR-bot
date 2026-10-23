from src.utils.text import to_lexical_chunks


def test_to_lexical_chunks_handles_empty_text() -> None:
    assert to_lexical_chunks("", 10) == [""]


def test_to_lexical_chunks_with_chunk_size_zero() -> None:
    text = "Hello world"
    assert to_lexical_chunks(text, 0) == [text]


def test_to_lexical_chunks_with_negative_chunk_size() -> None:
    text = "Hello world"
    assert to_lexical_chunks(text, -5) == [text]


def test_to_lexical_chunks_with_chunk_size_larger_than_text() -> None:
    text = "Short text"
    assert to_lexical_chunks(text, 100) == [text]


def test_to_lexical_chunks_splits_on_paragraphs() -> None:
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    result = to_lexical_chunks(text, 20)
    assert result == ["First paragraph.", "Second paragraph.", "Third paragraph."]


def test_to_lexical_chunks_splits_on_sentences() -> None:
    text = "First sentence. Second sentence! Third sentence? Fourth sentence."
    result = to_lexical_chunks(text, 20)
    assert result == [
        "First sentence.",
        "Second sentence!",
        "Third sentence?",
        "Fourth sentence.",
    ]


def test_to_lexical_chunks_splits_on_words_when_no_sentence_breaks() -> None:
    text = "This is a sentence without sentence breaks but with multiple words"
    expected_max = 10
    result = to_lexical_chunks(text, expected_max)
    assert all(len(chunk) <= expected_max or " " not in chunk for chunk in result)


def test_to_lexical_chunks_handles_leading_trailing_whitespace() -> None:
    text = "   Hello world   "
    result = to_lexical_chunks(text, 10)
    assert result == ["Hello", "world"]


def test_to_lexical_chunks_handles_multiple_spaces() -> None:
    text = "Word    with    multiple    spaces"
    result = to_lexical_chunks(text, 10)
    assert result == ["Word", "with", "multiple", "spaces"]


def test_to_lexical_chunks_handles_newlines_in_middle() -> None:
    text = "Line one\nLine two\nLine three"
    result = to_lexical_chunks(text, 15)
    assert result == ["Line one", "Line two", "Line three"]


def test_to_lexical_chunks_keeps_word_boundaries_when_possible() -> None:
    text = "This is a very long paragraph that exceeds the chunk size and should be split."
    assert to_lexical_chunks(text, 15) == [
        "This is a very",
        "long paragraph",
        "that exceeds",
        "the chunk size",
        "and should be",
        "split.",
    ]
