"""Roster router — OWNER: Person C."""

from __future__ import annotations

from fastapi import APIRouter

from app.agents.roster.mocks import fake_roster
from app.contracts import RosterResult

router = APIRouter()


@router.post("/generate", response_model=RosterResult)
def generate(payload: dict) -> RosterResult:
    """TODO(Person C): wire to `app.agents.roster.api.generate_roster(...)`."""
    return fake_roster()


@router.post("/sick-call", response_model=RosterResult)
def sick_call(payload: dict) -> RosterResult:
    """TODO(Person C): wire to `find_sick_call_replacement(...)`."""
    return fake_roster()
