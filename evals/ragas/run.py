"""Run the Documentation Agent eval suite. OWNER: Person A — Day 5/9.

Modes:
    python -m evals.ragas.run                 # offline retrieval-grounding gate
    python -m evals.ragas.run --full          # also generate drafts + faithfulness
                                              # (needs an LLM key; uses RAGAS if installed)

Exit code is non-zero if the gate (context_precision / faithfulness >= 0.85)
fails, so this can run in CI.
"""

from __future__ import annotations

import argparse
import sys

from evals.ragas.scoring import (
    TARGET,
    keyword_faithfulness,
    load_golden,
    ragas_available,
    score_retrieval,
)


def _run_full(cases: list[dict]) -> float:
    """Generate a draft per case and return mean faithfulness."""
    from app.agents.documentation.api import draft_soap

    scores: list[float] = []
    for case in cases:
        try:
            draft = draft_soap(patient_id=case["patient_id"], transcript=case["transcript"])
        except Exception as exc:  # noqa: BLE001
            print(f"  ! {case['id']}: draft failed ({exc})")
            scores.append(0.0)
            continue
        f = keyword_faithfulness(draft, case)
        scores.append(f)
        print(f"  · {case['id']}: faithfulness≈{f:.2f}")
    return sum(scores) / (len(scores) or 1)


def main() -> int:
    parser = argparse.ArgumentParser(description="CliniqAI Documentation eval suite")
    parser.add_argument("--full", action="store_true", help="generate drafts + faithfulness")
    parser.add_argument("--target", type=float, default=TARGET)
    args = parser.parse_args()

    cases = load_golden()
    print(f"Loaded {len(cases)} golden cases.")

    retr = score_retrieval(cases)
    print(
        f"Retrieval grounding: context_precision={retr.context_precision:.2f} "
        f"icd_recall={retr.icd_recall:.2f} (n={retr.n})"
    )
    for c in retr.per_case:
        flag = "✓" if c["condition_ok"] else "✗"
        print(f"  {flag} {c['id']}: {c['retrieved_conditions']}")

    ok = retr.context_precision >= args.target

    if args.full:
        print(f"\nFull faithfulness pass (ragas {'available' if ragas_available() else 'NOT installed — heuristic'}):")
        faith = _run_full(cases)
        print(f"Mean faithfulness: {faith:.2f} (target {args.target})")
        ok = ok and faith >= args.target

    print(f"\nGATE: {'PASS' if ok else 'FAIL'} (target {args.target})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
