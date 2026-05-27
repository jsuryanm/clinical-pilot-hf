"""ChromaDB vector index. OWNER: Person A — Day 1."""

from __future__ import annotations

from app.contracts import Hit


def search(query: str, top_k: int = 5) -> list[Hit]:
    """TODO(Person A): wire to a persistent Chroma collection."""
    raise NotImplementedError("Person A — Day 1")


def index_docs(docs: list[dict]) -> int:
    """TODO(Person A): bulk insert with embeddings.

    Args:
        docs: list of {"id": str, "text": str, "metadata": dict[str,str]}
    Returns:
        Number of docs indexed.
    """
    raise NotImplementedError("Person A — Day 1")
