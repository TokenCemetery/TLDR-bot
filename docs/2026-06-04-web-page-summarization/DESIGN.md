# Design: Web Page Summarization

## User Experience

The user sends one URL in Telegram. If the URL is a supported video, the bot behaves as it does today. If the URL is an ordinary public web page, the bot summarizes the page.

No new command is required for the first version.

## Progress Messages

The existing progress flow should be reused with wording adjusted where needed:

- processing request
- fetching source content
- summarizing
- final summary reply

## Summary Response

The response should include:

- the page title when available
- the original or canonical URL
- the generated localized summary

Long responses should continue using the existing Telegram-safe chunking behavior.

## Failure Messages

The bot should give a clear localized error when:

- no URL is found
- more than one URL is found
- the URL cannot be fetched
- the page is not ordinary HTML
- readable content cannot be extracted
- the LLM summary fails

## Content Extraction Style

Extraction should be inspired by Obsidian Web Clipper:

- keep the readable main article content
- preserve useful title and metadata
- remove page chrome and boilerplate
- produce Markdown or clean text suitable for summarization

