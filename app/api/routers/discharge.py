"""Discharge router — OWNER: Person B (logic), Person C (wiring/triggers)."""

from __future__ import annotations

from fastapi import APIRouter

from app.agents.discharge.mocks import fake_discharge
from app.contracts import DischargeCoordination

router = APIRouter()


@router.post("/{patient_id}", response_model=DischargeCoordination)
def initiate(patient_id: str) -> DischargeCoordination:
    """Fan out the 5 discharge subtasks in parallel.

    TODO(Person B): replace with `app.agents.discharge.api.initiate_discharge(...)`.
    """
    return fake_discharge(patient_id=patient_id)


@router.get("/{patient_id}/status", response_model=DischargeCoordination)
def status(patient_id: str) -> DischargeCoordination:
    """TODO(Person B): poll subtask statuses."""
    return fake_discharge(patient_id=patient_id)
