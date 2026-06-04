# Roadmap

## Near Term

- Introduce a common content document model for summaries.
- Add a source detector that can distinguish supported videos from ordinary web pages.
- Add a static web page loader for public HTML pages.
- Reuse the current summarizer, cache, localization, and Telegram reply flow.

## Medium Term

- Add source-aware summary prompts if video and article summaries need different formats.
- Improve metadata extraction for title, site name, author, canonical URL, and language.
- Add richer tests for cache behavior and extraction failure cases.
- Add configuration for maximum fetched page size and request timeout.

## Later

- Add optional Playwright extraction behind the same web extraction interface.
- Add queueing for long-running extraction if needed.
- Consider extracting browser-based content loading into a separate service only if operational pressure justifies it.

