"""Documentation Agent tests. OWNER: Person A — Day 3/4.

The LLM is mocked (no network / key needed). The patient-wiki write is pointed
at a tmp dir via CLINIQ_WIKI_DIR so tests never touch the real repo.
"""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from app.agents.documentation import api
from app.agents.wiki import api as wiki_api
from app.llm.router import CompletionResult

_TRANSCRIPT = (
    "Doctor: how is the blood pressure at home? "
    "Patient: I stopped the amlodipine tablet last week, having headaches and dizziness. "
    "Doctor: your BP today is 162 over 98."
)

_MODEL_JSON = {
    "soap": {
        "subjective": "52M, hypertensive, stopped amlodipine, 2-day headache and dizziness.",
        "objective": "BP 162/98, HR 84, afebrile.",
        "assessment": "Uncontrolled essential hypertension, likely non-adherence.",
        "plan": "Restart and uptitrate amlodipine; home BP log; review in 2 weeks.",
    },
    "icd10_suggestions": [{"code": "I10", "label": "Essential hypertension", "confidence": 0.92}],
    "guideline_suggestions": ["Combination therapy preferred in stage-2 HTN."],
    "referral_needed": False,
    "confidence_overall": 0.83,
}


def _fake_completion(text: str) -> CompletionResult:
    return CompletionResult(
        text=text,
        model="groq/qwen/qwen3-32b",
        latency_ms=900.0,
        prompt_tokens=400,
        completion_tokens=180,
    )


@pytest.fixture()
def mock_llm():
    """Patch the router so draft_soap returns our canned JSON."""
    with patch.object(api, "complete") as m:
        m.return_value = _fake_completion(json.dumps(_MODEL_JSON))
        yield m


@pytest.fixture(autouse=True)
def _tmp_wiki(tmp_path, monkeypatch):
    monkeypatch.setenv("CLINIQ_WIKI_DIR", str(tmp_path / "wiki"))
    monkeypatch.setenv("CLINIQ_WIKI_HISTORY_DIR", str(tmp_path / "history"))


# --- draft_soap ---------------------------------------------------------------


def test_draft_soap_assembles_validated_draft(mock_llm) -> None:
    draft = api.draft_soap(patient_id="p-001", transcript=_TRANSCRIPT)

    assert draft.patient_id == "p-001"
    assert draft.draft_id.startswith("soap-")
    assert "hypertension" in draft.soap.assessment.lower()
    assert draft.model == "groq/qwen/qwen3-32b"
    assert draft.confidence_overall == pytest.approx(0.83)
    assert draft.icd10_suggestions[0].code == "I10"


def test_draft_soap_guarantees_guideline_citation(mock_llm) -> None:
    """The hypertension consult must cite the hypertension wiki page (audit contract)."""
    draft = api.draft_soap(patient_id="p-001", transcript=_TRANSCRIPT)
    cited = {c.source_id for c in draft.sources}
    assert "conditions/hypertension" in cited
    assert all(c.source_type == "wiki" for c in draft.sources)


def test_draft_soap_requires_input() -> None:
    with pytest.raises(ValueError):
        api.draft_soap(patient_id="p-001")


def test_draft_soap_tolerates_fenced_json(monkeypatch) -> None:
    fenced = "```json\n" + json.dumps(_MODEL_JSON) + "\n```"
    with patch.object(api, "complete", return_value=_fake_completion(fenced)):
        draft = api.draft_soap(patient_id="p-001", transcript=_TRANSCRIPT)
    assert draft.soap.plan.startswith("Restart")


# --- approve_draft + wiki persistence ----------------------------------------


def test_approve_writes_patient_page_with_edits(mock_llm) -> None:
    draft = api.draft_soap(patient_id="p-007", transcript=_TRANSCRIPT)
    ref = api.approve_draft(draft, edits={"plan": "EDITED: amlodipine 10 mg, review day 7."})

    assert ref.patient_id == "p-007"
    assert ref.version  # content hash present

    page = wiki_api.get_patient_page("p-007")
    assert page is not None
    assert "## Encounter History" in page
    assert "EDITED: amlodipine 10 mg" in page
    assert draft.draft_id in page


def test_get_patient_page_absent_returns_none() -> None:
    assert wiki_api.get_patient_page("does-not-exist") is None
