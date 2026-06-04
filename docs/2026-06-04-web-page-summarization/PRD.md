# Product Requirements: Web Page Summarization

## Problem

Briefly Bot currently summarizes video content from YouTube and VK Video. Users also want to summarize ordinary public web pages such as articles, blogs, and documentation pages without leaving Telegram.

## Goal

Allow a user to send one ordinary public web page URL to the bot and receive a localized summary, using the same conversational flow already used for video summaries.

## Users

- Telegram users who want a quick summary of an article or documentation page.
- Existing bot users who already expect link-in, summary-out behavior.

## Requirements

- Detect ordinary HTTP and HTTPS web page URLs.
- Continue supporting current YouTube and VK Video links.
- Accept only one URL per message.
- Fetch public HTML pages without browser rendering.
- Extract readable main content and useful metadata.
- Convert extracted content to Markdown or clean text before summarization.
- Reuse existing OpenAI-compatible summarization.
- Reuse existing localization, rate limiting, caching, message chunking, and Telegram reply behavior.
- Return a clear localized error when a page cannot be fetched or readable content cannot be extracted.

## Non-Goals

- JavaScript-heavy page rendering.
- Authenticated, private, or paywalled content.
- PDF summarization.
- Exact copy of Obsidian Web Clipper implementation.
- Microservice split for the first version.

## Success Criteria

- A user can send a normal article URL and receive a useful summary.
- Existing video summarization behavior remains unchanged.
- Web extraction is isolated enough to replace with Playwright later.
- Tests cover source detection, web loading success, web loading failures, and Telegram routing behavior.

