"""BM25 keyword index. OWNER: Person A — Day 1.

Used for ICD-10 codes (95k+ entries) and drug formulary lookups where exact
keyword precision matters more than semantic similarity.
"""

from __future__ import annotations

from app.contracts import Hit


def search(query: str, top_k: int = 5) -> list[Hit]:
    """TODO(Person A): rank-bm25 over the ICD-10 + drug corpora."""
    raise NotImplementedError("Person A — Day 1")


def index_docs(docs: list[dict]) -> int:
    raise NotImplementedError("Person A — Day 1")
