# Content Document Summarization Implementation Plan

## Approach

Introduce the source-neutral document contract first, migrate the video path
onto it, then update prompt construction and provider fallback behavior.
Validate each boundary before running the full quality suite.

## Scope And Assumptions

- Web page fetching and extraction remain out of scope.
- `ContentDocument.content` accepts Markdown or clean text.
- Existing summary cache entries remain valid because keys still derive from
  content and locale.
- The exact file request shape must be confirmed during implementation. No
  `.venv` currently exists, so installed SDK types could not be inspected
  locally while preparing this plan.

## 1. Add ContentDocument

Create `src/load/content_document.py` containing a frozen, typed data model:

- `id`
- `source_type`
- `url`
- `title`
- `language`
- `content`
- optional `thumbnail`
- optional metadata with a concrete typed representation

Update loader tests to cover construction and field mapping.

Dependencies: none.

Verification:

- focused model and loader tests pass;
- strict `mypy` accepts the model;
- the model contains no provider, formatting, or loading logic.

## 2. Migrate Video Loading

Change `VideoDataLoader.load()` and `_load()` to return `ContentDocument`.

Map:

- `transcript` to `content`;
- processed URL to `url`;
- existing video fields to corresponding common fields;
- uploader and other video-only data to `metadata` only if currently needed.

Update cache serialization and deserialization and
`tests/load/test_video_loader.py`.

Dependencies: step 1.

Verification:

- video loading tests pass;
- cached and newly loaded videos return the same document contract;
- existing video metadata and cleaned transcript content are preserved.

## 3. Migrate Telegram Handler

Update `src/client/telegram/handlers/messages.py` to use source-neutral
variable names and fields:

```text
document = await loader.load(url)
summary = await summarizer.summarize(document, language)
```

Build the response from `document.title` and `document.url`. Preserve progress
messages, error translations, chunking, HTML conversion, and link previews.

Update handler tests to assert that the full `ContentDocument` is passed to
the summarizer.

Dependencies: steps 1 and 2.

Verification:

- handler tests pass;
- current video interaction behavior remains unchanged;
- the handler no longer reads transcript-specific fields.

## 4. Split Localized Prompts

Replace `openai.prompt` in every file under `locales/` with:

- `openai.system_prompt`;
- `openai.user_prompt`.

Keep the current language-specific style and summary requirements. Remove
`%{text}` interpolation because source content is supplied separately.

Add or update tests ensuring both keys resolve for every supported locale.

Dependencies: none. This can be implemented in parallel with steps 1 and 2,
but must be complete before step 5.

Verification:

- every supported locale resolves both prompt keys;
- prompt behavior remains equivalent to the existing localized instructions;
- `summarization.py` contains no hardcoded prompt text.

## 5. Implement Request Construction

Change `OpenAISummarizer.summarize()` to accept `ContentDocument`.

Add focused internal request builders for:

- preferred messages containing separate system and task prompts plus
  `source.md`;
- fallback messages containing separate prompts and clearly delimited inline
  Markdown.

Before choosing types, create the project virtual environment or otherwise
inspect the resolved OpenAI SDK version. Determine whether file content is
available through `chat.completions`, another compatible endpoint, or
provider-supported content parts.

Avoid a remote file upload lifecycle unless the installed SDK and target
provider APIs make it unavoidable.

Dependencies: steps 1 and 4.

Decision point:

- If no common file representation exists across the configured API surface,
  use the closest SDK-supported file-content part as the preferred path and
  retain inline Markdown as the compatibility guarantee.

Verification:

- request payload tests verify separate system and user prompts;
- the preferred payload identifies the document as `source.md`;
- fallback payloads delimit source Markdown from task instructions;
- configured model and timeout values are preserved.

## 6. Add Narrow Fallback Classification

Implement a focused predicate for identifying unsupported file or
content-part errors.

Fallback exactly once only for an identifiable provider rejection of the
preferred format. Do not fallback for:

- authentication or authorization failures;
- rate limits;
- timeouts or network errors;
- invalid models;
- provider server errors;
- empty or malformed successful responses.

Log which request mode was used without logging document contents.

Dependencies: step 5.

Verification:

- mocked unsupported-format errors trigger exactly one inline request;
- unrelated API errors do not trigger fallback;
- preferred and fallback failures preserve useful error context.

## 7. Preserve Response And Cache Behavior

Use one response-validation path for preferred and fallback requests.

Update cache hashing to read `document.content` and retain the output locale in
the cache key. Preserve the existing public `RuntimeError` behavior.

Dependencies: steps 1, 5, and 6.

Verification:

- cache-hit and cache-miss tests pass;
- cache keys still use the content hash and locale;
- empty responses remain errors;
- preferred and fallback responses use identical validation.

## 8. Update Documentation

Update project-scoped documentation that describes the summarizer or loader
boundary:

- `docs/ARCHITECTURE.md`;
- relevant README wording if the public configuration or compatibility
  statement changes;
- the existing web page specification only if implementation details diverge
  from it.

Dependencies: implementation decisions from steps 2, 5, and 6.

Verification:

- documentation consistently describes `ContentDocument`;
- documentation states that Markdown file content is preferred and inline
  Markdown is the compatibility fallback;
- no documentation implies that web page extraction was implemented.

## 9. Verification

Run focused tests first:

```text
.venv/bin/python -m pytest tests/load/test_video_loader.py
.venv/bin/python -m pytest tests/transform/test_summarization.py
.venv/bin/python -m pytest tests/client/telegram/test_handlers.py
```

Then run the repository's complete required checks:

```text
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy .
.venv/bin/python -m pytest
```

Dependencies: steps 1 through 8 and an installed development environment.

Verification:

- all focused tests pass;
- lint, formatting, strict type checking, and the full test suite pass;
- final diff contains no unrelated refactoring or generated-file churn.

## Risks And Mitigations

### Provider File Compatibility

OpenAI-compatible providers expose inconsistent file-content support.

Mitigation: verify the resolved SDK types before implementation, isolate
preferred request construction, and make inline Markdown the guaranteed
fallback.

### Error Classification

Provider error bodies may vary, making unsupported-format detection brittle.

Mitigation: prefer typed status and error fields where available, keep the
predicate narrow, and test representative llama.cpp and OpenRouter failures
without treating every client error as fallback-eligible.

### Loader Contract Change

Changing `VideoDataLoader` affects cache deserialization, handler code, and
tests.

Mitigation: introduce `ContentDocument` first, migrate direct consumers
together, and preserve serialized source data where practical.

## Completion Criteria

- Video content flows through `ContentDocument`.
- The handler and summarizer contain no transcript-specific contract.
- Every locale has separate system and user prompts.
- Preferred requests carry source content as `source.md`.
- Unsupported file formats fall back exactly once to inline Markdown.
- Other errors never cause fallback.
- Cache and Telegram behavior remain compatible.
- Focused tests and the complete quality suite pass.
