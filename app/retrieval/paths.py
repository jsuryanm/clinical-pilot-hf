"""Shared on-disk locations for the retrieval indices. OWNER: Person A.

Both indices live under `data/indices/` (the whole `data/` tree is gitignored
and distributed via the shared bucket). Override the root with the
`CLINIQ_INDEX_DIR` env var — handy for tests, which point it at a tmp dir.
"""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_ROOT = Path(__file__).resolve().parents[2] / "data" / "indices"


def index_root() -> Path:
    root = Path(os.getenv("CLINIQ_INDEX_DIR", str(_DEFAULT_ROOT)))
    root.mkdir(parents=True, exist_ok=True)
    return root


def bm25_path() -> Path:
    return index_root() / "bm25.pkl"


def chroma_path() -> Path:
    p = index_root() / "chroma"
    p.mkdir(parents=True, exist_ok=True)
    return p
