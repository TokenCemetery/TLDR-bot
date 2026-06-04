# Tasks: Web Page Summarization

## Documentation

- [x] Document modular-monolith direction.
- [x] Document web page summarization requirements.
- [x] Document static extraction design and Playwright migration path.

## Implementation

- [ ] Add common content document model.
- [ ] Add source detector for video URLs and ordinary web page URLs.
- [ ] Add static web page fetcher with timeout, content-type checks, and size limits.
- [ ] Add readable HTML extraction and Markdown or clean-text conversion.
- [ ] Add cache keys for extracted web page content.
- [ ] Update Telegram message handling to route URLs through the source detector.
- [ ] Add localized web page error messages.
- [ ] Update README with web page support and new settings.

## Testing

- [ ] Test source detection for YouTube, VK Video, and generic web URLs.
- [ ] Test successful web page extraction.
- [ ] Test fetch failures and unsupported content types.
- [ ] Test no-readable-content behavior.
- [ ] Test Telegram handler routing for video and web URLs.
- [ ] Run full test suite.

