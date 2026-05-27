"""Clerical router — OWNER: Person B."""

from __future__ import annotations

from fastapi import APIRouter

from app.agents.clerical.mocks import fake_post_discharge_followup, fake_referral_letter
from app.contracts import CommunicationDraft

router = APIRouter()


@router.post("/referral", response_model=CommunicationDraft)
def referral(payload: dict) -> CommunicationDraft:
    """TODO(Person B): replace with `app.agents.clerical.api.draft_referral(...)`."""
    return fake_referral_letter(patient_id=payload.get("patient_id", "p-001"))


@router.post("/post-discharge-followup", response_model=CommunicationDraft)
def post_discharge_followup(payload: dict) -> CommunicationDraft:
    """TODO(Person B): wire to Celery beat at discharge_time + 72h."""
    return fake_post_discharge_followup(patient_id=payload.get("patient_id", "p-001"))
