# Technical Specification: Web Page Summarization

## Overview

Implement web page summarization as a modular-monolith extension. The project stays in Python and adds a native static web page loader inspired by Obsidian Web Clipper behavior.

The first version fetches ordinary public HTML pages, extracts readable main content, converts that content to Markdown or clean text, and passes it to the existing summarizer.

## Proposed Modules

- `src/load/content_document.py`: common document model returned by all content loaders.
- `src/load/source_detector.py`: detects whether a message URL is a video source or a generic web page.
- `src/load/web_page_loader.py`: fetches and loads ordinary public web pages.
- `src/load/web_content_extractor.py`: extracts readable content and metadata from HTML.
- Existing `src/load/video_loader.py`: remains responsible for video transcripts.

Exact file names can be adjusted during implementation to fit repository conventions, but no source-specific web logic should be added to `video_provider.py`.

## Common Document Model

All loaders should return a common document object with fields similar to:

```text
id
source_type
url
title
language
thumbnail
content
metadata
```

Video loaders can map transcript text into `content`. Web page loaders can map extracted Markdown or clean text into `content`.

## Web Extraction

The web loader should:

- Validate `http` and `https` URLs.
- Reject known video URLs so they continue through the video path.
- Fetch HTML with explicit timeout and size limits.
- Reject unsupported content types.
- Extract title, canonical URL, site name, and readable body where available.
- Remove scripts, styles, navigation, footers, ads, and boilerplate where possible.
- Convert readable HTML to Markdown or clean text.
- Cache extracted page content with a source-aware cache key.

## Summarization

The existing `OpenAISummarizer` should be reused. If article summaries later need different formatting from video summaries, add source-aware prompt selection as a later enhancement.

## Error Handling

The web loading path should raise domain-specific errors for:

- invalid URL
- unsupported content type
- fetch timeout
- fetch failure
- content too large
- no readable content

Telegram handlers should translate those failures into localized user-facing messages.

## Future Playwright Support

Playwright should be added later as an alternative extraction backend, not as a replacement for the loader contract.

```text
WebContentExtractor
-> StaticHtmlExtractor
-> PlaywrightRenderedExtractor
```

A future config value such as `WEB_EXTRACTOR_MODE=static|browser` can choose the backend.

