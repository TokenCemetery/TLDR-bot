# Tests

```bash
# Run all tests
.venv/bin/python -m pytest

# Run with coverage
.venv/bin/python -m pytest --cov=src

# Run specific module
.venv/bin/python -m pytest tests/test_config.py
```

## Prompt Evaluation

`eval/prompt_eval.py` runs the real summarizer against the LLM in `.env` to compare
prompt variants. It is not collected by pytest. Each source is a subtitle file or a video URL;
summaries go to `.eval-out/<label>/`, and each line reports time, word count, dominant script,
and numbers that do not appear in the source.

```bash
.venv/bin/python -m tests.eval.prompt_eval --label A \
  --locale en --locale ru path/to/video.en.srt https://youtu.be/VIDEO_ID
```
