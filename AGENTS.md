# AGENTS.md

## Documentation

- Project documentation lives in `docs/`; follow `docs/AGENTS.md` when writing it.
- If a change affects behavior described by a project-scoped document, update that document in the same change.

## Code Style

- **Docstrings:** Use Google style docstrings for all public modules and classes.
- **Error Handling:** Raise domain-specific exceptions; never swallow errors silently.
- **Verification:** For Python changes, run `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, `.venv/bin/mypy .` (strict), and the smallest relevant `.venv/bin/python -m pytest` target.

## Architecture Rules

- **`__init__.py` is an Entry Point:** It MUST ONLY contain re-exports or package wiring. No business logic or utility functions allowed here.
- **No Catch-All Files:** Names like `utils.py`, `helpers.py`, or `services.py` are BANNED. Use domain-specific names (e.g., `yt_dlp_handler.py`, `date_formatter.py`).
