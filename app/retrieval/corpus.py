"""Corpus loaders for the retrieval indices. OWNER: Person A — Day 1.

The Day-1 sample is a slice of the CDC ICD-10-CM FY2026 code list
(`data/icd10/icd10cm_2026/icd10cm-codes-2026.txt`). Lines are
`<dotless-code><whitespace><description>`, e.g. `A000  Cholera due to ...`.
Codes are stored dotted for display (`A000` -> `A00.0`).
"""

from __future__ import annotations

from pathlib import Path

_ICD10CM_FILE = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "icd10"
    / "icd10cm_2026"
    / "icd10cm-codes-2026.txt"
)


def dot_code(dotless: str) -> str:
    """ICD-10-CM stores codes dotless; insert the conventional dot after 3 chars."""
    return f"{dotless[:3]}.{dotless[3:]}" if len(dotless) > 3 else dotless


def load_icd10_sample(limit: int = 200, path: Path | None = None) -> list[dict]:
    """Return up to `limit` ICD-10-CM codes as index docs.

    Each doc: {"id": <dotted code>, "text": "<code> <description>",
               "metadata": {"code", "category", "source"}}.
    """
    src = path or _ICD10CM_FILE
    docs: list[dict] = []
    with src.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            parts = line.split(maxsplit=1)
            if len(parts) != 2:
                continue
            dotless, description = parts
            code = dot_code(dotless)
            docs.append(
                {
                    "id": code,
                    "text": f"{code} {description}",
                    "metadata": {
                        "code": code,
                        "category": dotless[:3],
                        "source": "icd10cm_2026",
                    },
                }
            )
            if len(docs) >= limit:
                break
    return docs
