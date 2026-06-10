"""Handover router - OWNER: Person C."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.handover.api import generate_handover
from app.contracts import HandoverBrief

router = APIRouter()


class GenerateHandoverRequest(BaseModel):
    ward_id: str = "ward-A"
    shift_end_ts: datetime | None = None


@router.post("/generate", response_model=HandoverBrief)
def generate(payload: GenerateHandoverRequest) -> HandoverBrief:
    """Generate the current ward handover brief."""
    return generate_handover(
        ward_id=payload.ward_id,
        shift_end_ts=payload.shift_end_ts or datetime.now(timezone.utc),
    )
