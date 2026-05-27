"""Unified retrieval API. OWNER: Person A.

Hides Chroma + BM25 behind one function so callers don't care which index
returned a hit. Returns a list of validated `Hit` objects.
"""

from __future__ import annotations

from typing import Literal

from app.contracts import Hit


def search(query: str, top_k: int = 5, mode: Literal["vector", "bm25", "hybrid"] = "hybrid") -> list[Hit]:
    """Hybrid retrieval — runs both indices and reciprocally rank-fuses.

    TODO(Person A — Day 1):
      - vector mode  -> app.retrieval.chroma_index.search(query, top_k)
      - bm25 mode    -> app.retrieval.bm25_index.search(query, top_k)
      - hybrid mode  -> RRF over both
    """
    raise NotImplementedError("Person A — Day 1")
