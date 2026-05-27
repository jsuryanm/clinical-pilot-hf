"""Fake Discharge Agent output. OWNER: Person B."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.contracts import (
    DischargeCoordination,
    DischargeSubtask,
    DischargeSubtaskStatus,
)


def fake_discharge(patient_id: str = "p-001") -> DischargeCoordination:
    now = datetime.now(timezone.utc)
    return DischargeCoordination(
        discharge_id=f"dsc-{uuid4().hex[:8]}",
        patient_id=patient_id,
        initiated_at=now,
        target_complete_by=now + timedelta(minutes=90),
        subtasks=[
            DischargeSubtask(
                name="discharge_summary",
                status=DischargeSubtaskStatus.AWAITING_APPROVAL,
                detail="Drafted from SOAP soap-001; awaiting Dr. Sharma approval.",
                artifact_id="soap-001",
            ),
            DischargeSubtask(
                name="pharmacy",
                status=DischargeSubtaskStatus.IN_PROGRESS,
                detail="3 meds queued at pharmacy counter 2.",
            ),
            DischargeSubtask(
                name="family_notification",
                status=DischargeSubtaskStatus.DONE,
                detail="WhatsApp sent to next-of-kin at 14:02.",
            ),
            DischargeSubtask(
                name="follow_up_appointment",
                status=DischargeSubtaskStatus.DONE,
                detail="Booked 7-day follow-up with Dr. Sharma.",
                artifact_id="appt-002",
            ),
            DischargeSubtask(
                name="billing_trigger",
                status=DischargeSubtaskStatus.QUEUED,
                detail="Billing dept notified; final bill pending pharmacy total.",
            ),
        ],
    )
