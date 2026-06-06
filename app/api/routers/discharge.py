"""Discharge router — OWNER: Person B (logic), Person C (wiring/triggers)."""

from __future__ import annotations

from fastapi import APIRouter

from app.agents.discharge import api as discharge_api
from app.contracts import DischargeCoordination

router = APIRouter()


@router.post("/{patient_id}", response_model=DischargeCoordination)
def initiate(patient_id: str) -> DischargeCoordination:
    """Fan out the 5 discharge subtasks in parallel."""
    return discharge_api.initiate_discharge(patient_id)


@router.get("/{patient_id}/status", response_model=DischargeCoordination)
def status(patient_id: str) -> DischargeCoordination:
    """Return current subtask statuses for an in-progress discharge."""
    return discharge_api.discharge_status(patient_id)
