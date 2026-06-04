# Design

Briefly Bot should feel like a single-purpose assistant: the user sends a link and receives a useful summary in the same chat.

## Interaction Model

- The user sends one supported URL.
- The bot detects whether the URL points to a video or an ordinary public web page.
- The bot shows progress while it loads source content and generates a summary.
- The bot replies with the original link, source title when available, and localized summary.
- Long responses are split into Telegram-safe chunks.

## Web Page Summary Behavior

Web page summarization should follow the same Telegram behavior as video summarization. It should not require a new command for the first version.

For ordinary public pages, the bot should extract readable article-like content, convert it into Markdown or clean text, and summarize that content. The extraction behavior should be inspired by Obsidian Web Clipper: preserve the useful page title and main readable content while removing navigation, ads, scripts, repeated boilerplate, and unrelated page chrome.

## Out Of Scope For First Version

- JavaScript-heavy pages that require browser rendering.
- Logged-in pages.
- Paywalled pages.
- PDF summarization.
- Multi-URL messages.
- Exact compatibility with Obsidian Web Clipper internals.

