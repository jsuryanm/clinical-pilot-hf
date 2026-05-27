"""Smoke tests for the shared contracts. If these break, the whole team is blocked."""

from __future__ import annotations

import pytest

from app.agents.appointment.mocks import fake_booking, fake_communication
from app.agents.clerical.mocks import fake_post_discharge_followup, fake_referral_letter
from app.agents.discharge.mocks import fake_discharge
from app.agents.documentation.mocks import fake_soap_draft
from app.agents.handover.mocks import fake_handover
from app.agents.roster.mocks import fake_roster
from app.contracts import (
    BookingResult,
    CommunicationDraft,
    DischargeCoordination,
    HandoverBrief,
    Priority,
    RosterResult,
    SOAPNoteDraft,
)


def test_soap_mock_validates() -> None:
    d = fake_soap_draft()
    assert isinstance(d, SOAPNoteDraft)
    assert d.soap.subjective
    assert d.icd10_suggestions
    assert all(0.0 <= s.confidence <= 1.0 for s in d.icd10_suggestions)
    assert d.sources, "every SOAP draft must cite at least one source"


def test_booking_mock_validates() -> None:
    b = fake_booking()
    assert isinstance(b, BookingResult)
    assert b.reminder_jobs, "booking should schedule at least one reminder"


def test_communication_mock_validates() -> None:
    c = fake_communication()
    assert isinstance(c, CommunicationDraft)
    assert c.body


def test_discharge_mock_has_five_subtasks() -> None:
    d = fake_discharge()
    assert isinstance(d, DischargeCoordination)
    assert len(d.subtasks) == 5
    names = {s.name for s in d.subtasks}
    assert names == {
        "discharge_summary", "pharmacy", "family_notification",
        "follow_up_appointment", "billing_trigger",
    }


def test_roster_mock_validates() -> None:
    r = fake_roster()
    assert isinstance(r, RosterResult)
    assert 0 <= r.fairness_score <= 1
    assert r.assignments


def test_handover_mock_ordered_by_priority() -> None:
    h = fake_handover()
    assert isinstance(h, HandoverBrief)
    rank = {Priority.URGENT: 0, Priority.WATCH: 1, Priority.STABLE: 2}
    ranks = [rank[p.priority] for p in h.patients]
    assert ranks == sorted(ranks), "handover must surface urgent patients first"


def test_clerical_mocks_validate() -> None:
    assert isinstance(fake_referral_letter(), CommunicationDraft)
    assert isinstance(fake_post_discharge_followup(), CommunicationDraft)


def test_contracts_forbid_extra_fields() -> None:
    with pytest.raises(Exception):
        # extra field should be rejected
        SOAPNoteDraft(
            draft_id="x", patient_id="p", encounter_ts=fake_soap_draft().encounter_ts,
            soap=fake_soap_draft().soap, model="x", extra_field="nope",  # type: ignore[call-arg]
        )
