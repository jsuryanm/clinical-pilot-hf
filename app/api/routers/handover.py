"""Handover router — OWNER: Person C."""

from __future__ import annotations

from fastapi import APIRouter

from app.agents.handover.mocks import fake_handover
from app.contracts import HandoverBrief

router = APIRouter()


@router.post("/generate", response_model=HandoverBrief)
def generate(payload: dict) -> HandoverBrief:
    """TODO(Person C): wire to `app.agents.handover.api.generate_handover(...)`."""
    return fake_handover(ward_id=payload.get("ward_id", "ward-A"))
