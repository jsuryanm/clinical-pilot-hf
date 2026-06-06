"""Unified retrieval API. OWNER: Person A.

Hides Chroma + BM25 behind one function so callers don't care which index
returned a hit. Hybrid mode reciprocally rank-fuses the two result lists.
"""

from __future__ import annotations

from typing import Literal

from app.contracts import Hit
from app.retrieval import bm25_index, chroma_index

_RRF_K = 60  # standard reciprocal-rank-fusion constant


def reciprocal_rank_fusion(
    rank_lists: list[list[Hit]], *, top_k: int, k: int = _RRF_K
) -> list[Hit]:
    """Fuse several ranked Hit lists into one.

    Each document's fused score is the sum of 1/(k + rank) across the lists it
    appears in (rank is 0-based within its list). The returned Hit keeps the
    first representative seen and is tagged source="hybrid".
    """
    fused: dict[str, float] = {}
    rep: dict[str, Hit] = {}

    for hits in rank_lists:
        for rank, hit in enumerate(hits):
            fused[hit.doc_id] = fused.get(hit.doc_id, 0.0) + 1.0 / (k + rank)
            rep.setdefault(hit.doc_id, hit)

    ordered = sorted(fused.items(), key=lambda kv: kv[1], reverse=True)
    out: list[Hit] = []
    for doc_id, score in ordered[:top_k]:
        h = rep[doc_id]
        out.append(
            Hit(
                doc_id=h.doc_id,
                text=h.text,
                score=score,
                source="hybrid",
                metadata=h.metadata,
            )
        )
    return out


def search(
    query: str, top_k: int = 5, mode: Literal["vector", "bm25", "hybrid"] = "hybrid"
) -> list[Hit]:
    """Retrieve the top_k hits for `query` using the requested index strategy."""
    if mode == "vector":
        return chroma_index.search(query, top_k)
    if mode == "bm25":
        return bm25_index.search(query, top_k)

    # hybrid — pull a wider candidate set from each index before fusing.
    candidates = max(top_k * 2, top_k)
    vector_hits = chroma_index.search(query, candidates)
    keyword_hits = bm25_index.search(query, candidates)
    return reciprocal_rank_fusion([vector_hits, keyword_hits], top_k=top_k)
