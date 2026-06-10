"""Standalone Documentation Agent CLI. OWNER: Person A.

Run the agent without the orchestrator or UI::

    python -m app.agents.documentation.cli --patient p-001 --transcript "Doctor: ..."
    python -m app.agents.documentation.cli --patient p-001 --audio consult.wav
    python -m app.agents.documentation.cli --patient p-001 --transcript "..." --approve

Without an LLM key set the draft step will error from the router — use
``app.agents.documentation.mocks.fake_soap_draft`` for offline UI work.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.agents.documentation.api import approve_draft, draft_soap


def _main() -> None:
    parser = argparse.ArgumentParser(description="Draft a SOAP note from a consult")
    parser.add_argument("--patient", required=True, help="patient id, e.g. p-001")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--transcript", help="consult transcript text")
    src.add_argument("--audio", type=Path, help="path to a consult audio file")
    parser.add_argument(
        "--approve",
        action="store_true",
        help="persist the draft to the patient wiki page after drafting",
    )
    args = parser.parse_args()

    draft = draft_soap(
        patient_id=args.patient,
        transcript=args.transcript,
        audio_path=args.audio,
    )

    print(draft.model_dump_json(indent=2))

    if args.approve:
        ref = approve_draft(draft)
        print(f"\nApproved -> {ref.page_path} @ {ref.version}", file=sys.stderr)


if __name__ == "__main__":
    _main()
