"""
Run the real summarization pipeline on fixed samples to compare prompt variants.

Needs a reachable LLM configured in ``.env``, so it is a developer tool, not part of the test suite.
Each SOURCE is a subtitle file (.srt/.vtt; title taken from the file name) or a video URL
(loaded through the bot's own loader).

Usage:
    .venv/bin/python -m tests.eval.prompt_eval --label A --locale en --locale ru SOURCE [SOURCE ...]

For each sample and locale it writes the summary to ``<out>/<label>/`` and prints elapsed time,
word count, dominant script, and numbers in the summary that do not appear anywhere in the source.
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
import re
import time
import unicodedata
from collections import Counter
from pathlib import Path

from src.config import Settings
from src.load.content_document import ContentDocument
from src.load.transcripts import clean_srt
from src.load.video_loader import VideoDataLoader
from src.transform.summarization import OpenAISummarizer

# Digits with optional thousands groups ("12 262", "1,200") and an optional decimal part ("1.2", "1,5").
_NUMBER_RE = re.compile(r"\d+(?:[\s,]\d{3}(?!\d))*(?:[.,]\d+)?")
_NUMBER_SEPARATORS_RE = re.compile(r"[\s,]")
_FILE_DATE_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2} - ")
_FILE_LANGUAGE_SUFFIX_RE = re.compile(r"\.[a-z]{2}(?:[-_][A-Za-z]+)?$")


def find_unsupported_numbers(summary: str, source: str) -> list[str]:
    """
    Return numbers from the summary that do not occur in the source.

    Whole numbers are compared after normalization, so "12 262" matches "12262", "1,2" matches "1.2",
    and "5" does not match "250". This is a heuristic: a number written as words in the source is
    reported as unsupported.
    """
    source_numbers: set[str] = set()
    for match in _NUMBER_RE.findall(source):
        source_numbers.add(_canonical_number(match))
        # "in 2021 300 people" parses as one grouped number; keep the parts too.
        source_numbers.update(_canonical_number(part) for part in re.findall(r"\d+(?:[.,]\d+)?", match))
    found: list[str] = []
    for match in _NUMBER_RE.findall(summary):
        if _canonical_number(match) not in source_numbers and match not in found:
            found.append(match)
    return found


def dominant_script(text: str) -> str:
    """Return the Unicode script name (LATIN, CYRILLIC, CJK, ...) of most letters, to spot language drift."""
    scripts = Counter(unicodedata.name(char, "UNKNOWN").split()[0] for char in text if char.isalpha())
    return scripts.most_common(1)[0][0] if scripts else "NONE"


def _canonical_number(text: str) -> str:
    """Drop thousands separators and turn a decimal comma into a dot."""
    text = re.sub(r"\s", "", text)
    if re.search(r",\d{3}(?!\d)", text):
        return text.replace(",", "")
    return text.replace(",", ".")


def _load_subtitle_file(path: Path) -> ContentDocument:
    title = _FILE_LANGUAGE_SUFFIX_RE.sub("", _FILE_DATE_PREFIX_RE.sub("", path.stem))
    return ContentDocument(
        id=path.stem,
        source_type="video",
        url=str(path),
        title=title,
        language="",
        content=clean_srt(path.read_text(encoding="utf-8", errors="replace")),
    )


async def _load_document(source: str, settings: Settings) -> ContentDocument:
    path = Path(source).expanduser()
    if path.is_file():
        return _load_subtitle_file(path)
    return await VideoDataLoader(settings).load(source)


def _sample_name(document: ContentDocument) -> str:
    return re.sub(r"[^\w-]+", "_", document.title)[:60].strip("_") or document.id


async def _run(args: argparse.Namespace) -> None:
    settings = dataclasses.replace(Settings.from_env(), valkey_url=None)
    out_dir = Path(args.out) / args.label
    out_dir.mkdir(parents=True, exist_ok=True)
    summarizer = OpenAISummarizer(settings)
    print(f"{args.label}: model={settings.openai_model}")

    for source in args.sources:
        try:
            document = await _load_document(source, settings)
        except (RuntimeError, OSError, ValueError) as exc:
            print(f"  {source}: FAILED to load: {exc}")
            continue
        source_text = f"{document.title}\n{document.content}"
        for locale in args.locales:
            name = f"{_sample_name(document)}.{locale}.md"
            start = time.monotonic()
            try:
                summary = await summarizer.summarize(document, locale)
            except RuntimeError as exc:
                print(f"  {name}: FAILED: {exc}")
                continue
            elapsed = time.monotonic() - start
            (out_dir / name).write_text(summary, encoding="utf-8")
            unsupported = find_unsupported_numbers(summary, source_text)
            stats = f"{elapsed:.0f}s script={dominant_script(summary)} words={len(summary.split())}"
            print(f"  {name}: {stats} unsupported_numbers={len(unsupported)} {unsupported}")


def main() -> None:
    """Parse arguments and run the evaluation."""
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("sources", nargs="+", metavar="SOURCE", help="subtitle file path or video URL")
    parser.add_argument("--label", required=True, help="variant name, used as the output subdirectory")
    parser.add_argument("--locale", dest="locales", action="append", default=None, help="summary locale (repeatable, default: en)")
    parser.add_argument("--out", default=".eval-out", help="output root directory (default: .eval-out)")
    args = parser.parse_args()
    args.locales = args.locales or ["en"]
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
