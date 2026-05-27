"""Orchestrator routing — keyword fallback is deterministic and testable
even when no LLM keys are configured."""

from __future__ import annotations

import pytest

from app.contracts import TaskType
from app.orchestrator import _route_with_keywords


@pytest.mark.parametrize(
    "utterance,expected",
    [
        ("please book me an appointment tomorrow at 3pm", TaskType.APPOINTMENT),
        ("can you reschedule my slot?", TaskType.APPOINTMENT),
        ("patient is ready for discharge", TaskType.DISCHARGE),
        ("sick call — Dr. Verma is out today", TaskType.ROSTER),
        ("generate the shift change handover brief", TaskType.HANDOVER),
        ("draft a referral letter to cardiology", TaskType.CLERICAL),
        ("update the hypertension guideline page", TaskType.WIKI_MAINT),
        ("write a SOAP note for today's patient", TaskType.DOCUMENTATION),
    ],
)
def test_keyword_routing(utterance: str, expected: TaskType) -> None:
    decision = _route_with_keywords(utterance)
    assert decision.task == expected
