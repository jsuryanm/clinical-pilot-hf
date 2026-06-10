"""Retrieval-layer smoke tests. OWNER: Person A — Day 1.

The RRF fusion and corpus-loader tests run with no extra deps. The BM25 and
Chroma round-trip tests `importorskip` their backend so the suite stays green
before `uv sync` has installed rank-bm25 / chromadb.
"""

from __future__ import annotations

import pytest

from app.contracts import Hit
from app.retrieval import bm25_index, chroma_index, index_api
from app.retrieval.corpus import dot_code, load_icd10_sample

SAMPLE_DOCS = [
    {"id": "I10", "text": "I10 Essential (primary) hypertension", "metadata": {"category": "I10"}},
    {"id": "E11.9", "text": "E11.9 Type 2 diabetes mellitus without complications", "metadata": {"category": "E11"}},
    {"id": "J18.9", "text": "J18.9 Pneumonia, unspecified organism", "metadata": {"category": "J18"}},
    {"id": "J45.901", "text": "J45.901 Unspecified asthma with acute exacerbation", "metadata": {"category": "J45"}},
    {"id": "A09", "text": "A09 Infectious gastroenteritis and colitis, unspecified", "metadata": {"category": "A09"}},
]


# --- pure-python, no backend needed -------------------------------------------


def test_rrf_fuses_and_dedupes() -> None:
    list_a = [
        Hit(doc_id="x", text="x", score=9.0, source="chroma"),
        Hit(doc_id="y", text="y", score=8.0, source="chroma"),
    ]
    list_b = [
        Hit(doc_id="y", text="y", score=2.0, source="bm25"),
        Hit(doc_id="z", text="z", score=1.0, source="bm25"),
    ]

    fused = index_api.reciprocal_rank_fusion([list_a, list_b], top_k=10)

    ids = [h.doc_id for h in fused]
    assert ids == ["y", "x", "z"]  # y appears in both lists -> ranks first
    assert all(h.source == "hybrid" for h in fused)
    assert len(ids) == len(set(ids))  # deduped


def test_rrf_respects_top_k() -> None:
    lists = [[Hit(doc_id=str(i), text=str(i), score=1.0, source="bm25") for i in range(10)]]
    assert len(index_api.reciprocal_rank_fusion(lists, top_k=3)) == 3


def test_dot_code() -> None:
    assert dot_code("A000") == "A00.0"
    assert dot_code("I10") == "I10"
    assert dot_code("J45901") == "J45.901"


def test_load_icd10_sample() -> None:
    docs = load_icd10_sample(limit=50)
    assert len(docs) == 50
    first = docs[0]
    assert set(first) == {"id", "text", "metadata"}
    assert first["text"].startswith(first["id"])
    assert first["metadata"]["source"] == "icd10cm_2026"


# --- backend round-trips (skipped if the lib isn't installed) -----------------


def test_bm25_roundtrip(tmp_path, monkeypatch) -> None:
    pytest.importorskip("rank_bm25")
    monkeypatch.setenv("CLINIQ_INDEX_DIR", str(tmp_path))
    bm25_index._reset_cache()

    n = bm25_index.index_docs(SAMPLE_DOCS)
    assert n == len(SAMPLE_DOCS)

    hits = bm25_index.search("diabetes mellitus", top_k=3)
    assert hits, "expected at least one keyword hit"
    assert hits[0].doc_id == "E11.9"
    assert hits[0].source == "bm25"


def test_chroma_roundtrip(tmp_path, monkeypatch) -> None:
    pytest.importorskip("chromadb")
    monkeypatch.setenv("CLINIQ_INDEX_DIR", str(tmp_path))
    chroma_index._reset()

    n = chroma_index.index_docs(SAMPLE_DOCS)
    assert n == len(SAMPLE_DOCS)

    hits = chroma_index.search("high blood pressure", top_k=3)
    assert hits, "expected at least one semantic hit"
    assert all(0.0 < h.score <= 1.0 for h in hits)
    assert hits[0].source == "chroma"


def test_hybrid_search(tmp_path, monkeypatch) -> None:
    pytest.importorskip("rank_bm25")
    pytest.importorskip("chromadb")
    monkeypatch.setenv("CLINIQ_INDEX_DIR", str(tmp_path))
    bm25_index._reset_cache()
    chroma_index._reset()

    bm25_index.index_docs(SAMPLE_DOCS)
    chroma_index.index_docs(SAMPLE_DOCS)

    hits = index_api.search("asthma exacerbation", top_k=3, mode="hybrid")
    assert hits
    assert hits[0].source == "hybrid"
    assert any(h.doc_id == "J45.901" for h in hits)
