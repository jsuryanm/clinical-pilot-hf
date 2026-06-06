"""ChromaDB vector index. OWNER: Person A — Day 1.

A persistent Chroma collection over the same corpus BM25 indexes, used for
semantic recall. `chromadb` is imported lazily so this module imports cleanly
before `uv sync` (mirrors the litellm guard in llm/router.py).

Distances are converted to a bounded similarity score via `1 / (1 + distance)`,
which is monotonic regardless of the underlying metric.
"""

from __future__ import annotations

from typing import Any

from app.contracts import Hit
from app.retrieval.paths import chroma_path

_COLLECTION = "cliniq_corpus"
_client: Any = None
_collection: Any = None


def _get_collection() -> Any:
    global _client, _collection
    if _collection is not None:
        return _collection
    try:
        import chromadb
    except ImportError as exc:  # pragma: no cover — depends on uv sync
        raise RuntimeError("chromadb is not installed — run `make install`") from exc

    _client = chromadb.PersistentClient(path=str(chroma_path()))
    _collection = _client.get_or_create_collection(
        name=_COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )
    return _collection


def index_docs(docs: list[dict]) -> int:
    """Upsert documents with embeddings.

    Args:
        docs: list of {"id": str, "text": str, "metadata": dict[str, str]}
    Returns:
        Number of docs indexed.
    """
    if not docs:
        return 0
    coll = _get_collection()

    ids = [d["id"] for d in docs]
    documents = [d["text"] for d in docs]
    metadatas = [d.get("metadata") or None for d in docs]
    # Chroma rejects empty dicts; pass metadatas only if every doc carries one.
    kwargs: dict[str, Any] = {"ids": ids, "documents": documents}
    if all(m for m in metadatas):
        kwargs["metadatas"] = metadatas

    coll.upsert(**kwargs)
    return len(ids)


def search(query: str, top_k: int = 5) -> list[Hit]:
    """Semantic nearest-neighbour search. Empty list if the collection is empty."""
    coll = _get_collection()
    if coll.count() == 0:
        return []

    res = coll.query(query_texts=[query], n_results=top_k)
    ids = res["ids"][0]
    documents = res["documents"][0]
    distances = res["distances"][0]
    metadatas = (res.get("metadatas") or [[]])[0] or [None] * len(ids)

    hits: list[Hit] = []
    for doc_id, text, dist, meta in zip(ids, documents, distances, metadatas, strict=False):
        hits.append(
            Hit(
                doc_id=doc_id,
                text=text,
                score=1.0 / (1.0 + float(dist)),
                source="chroma",
                metadata={str(k): str(v) for k, v in (meta or {}).items()},
            )
        )
    return hits


def _reset() -> None:
    """Test hook — drop the cached client/collection handle."""
    global _client, _collection
    _client = None
    _collection = None
