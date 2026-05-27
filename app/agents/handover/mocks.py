"""Fake Handover Agent output. OWNER: Person C."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.contracts import Citation, HandoverBrief, PatientBrief, Priority


def fake_handover(ward_id: str = "ward-A") -> HandoverBrief:
    return HandoverBrief(
        brief_id=f"hb-{uuid4().hex[:8]}",
        ward_id=ward_id,
        shift_end_ts=datetime.now(timezone.utc),
        estimated_read_minutes=5,
        patients=[
            PatientBrief(
                patient_id="p-007",
                bed="A-12",
                priority=Priority.URGENT,
                one_liner=(
                    "Post-op day 1 cholecystectomy, fever 38.7°C, HR trending up — review wound."
                ),
                actions_pending=["Blood culture pending", "Surgeon review needed"],
                sources=[Citation(source_type="wiki", source_id="patients/p-007")],
            ),
            PatientBrief(
                patient_id="p-011",
                bed="A-09",
                priority=Priority.WATCH,
                one_liner="CAP, day 2 IV ceftriaxone, SpO2 95% on room air — continue plan.",
                actions_pending=["Repeat CXR tomorrow"],
                sources=[Citation(source_type="wiki", source_id="patients/p-011")],
            ),
            PatientBrief(
                patient_id="p-019",
                bed="A-04",
                priority=Priority.STABLE,
                one_liner="Stable, awaiting discharge paperwork.",
                actions_pending=[],
            ),
        ],
    )
