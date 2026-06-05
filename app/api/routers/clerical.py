"""Clerical router — OWNER: Person B."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agents.clerical import api as clerical_api
from app.contracts import CommunicationDraft

router = APIRouter()


@router.post("/referral", response_model=CommunicationDraft)
def referral(payload: dict) -> CommunicationDraft:
    """Draft a referral letter. Body: {soap_id, receiving_specialist}"""
    soap_id = payload.get("soap_id", "")
    specialist = payload.get("receiving_specialist", "")
    if not specialist:
        raise HTTPException(status_code=422, detail="receiving_specialist is required")
    return clerical_api.draft_referral(soap_id=soap_id, receiving_specialist=specialist)


@router.post("/classify-reply")
def classify_reply(payload: dict) -> dict:
    """Classify a post-discharge patient reply. Body: {message, context}"""
    message = payload.get("message", "")
    context = payload.get("context", {})
    if not message:
        raise HTTPException(status_code=422, detail="message is required")
    classification = clerical_api.classify_inbound_reply(message=message, context=context)
    return {"classification": classification}


@router.post("/post-discharge-followup", response_model=CommunicationDraft)
def post_discharge_followup(payload: dict) -> CommunicationDraft:
    """Trigger a 72h post-discharge follow-up (called by beat sweep or manual override)."""
    from app.agents.clerical.mocks import fake_post_discharge_followup
    return fake_post_discharge_followup(patient_id=payload.get("patient_id", "p-001"))
