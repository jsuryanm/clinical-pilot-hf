"""Roster router - OWNER: Person C."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from app.agents.roster.api import find_sick_call_replacement, generate_roster, load_staff
from app.agents.roster.mocks import fake_roster
from app.contracts import RosterResult

router = APIRouter()


class GenerateRosterRequest(BaseModel):
    staff_csv: str | None = None
    window_days: int = 14


class SickCallRequest(BaseModel):
    shift_id: str | None = None
    sick_staff_id: str | None = None
    staff_csv: str | None = None
    window_days: int = 14


@router.post("/generate", response_model=RosterResult)
def generate(payload: GenerateRosterRequest) -> RosterResult:
    """Generate a roster from CSV, or return demo data when no CSV is supplied."""
    if payload.staff_csv:
        return generate_roster(Path(payload.staff_csv), window_days=payload.window_days)
    return fake_roster()


@router.post("/sick-call", response_model=RosterResult)
def sick_call(payload: SickCallRequest) -> RosterResult:
    """Replace a sick staff member when enough roster context is supplied."""
    if payload.staff_csv and payload.shift_id and payload.sick_staff_id:
        csv_path = Path(payload.staff_csv)
        staff = load_staff(csv_path)
        roster = generate_roster(csv_path, window_days=payload.window_days)
        return find_sick_call_replacement(
            payload.shift_id,
            payload.sick_staff_id,
            staff=staff,
            roster=roster,
        )
    return fake_roster()
