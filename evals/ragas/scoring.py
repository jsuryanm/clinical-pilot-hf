"""Scoring for the Documentation Agent eval suite. OWNER: Person A — Day 5/9.

Two scorers:

- **Retrieval grounding** (offline, no LLM/keys): did the agent retrieve the
  guideline page the golden case expects, and surface the expected ICD-10 code?
  This is a deterministic ``context_precision`` proxy we can gate in CI without
  network access.
- **RAGAS** (optional): real faithfulness / answer_relevancy / context_precision
  via the ``ragas`` package when it is installed and an LLM key is configured.
  Falls back to a keyword-grounding heuristic otherwise.

A "golden case" is a dict loaded from ``evals/ragas/golden/*.json`` with keys:
``id, patient_id, transcript, expected_conditions, expected_icd10,
expected_assessment_keywords, expected_plan_keywords``.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

GOLDEN_DIR = Path(__file__).resolve().parent / "golden"
TARGET = 0.85  # faithfulness gate from the plan

_REQUIRED_KEYS = {
    "id",
    "patient_id",
    "transcript",
    "expected_conditions",
    "expected_icd10",
    "expected_assessment_keywords",
    "expected_plan_keywords",
}


def load_golden(golden_dir: Path = GOLDEN_DIR) -> list[dict]:
    """Load and validate all golden case files."""
    cases: list[dict] = []
    for path in sorted(golden_dir.glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        missing = _REQUIRED_KEYS - case.keys()
        if missing:
            raise ValueError(f"{path.name} missing keys: {sorted(missing)}")
        cases.append(case)
    return cases


@dataclass
class RetrievalScore:
    n: int
    context_precision: float  # expected condition retrieved
    icd_recall: float  # expected ICD-10 code surfaced by the index
    per_case: list[dict]

    def passed(self, target: float = TARGET) -> bool:
        return self.context_precision >= target


def score_retrieval(cases: list[dict], top_guidelines: int = 2, top_icd: int = 8) -> RetrievalScore:
    """Offline grounding score — runs the real retrieval, no LLM needed."""
    from app.agents.documentation.retrieval import retrieve_guidelines
    from app.retrieval import index_api

    per_case: list[dict] = []
    hits_cond = 0
    hits_icd = 0
    for case in cases:
        guides = retrieve_guidelines(case["transcript"], top_k=top_guidelines)
        got_conditions = {g.page_id for g in guides}
        cond_ok = any(c in got_conditions for c in case["expected_conditions"])

        try:
            icd_hits = index_api.search(case["transcript"], top_k=top_icd, mode="bm25")
        except Exception:
            icd_hits = []
        got_codes = {h.doc_id for h in icd_hits}
        icd_ok = any(code in got_codes for code in case["expected_icd10"])

        hits_cond += cond_ok
        hits_icd += icd_ok
        per_case.append(
            {"id": case["id"], "condition_ok": cond_ok, "icd_ok": icd_ok,
             "retrieved_conditions": sorted(got_conditions)}
        )

    n = len(cases) or 1
    return RetrievalScore(
        n=len(cases),
        context_precision=hits_cond / n,
        icd_recall=hits_icd / n,
        per_case=per_case,
    )


def keyword_faithfulness(draft, case: dict) -> float:
    """Heuristic faithfulness proxy: fraction of expected keywords grounded in the
    draft's assessment + plan. Used when RAGAS is unavailable."""
    text = f"{draft.soap.assessment} {draft.soap.plan}".lower()
    expected = [k.lower() for k in case["expected_assessment_keywords"] + case["expected_plan_keywords"]]
    if not expected:
        return 1.0
    return sum(k in text for k in expected) / len(expected)


def ragas_available() -> bool:
    try:
        import ragas  # noqa: F401
    except ImportError:
        return False
    return True
