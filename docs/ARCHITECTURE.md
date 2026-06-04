# Architecture

Briefly Bot is a modular monolith. The application runs as one Python service, while major responsibilities are separated into focused modules with explicit boundaries.

## Current Runtime

- Telegram client: receives user messages, sends progress updates, and replies with summaries.
- Source loading: extracts supported video URLs and loads video transcripts with `yt-dlp`.
- Summarization: sends cleaned source text to an OpenAI-compatible API.
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

