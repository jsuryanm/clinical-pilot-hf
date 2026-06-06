"""Clerical Agent — happy path tests. OWNER: Person B."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.contracts import Channel


# ---------------------------------------------------------------------------
# classify_inbound_reply
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("reply,expected", [
    ("I'm feeling much better, thank you!", "reassuring"),
    ("Still have mild fever, should I be worried?", "needs_review"),
    ("Chest pain and difficulty breathing!", "needs_urgent_callback"),
])
def test_classify_reply_routing(reply: str, expected: str):
    from app.agents.clerical.api import classify_inbound_reply

    llm_response = f'{{"classification": "{expected}", "reason": "test"}}'
    mock_result = MagicMock()
    mock_result.text = llm_response

    with patch("app.agents.clerical.api.complete", return_value=mock_result):
        result = classify_inbound_reply(message=reply, context={"patient_id": "p-001"})

    assert result == expected


def test_classify_reply_falls_back_to_needs_review_on_llm_failure():
    """On any LLM error, classification must default to needs_review (safe escalation)."""
    from app.agents.clerical.api import classify_inbound_reply

    with patch("app.agents.clerical.api.complete", side_effect=RuntimeError("LLM down")):
        result = classify_inbound_reply(message="feeling okay", context={})

    assert result == "needs_review"


def test_classify_reply_invalid_llm_output_defaults_to_needs_review():
    from app.agents.clerical.api import classify_inbound_reply

    mock_result = MagicMock()
    mock_result.text = '{"classification": "unknown_value", "reason": "x"}'

    with patch("app.agents.clerical.api.complete", return_value=mock_result):
        result = classify_inbound_reply(message="hmm", context={})

    assert result == "needs_review"


# ---------------------------------------------------------------------------
# draft_referral
# ---------------------------------------------------------------------------

def test_draft_referral_returns_communication_draft():
    from app.agents.clerical.api import draft_referral

    mock_result = MagicMock()
    mock_result.text = "Dear Cardiology team,\n\nReferring patient...\n\nRegards, Dr. Sharma"

    with patch("app.agents.clerical.api.complete", return_value=mock_result):
        draft = draft_referral(soap_id="soap-001", receiving_specialist="Cardiology")

    assert draft.channel == Channel.EMAIL
    assert "cardiology" in draft.to.lower()
    assert draft.requires_approval is True
    assert "Cardiology" in draft.subject
    assert "Dr. Sharma" in draft.body


def test_draft_referral_requires_approval():
    from app.agents.clerical.api import draft_referral

    mock_result = MagicMock()
    mock_result.text = "Referral letter body"

    with patch("app.agents.clerical.api.complete", return_value=mock_result):
        draft = draft_referral(soap_id="soap-002", receiving_specialist="Neurology")

    assert draft.requires_approval is True, "Referral must always require doctor approval"
