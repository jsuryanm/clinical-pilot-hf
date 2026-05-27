"""Fake Rostering Agent output. OWNER: Person C."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.contracts import RosterResult, ShiftAssignment


def fake_roster() -> RosterResult:
    start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=14)
    assignments: list[ShiftAssignment] = []
    staff = [
        ("nurse-01", "nurse"),
        ("nurse-02", "nurse"),
        ("nurse-03", "nurse"),
        ("doc-01", "doctor"),
        ("doc-02", "doctor"),
    ]
    for day in range(14):
        d = start + timedelta(days=day)
        for i, (sid, role) in enumerate(staff):
            shift_start = d + timedelta(hours=8 + (i % 3) * 8)
            assignments.append(
                ShiftAssignment(
                    shift_id=f"sh-{uuid4().hex[:6]}",
                    staff_id=sid,
                    role=role,  # type: ignore[arg-type]
                    start=shift_start,
                    end=shift_start + timedelta(hours=8),
                )
            )
    return RosterResult(
        roster_id=f"rost-{uuid4().hex[:8]}",
        window_start=start,
        window_end=end,
        assignments=assignments,
        fairness_score=0.87,
        unresolved_conflicts=[],
        generated_in_seconds=0.42,
    )
