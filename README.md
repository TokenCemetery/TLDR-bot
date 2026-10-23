# YouTube Briefly Bot

A Telegram bot written in Python that summarizes Video content using LLM.

## Stack

- `aiogram`
- `aiohttp-socks`
- `python-dotenv`
- `python-i18n[YAML]`
- `openai`
- `yt-dlp`
- `Markdown`, `bs4`
- `valkey`

## Features

- 🎬 **Video URL Extraction** — automatically finds Video links in messages
- 📝 **Subtitle Download** — downloads and processes subtitles via `yt-dlp`
- 🤖 **AI Summarization** — creates transcript summaries via OpenAI-compatible API
- 🌍 **Localization** — supports 13 languages (en, ru, de, es, fr, it, pt, ar, zh, cn, ja, ko, hi)
- ⏱️ **Rate Limiting** — abuse protection with per-user cooldown
- ⚡ **Caching & Scaling** — Valkey-backed state provider for transcripts, summaries, and rate limits, enabling horizontal scaling
- 📊 **Message Chunking** — automatic splitting of long responses into parts

## Supported Platforms

- YouTube (regular videos and Shorts)
- VK Video

## Requirements

- Python 3.11+
- `ffmpeg` (recommended by yt-dlp)
- `valkey` (optional, recommended for production scale and distributed rate-limiting)

## Quick Start

### 1. Clone and Setup

```bash
git clone https://github.com/TokenCemetery/TLDR-bot.git
cd TLDR-bot
cp .env.example .env
```

### 2. Configure `.env`

```env
TELEGRAM_BOT_TOKEN=your_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_BASE_URL=https://api.openai.com/v1/
LOG_LEVEL=INFO
```

### 3. Install Dependencies

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

### 4. Install Git Hooks (optional)

```bash
chmod +x install-hooks.sh
./install-hooks.sh
```

This enables pre-commit hooks that run tests and linting before each commit.

### 5. Run the Bot

```bash
.venv/bin/python -m src.client.telegram.main
```

## VS Code Setup

This project includes pre-configured VS Code settings for optimal Python development.

### Recommended Extensions

Install the recommended extensions:

```bash
# Open the Command Palette (Cmd+Shift+P) and run:
# "Extensions: Show Recommended Extensions"
```

Or install via CLI:

```bash
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension ms-python.debugpy
code --install-extension ms-python.isort
code --install-extension charliermarsh.ruff
code --install-extension tamasfe.even-better-toml
code --install-extension redhat.vscode-yaml
```

### Available Tasks

Open the Command Palette (`Cmd+Shift+P` or `Ctrl+Shift+P`) → **Tasks: Run Task**:

| Task              | Description                                                  |
| ----------------- | ------------------------------------------------------------ |
| `python: install` | Install dependencies from pyproject.toml into `.venv`        |
| `python: run`     | Run the bot application                                      |
| `python: format`  | Format code with Ruff                                        |
| `python: lint`    | Format, then run `ruff check --fix` and `mypy` on src/tests  |
| `python: test`    | Format and lint, then run the pytest suite (default build task) |

### Debug Configurations

Press `F5` to start debugging. Available configurations:

| Configuration           | Description             |
| ----------------------- | ----------------------- |
| `🐍 Run Bot`            | Debug the bot           |
| `🧪 Test All`           | Debug all tests         |
| `🧪 Test Current File`  | Debug current test file |
| `🧪 Test with Coverage` | Run tests with coverage |

### Keyboard Shortcuts

- **Run Tests** (default build task): `Cmd+Shift+B` (macOS) / `Ctrl+Shift+B` (Windows/Linux)
- **Debug Bot**: `F5` with the `🐍 Run Bot` configuration
- **Format Code**: `Shift+Alt+F` (default)
- **Quick Fix**: `Cmd+.` (macOS) / `Ctrl+.` (Windows/Linux)

## Environment Variables

| Variable                       | Description                        | Default                          |
| ------------------------------ | ---------------------------------- | -------------------------------- |
| `TELEGRAM_BOT_TOKEN`           | Telegram bot token (required)      | —                                |
| `TELEGRAM_PROXY_URL`           | Proxy URL for Telegram API         | —                                |
| `OPENAI_API_KEY`               | LLM API key (required)             | —                                |
| `OPENAI_MODEL`                 | Model for summarization (required) | —                                |
| `OPENAI_BASE_URL`              | OpenAI-compatible API base URL     | `https://api.openai.com/v1/`     |
| `OPENAI_TIMEOUT_SECONDS`       | LLM request timeout                | `300`                            |
| `OPENAI_MAX_RETRIES`           | LLM max retry attempts             | `3`                              |
| `YT_DLP_ADDITIONAL_OPTIONS`    | Additional yt-dlp options          | —                                |
| `VALKEY_URL`                   | Valkey connection URL (optional)   | —                                |
| `CACHE_SUMMARY_TTL_SECONDS`    | TTL for cached summaries           | `3600` (local), `86400` (Valkey) |
| `CACHE_TRANSCRIPT_TTL_SECONDS` | TTL for cached transcripts         | `3600` (local), `86400` (Valkey) |
| `CACHE_COMPRESSION_METHOD`     | Compression for Valkey cache       | `gzip` (none, gzip, zlib, lzma)  |
| `MAX_TELEGRAM_MESSAGE_LENGTH`  | Max length for Telegram messages   | `3500`                           |
| `RATE_LIMIT_WINDOW_SECONDS`    | Cooldown between user requests     | `10`                             |
| `LOG_LEVEL`                    | Logging level                      | `INFO`                           |

## Tests

```bash
# Run all tests
.venv/bin/python -m pytest

# Run with coverage
.venv/bin/python -m pytest --cov=src

# Run specific module
.venv/bin/python -m pytest tests/test_config.py
```

## Docker

### Build Image

```bash
docker build -f .devops/Telegram.Dockerfile -t ghcr.io/olegshulyakov/go-briefly-bot .
```

### Run Container

```bash
# Using docker run
docker run -d \
  --name go-briefly-bot \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -e OPENAI_BASE_URL=https://api.openai.com/v1/ \
  -e OPENAI_API_KEY=your_key \
  -e OPENAI_MODEL=gpt-4o-mini \
  ghcr.io/olegshulyakov/go-briefly-bot
```

### Docker Compose

```bash
docker compose up -d
```

## Localization

The bot supports the following languages:

- 🇬🇧 English (`en`)
- 🇷🇺 Русский (`ru`)
- 🇩🇪 Deutsch (`de`)
- 🇪🇸 Español (`es`)
- 🇫🇷 Français (`fr`)
- 🇮🇹 Italiano (`it`)
- 🇵🇹 Português (`pt`)
- 🇸🇦 العربية (`ar`)
- 🇨🇳 中文 (`zh`, `cn`)
- 🇯🇵 日本語 (`ja`)
- 🇰🇷 한국어 (`ko`)
- 🇮🇳 हिन्दी (`hi`)

Language is detected from the user's Telegram language setting.

## License

[MIT License](LICENSE)
