"""Eval-suite tests. OWNER: Person A — Day 5/9.

Validates the golden dataset and runs the offline retrieval-grounding gate
(no LLM / network needed). The full RAGAS faithfulness pass is exercised by
`python -m evals.ragas.run --full` with an LLM key.
"""

from __future__ import annotations

from evals.ragas.scoring import TARGET, load_golden, score_retrieval


def test_golden_cases_load_and_validate() -> None:
    cases = load_golden()
    assert len(cases) >= 10
    ids = [c["id"] for c in cases]
    assert len(ids) == len(set(ids)), "duplicate golden case ids"


def test_retrieval_grounding_meets_gate() -> None:
    cases = load_golden()
    score = score_retrieval(cases)
    # every golden transcript should surface its expected guideline page
    assert score.context_precision >= TARGET, score.per_case
