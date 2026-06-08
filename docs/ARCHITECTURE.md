# Architecture

Briefly Bot is a modular monolith. The application runs as one Python service, while major responsibilities are separated into focused modules with explicit boundaries.

## Current Runtime

- Telegram client: receives user messages, sends progress updates, and replies with summaries.
- Source loading: extracts supported video URLs and returns source-neutral `ContentDocument` values with transcripts in `content`.
- Summarization: sends localized system and task prompts plus source Markdown to an OpenAI-compatible API.
- Cache: stores transcripts, summaries, and rate-limit state through an in-memory or Valkey provider.
- Localization: renders bot messages and LLM prompts in the user's language.

## Target Direction

The bot should support multiple summarizable content sources through a common content-loading boundary.

```text
Telegram handler
-> Source detector
-> Content loader
   -> Video content loader
   -> Web page content loader
-> Summarizer
-> Response formatter
-> Telegram reply
```

The application should remain one Python service until there is concrete pressure to split it. Likely reasons to extract a service later include Playwright browser pools, queue-based long-running extraction jobs, separate scaling requirements, or stricter runtime isolation.

## Boundary Principles

- Keep source-specific extraction inside source-specific modules.
- Return a common document model from all loaders.
- Keep Telegram handlers thin: detect input, call loaders, summarize, reply.
- Keep the summarizer independent from content source type.
- Keep cache keys source-aware to avoid collisions between videos and web pages.

## Summarization Requests

The summarizer receives a `ContentDocument` rather than a transcript-specific
value. It sends separate localized system and user prompts and prefers a
Markdown file content part named `source.md`. Providers that explicitly reject
file content parts are retried once with the same Markdown embedded in the user
message. Authentication, rate limits, timeouts, server failures, and unrelated
bad requests do not trigger the inline fallback.
