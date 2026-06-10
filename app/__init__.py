"""CliniqAI application package.

Importing `app` (which every entry point does — CLI, FastAPI, Gradio, Celery)
loads local env files so `os.getenv(...)` works without manually `source`-ing.

Precedence (highest first):
  1. variables already in the real environment (shell export, docker compose)
  2. .env.local   — your gitignored secrets
  3. .env         — optional shared defaults

Real environment always wins (`override=False`), so production / CI is never
clobbered by a stray file.
"""

from __future__ import annotations

from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover — dotenv is a declared dep, but be safe
    load_dotenv = None  # type: ignore[assignment]

if load_dotenv is not None:
    _ROOT = Path(__file__).resolve().parent.parent
    # Load .env.local before .env: with override=False the first file to set a
    # key wins, so .env.local takes precedence over .env.
    load_dotenv(_ROOT / ".env.local", override=False)
    load_dotenv(_ROOT / ".env", override=False)
