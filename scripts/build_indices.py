#!/usr/bin/env python
"""Build the Day-1 retrieval indices from the ICD-10-CM sample. OWNER: Person A.

Usage:
    python -m scripts.build_indices            # 200-row sample into both indices
    python -m scripts.build_indices --limit 500
    python -m scripts.build_indices --bm25-only

Reads `data/icd10/icd10cm_2026/icd10cm-codes-2026.txt` and writes the indices
under `data/indices/` (override with the CLINIQ_INDEX_DIR env var).
"""

from __future__ import annotations

import argparse

from app.retrieval import bm25_index, chroma_index
from app.retrieval.corpus import load_icd10_sample


def main() -> None:
    parser = argparse.ArgumentParser(description="Build CliniqAI retrieval indices")
    parser.add_argument("--limit", type=int, default=200, help="number of ICD-10 codes")
    parser.add_argument("--bm25-only", action="store_true", help="skip the Chroma index")
    parser.add_argument("--chroma-only", action="store_true", help="skip the BM25 index")
    args = parser.parse_args()

    docs = load_icd10_sample(limit=args.limit)
    print(f"Loaded {len(docs)} ICD-10-CM codes.")

    if not args.chroma_only:
        n = bm25_index.index_docs(docs)
        print(f"BM25 index built: {n} docs.")

    if not args.bm25_only:
        n = chroma_index.index_docs(docs)
        print(f"Chroma index built: {n} docs.")


if __name__ == "__main__":
    main()
