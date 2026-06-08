# Content Document Summarization

## Outcome

Change the summarization boundary so video transcripts and future web page
content use the same source-neutral document model. Send LLM requests with a
localized system prompt for style, a localized user prompt for the task, and
the source content as a Markdown document when the provider supports it.

Preserve compatibility with OpenAI-compatible providers such as llama.cpp and
OpenRouter by falling back to inline Markdown when file content is unsupported.

## Scope

This change covers:

- a common `ContentDocument` model for summarizable source content;
- adapting video transcript loading to the common document boundary;
- updating the Telegram message handler to consume a `ContentDocument`;
- splitting the current localized combined prompt into system and user prompts;
- sending source content as `source.md` when supported;
- falling back to inline Markdown for providers without file support;
- tests and project documentation affected by the contract change.

This change does not implement web page fetching or extraction. A future web
page loader will return the same `ContentDocument` model and use the same
handler and summarizer flow.

## Architecture

The target flow is:

```text
Telegram message
-> source-specific loader
   -> video transcript loader
   -> future web page loader
-> ContentDocument
-> OpenAISummarizer
-> Telegram response
```

`ContentDocument` is the boundary between content loading and summarization.
The Telegram handler and summarizer must not depend on transcript-specific
field names or source-specific extraction behavior.

## Content Document

Create a focused model in `src/load/content_document.py` with these fields:

- `id`: source-specific stable identifier;
- `source_type`: identifies the source category, initially video;
- `url`: canonical or processed source URL;
- `title`: display title;
- `language`: detected source language when available;
- `content`: Markdown or clean text to summarize;
- `thumbnail`: optional preview image URL;
- `metadata`: optional source-specific metadata.

The initial video path maps the cleaned transcript to `content`. A future web
page path will map extracted Markdown to the same field.

The model should remain a data boundary. It must not contain loading,
summarization, formatting, or provider request logic.

## Localized Prompts

Prompt text remains in the files under `locales/`. Replace the combined
`openai.prompt` entry with two localized entries:

- `openai.system_prompt`: style, structure, output language, and formatting
  rules;
- `openai.user_prompt`: the summarization task and instruction to summarize the
  provided Markdown document.

`summarization.py` must not hardcode prompt text. The source document is not
localized or interpolated into either prompt before request construction.

Each supported locale must define both keys. Existing summary behavior should
remain equivalent: concise output, focus on key points, preserve useful source
structure, and write in the user's selected language.

## Provider Request Strategy

The preferred request contains:

1. a localized system message;
2. a localized user task message;
3. source content represented as a Markdown file named `source.md`.

The implementation must use a request representation supported by the
installed OpenAI Python SDK and preserve the configured model, base URL,
timeout, and retry behavior.

Because OpenAI-compatible providers differ in file-content support, the
summarizer must provide a compatibility fallback:

1. attempt the file-capable request;
2. when the provider rejects the request specifically because the file or
   content-part format is unsupported, retry once with the Markdown content
   appended inline to the user message;
3. return the response through the same validation and logging path.

The inline fallback should clearly delimit the source Markdown from the task
prompt. It must not change the requested style or output language.

## Error Handling

Fallback is allowed only for an identifiable unsupported file or request
content format error.

The summarizer must not perform the fallback for:

- authentication or authorization failures;
- rate limits;
- timeouts or network failures;
- provider server errors;
- invalid model errors;
- empty or malformed successful responses.

Those failures follow the existing error path and are wrapped as a
summarization `RuntimeError`. This prevents duplicate expensive requests for
errors that inline content cannot resolve.

If both the file request and inline fallback fail, expose the fallback failure
through the existing summarization error contract while retaining useful
provider context in logs.

## Handler Flow

The Telegram handler should use source-neutral names:

- load a `ContentDocument`;
- call `summarizer.summarize(document, language)`;
- build the response from `document.title` and `document.url`;
- retain existing progress messages, chunking, Markdown conversion, preview,
  and user-facing failure behavior.

The first implementation still routes only supported video URLs. Source
detection and web page loading remain part of the separate web page
summarization work.

## Cache Behavior

Summary cache identity remains based on:

- a deterministic hash of `document.content`;
- the requested output locale.

This keeps cache behavior independent of the source loader and allows video
transcripts and web page Markdown to share the summarizer contract. Existing
cache entries do not need migration.

## Testing

Focused tests should verify:

- video transcript data maps to `ContentDocument.content`;
- the handler passes a `ContentDocument` to the summarizer;
- localized system and user prompts are loaded separately;
- the preferred request includes `source.md` as Markdown file content;
- a recognized unsupported-file error triggers exactly one inline fallback;
- unrelated API errors do not trigger fallback;
- empty responses remain errors;
- cache lookup and storage use the document content hash and locale;
- existing Telegram response formatting and chunking remain unchanged.

Run the repository's required Python verification:

```text
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy .
.venv/bin/python -m pytest tests/transform/test_summarization.py
.venv/bin/python -m pytest tests/client/telegram/test_handlers.py
.venv/bin/python -m pytest tests/load/test_video_loader.py
```

## Compatibility And Risks

OpenAI-compatible providers do not implement file content uniformly. The
exact file-capable request representation and unsupported-format error
classification must be confirmed against the installed SDK types and tested
with mocked provider errors during implementation.

The inline fallback is the portability guarantee. Providers that do not
support the preferred representation continue to receive separate system and
user instructions with the source Markdown embedded in the user message.

Changing `VideoDataLoader.load()` to return `ContentDocument` affects its tests
and any direct consumers. The implementation should update only those callers
and avoid unrelated loader refactoring.

## Decision

Use the common `ContentDocument` approach. Keep prompts localized and
separated by responsibility. Prefer a Markdown file request and fall back once
to inline Markdown only when the provider clearly does not support the
file-capable request format.
