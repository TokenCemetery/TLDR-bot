# Architecture: Web Page Summarization

## Decision

Use a modular monolith. Add web page summarization as a new content source inside the existing Python application instead of splitting the project into microservices.

## Rationale

The current need is to add one content source. A separate service would add deployment, internal API, retry, auth, observability, and testing overhead before those costs are justified.

Clear internal boundaries provide the useful part of a service split while keeping local development and deployment simple.

## Target Flow

```text
User message
-> Telegram message handler
-> URL extraction
-> Source detector
   -> VideoContentLoader
   -> WebPageContentLoader
-> ContentDocument
-> OpenAISummarizer
-> Markdown-to-Telegram formatting
-> Telegram reply
```

## Extension Point

The web page loader should depend on a replaceable extractor interface.

```text
WebPageLoader
-> WebContentExtractor
   -> StaticHtmlExtractor
   -> future PlaywrightRenderedExtractor
```

This makes later Playwright support a backend swap instead of a Telegram or summarizer rewrite.

## Microservice Option

A microservice split may become useful if browser rendering becomes slow or operationally complex.

Potential future split:

```text
Telegram bot service
-> Content extraction service
   -> static HTML extraction
   -> Playwright extraction
-> LLM summarization
```

This should wait until there is concrete pressure such as high latency, browser pool management, independent scaling needs, or queue-based processing.

