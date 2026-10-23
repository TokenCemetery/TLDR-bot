from src.utils.markdown import markdown_to_telegram_html


def test_markdown_to_telegram_html_with_empty_text() -> None:
    assert markdown_to_telegram_html("") == ""


def test_markdown_to_telegram_html_with_bold() -> None:
    result = markdown_to_telegram_html("**bold text**")
    assert "<strong>bold text</strong>" in result


def test_markdown_to_telegram_html_with_italic() -> None:
    result = markdown_to_telegram_html("*italic text*")
    assert "<em>italic text</em>" in result


def test_markdown_to_telegram_html_with_underline() -> None:
    result = markdown_to_telegram_html("<u>underlined text</u>")
    assert "<u>underlined text</u>" in result


def test_markdown_to_telegram_html_with_strikethrough() -> None:
    result = markdown_to_telegram_html("<del>deleted text</del>")
    assert "<del>deleted text</del>" in result


def test_markdown_to_telegram_html_with_link() -> None:
    result = markdown_to_telegram_html("[link text](https://example.com)")
    assert '<a href="https://example.com">link text</a>' in result


def test_markdown_to_telegram_html_with_inline_code() -> None:
    result = markdown_to_telegram_html("`inline code`")
    assert "<code>inline code</code>" in result


def test_markdown_to_telegram_html_with_code_block() -> None:
    result = markdown_to_telegram_html("```\ncode block\n```")
    assert "<pre>" in result
    assert "code block" in result


def test_markdown_to_telegram_html_with_header_converts_to_bold() -> None:
    result = markdown_to_telegram_html("# Header 1")
    assert "<strong>Header 1</strong>" in result
    assert "<h1>" not in result


def test_markdown_to_telegram_html_with_header_level_2() -> None:
    result = markdown_to_telegram_html("## Header 2")
    assert "<strong>Header 2</strong>" in result
    assert "<h2>" not in result


def test_markdown_to_telegram_html_with_header_level_3() -> None:
    result = markdown_to_telegram_html("### Header 3")
    assert "<strong>Header 3</strong>" in result
    assert "<h3>" not in result


def test_markdown_to_telegram_html_with_list_items() -> None:
    result = markdown_to_telegram_html("- Item 1\n- Item 2")
    assert "- Item 1" in result
    assert "- Item 2" in result
    assert "<li>" not in result


def test_markdown_to_telegram_html_with_ordered_list() -> None:
    result = markdown_to_telegram_html("1. First\n2. Second")
    assert "- First" in result
    assert "- Second" in result


def test_markdown_to_telegram_html_removes_unsupported_tags() -> None:
    result = markdown_to_telegram_html("<div>content</div>")
    assert "<div>" not in result
    assert "content" in result


def test_markdown_to_telegram_html_with_mixed_formatting() -> None:
    md_text = """# Title

**Bold** and *italic* text.

- List item 1
- List item 2

[Link](https://example.com)

`inline code`
"""
    result = markdown_to_telegram_html(md_text)

    assert "<strong>Title</strong>" in result
    assert "<strong>Bold</strong>" in result
    assert "<em>italic</em>" in result
    assert "- List item 1" in result
    assert "- List item 2" in result
    assert '<a href="https://example.com">Link</a>' in result
    assert "<code>inline code</code>" in result
    assert "<h1>" not in result
    assert "<li>" not in result


def test_markdown_to_telegram_html_with_nested_formatting() -> None:
    result = markdown_to_telegram_html("**bold and *italic* inside**")
    assert "<strong>" in result
    assert "<em>" in result


def test_markdown_to_telegram_html_with_code_block_preserves_pre() -> None:
    md_text = """```python
def hello():
    print("Hello")
```"""
    result = markdown_to_telegram_html(md_text)
    assert "<pre>" in result


def test_markdown_to_telegram_html_strips_output() -> None:
    result = markdown_to_telegram_html("  **bold**  ")
    assert result == result.strip()


def test_markdown_to_telegram_html_with_paragraph() -> None:
    result = markdown_to_telegram_html("First paragraph.\n\nSecond paragraph.")
    assert "First paragraph." in result
    assert "Second paragraph." in result


def test_markdown_to_telegram_html_with_strong_tag() -> None:
    result = markdown_to_telegram_html("<strong>strong text</strong>")
    assert "<strong>strong text</strong>" in result


def test_markdown_to_telegram_html_with_em_tag() -> None:
    result = markdown_to_telegram_html("<em>emphasized text</em>")
    assert "<em>emphasized text</em>" in result


def test_markdown_to_telegram_html_with_ins_tag() -> None:
    result = markdown_to_telegram_html("<ins>inserted text</ins>")
    assert "<ins>inserted text</ins>" in result


def test_markdown_to_telegram_html_with_del_tag() -> None:
    result = markdown_to_telegram_html("<del>deleted text</del>")
    assert "<del>deleted text</del>" in result


def test_markdown_to_telegram_html_with_strike_tag() -> None:
    result = markdown_to_telegram_html("<strike>strike text</strike>")
    assert "<strike>strike text</strike>" in result


def test_markdown_to_telegram_html_collapses_multiple_newlines() -> None:
    md_text = "First paragraph.\n\n\n\nSecond paragraph."
    result = markdown_to_telegram_html(md_text)
    assert "\n\n\n" not in result
    assert result.count("\n") < md_text.count("\n")


def test_markdown_to_telegram_html_with_headers_collapses_newlines() -> None:
    md_text = "# Header\n\n\n\nParagraph"
    result = markdown_to_telegram_html(md_text)
    assert "\n\n\n" not in result
