"""
Markdown to Telegram HTML converter.

Converts Markdown syntax to Telegram-compatible HTML format.
Handles unsupported tags by converting them to safe alternatives.
"""

import re

import markdown
from bs4 import BeautifulSoup

# Telegram-supported HTML tags
ALLOWED_TAGS = frozenset(["b", "strong", "i", "em", "u", "ins", "s", "strike", "del", "a", "code", "pre"])

HEADER_TAGS = frozenset(["h1", "h2", "h3", "h4", "h5", "h6"])


def markdown_to_telegram_html(md_text: str) -> str:
    """
    Convert Markdown text to Telegram-compatible HTML.

    Process:
    1. Convert Markdown to HTML using python-markdown
    2. Parse HTML with BeautifulSoup
    3. Replace unsupported tags with Telegram-compatible alternatives
    4. Clean up excessive whitespace

    Args:
        md_text: Input Markdown text.

    Returns:
        Telegram-compatible HTML string.

    Note:
        - Headers are converted to <strong> (bold)
        - List items are prefixed with "- "
        - Unsupported tags are stripped (content preserved)
        - Multiple consecutive newlines are reduced to pairs
    """
    raw_html = markdown.markdown(md_text, extensions=["extra", "codehilite"])
    soup = BeautifulSoup(raw_html, "html.parser")

    for tag in soup.find_all(True):
        if tag.name not in ALLOWED_TAGS:
            if tag.name in HEADER_TAGS:
                tag.name = "strong"
                tag.insert_before("\n")
            elif tag.name == "li":
                tag.insert_before("- ")
                tag.unwrap()
            else:
                tag.unwrap()

    result = str(soup).strip()
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result
