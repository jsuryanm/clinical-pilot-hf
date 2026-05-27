"""Discharge Agent — public API. OWNER: Person B."""

from __future__ import annotations

from app.contracts import DischargeCoordination


def initiate_discharge(patient_id: str) -> DischargeCoordination:
    """Fan out 5 subtasks: summary, pharmacy, family, follow-up, billing."""
    raise NotImplementedError("Person B — Day 8")


def discharge_status(patient_id: str) -> DischargeCoordination:
    raise NotImplementedError("Person B — Day 8")
