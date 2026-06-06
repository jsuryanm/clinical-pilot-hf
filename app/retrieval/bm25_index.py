"""BM25 keyword index. OWNER: Person A — Day 1.

Used for ICD-10 codes (74k+ entries) and drug formulary lookups where exact
keyword precision matters more than semantic similarity.

The index is a pickle of {ids, texts, metadatas, bm25} persisted under
`data/indices/bm25.pkl`. `rank_bm25` is imported lazily so this module imports
cleanly before `uv sync` has run (mirrors the litellm guard in llm/router.py).
"""

from __future__ import annotations

import pickle
import re
from typing import Any

from app.contracts import Hit
from app.retrieval.paths import bm25_path

_TOKEN_RE = re.compile(r"\w+")

# Process-level cache so repeated searches don't re-read the pickle.
_CACHE: dict[str, Any] | None = None


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _require_bm25():
    try:
        from rank_bm25 import BM25Okapi
    except ImportError as exc:  # pragma: no cover — depends on uv sync
        raise RuntimeError("rank-bm25 is not installed — run `make install`") from exc
    return BM25Okapi


def index_docs(docs: list[dict]) -> int:
    """Build and persist a BM25 index.

    Args:
        docs: list of {"id": str, "text": str, "metadata": dict[str, str]}
    Returns:
        Number of docs indexed.
    """
    global _CACHE
    BM25Okapi = _require_bm25()

    ids = [d["id"] for d in docs]
    texts = [d["text"] for d in docs]
    metadatas = [d.get("metadata", {}) for d in docs]
    tokenized = [_tokenize(t) for t in texts]

    bm25 = BM25Okapi(tokenized)
    payload = {"ids": ids, "texts": texts, "metadatas": metadatas, "bm25": bm25}

    with bm25_path().open("wb") as fh:
        pickle.dump(payload, fh)

    _CACHE = payload
    return len(ids)


def _load() -> dict[str, Any] | None:
    global _CACHE
    if _CACHE is not None:
        return _CACHE
    path = bm25_path()
    if not path.exists():
        return None
    with path.open("rb") as fh:
        _CACHE = pickle.load(fh)
    return _CACHE


def search(query: str, top_k: int = 5) -> list[Hit]:
    """Rank-bm25 over the indexed corpus. Empty list if the index is absent."""
    payload = _load()
    if payload is None:
        return []

    scores = payload["bm25"].get_scores(_tokenize(query))
    ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)

    hits: list[Hit] = []
    for i in ranked[:top_k]:
        if scores[i] <= 0:
            break  # no keyword overlap beyond this point
        hits.append(
            Hit(
                doc_id=payload["ids"][i],
                text=payload["texts"][i],
                score=float(scores[i]),
                source="bm25",
                metadata=payload["metadatas"][i],
            )
        )
    return hits


def _reset_cache() -> None:
    """Test hook — drop the in-process cache so a fresh pickle is re-read."""
    global _CACHE
    _CACHE = None
