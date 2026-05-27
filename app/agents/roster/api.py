"""Rostering Agent — public API. OWNER: Person C."""

from __future__ import annotations

from pathlib import Path

from app.contracts import RosterResult


def generate_roster(staff_csv: Path, window_days: int = 14) -> RosterResult:
    """Greedy first, OR-tools later."""
    raise NotImplementedError("Person C — Day 3")


def find_sick_call_replacement(shift_id: str, sick_staff_id: str) -> RosterResult:
    raise NotImplementedError("Person C — Day 9")
