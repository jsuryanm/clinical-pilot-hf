"""Roster agent unit tests."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path

import pytest

from app.agents.roster.scheduler import (
    StaffRecord,
    fairness_score,
    greedy_schedule,
)
from app.agents.roster.api import find_sick_call_replacement, generate_roster, load_staff
from app.contracts import RosterResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

STAFF = [
    StaffRecord(id="n-01", name="Priya", role="nurse", certifications=[], max_hours_per_week=48),
    StaffRecord(id="n-02", name="Anjali", role="nurse", certifications=[], max_hours_per_week=48),
    StaffRecord(id="n-03", name="Ravi", role="nurse", certifications=[], max_hours_per_week=48),
    StaffRecord(id="d-01", name="Dr. Sharma", role="doctor", certifications=[], max_hours_per_week=40),
    StaffRecord(id="d-02", name="Dr. Mehta", role="doctor", certifications=[], max_hours_per_week=40),
]


def _write_staff_csv(staff: list[StaffRecord]) -> Path:
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".csv", delete=False, newline="", encoding="utf-8"
    )
    writer = csv.DictWriter(f, fieldnames=["id","name","role","certifications","max_hours","leave_days"])
    writer.writeheader()
    for s in staff:
        writer.writerow({
            "id": s.id, "name": s.name, "role": s.role,
            "certifications": ";".join(s.certifications),
            "max_hours": s.max_hours_per_week,
            "leave_days": ";".join(s.leave_days),
        })
    f.close()
    return Path(f.name)


# ---------------------------------------------------------------------------
# Scheduler unit tests
# ---------------------------------------------------------------------------

def test_scheduler_produces_assignments() -> None:
    assignments, conflicts = greedy_schedule(STAFF, window_days=7,
        window_start=__import__("datetime").datetime(2026, 6, 9, tzinfo=__import__("datetime").timezone.utc))
    assert len(assignments) > 0


def test_scheduler_respects_leave() -> None:
    staff = [
        StaffRecord(id="n-01", name="Priya", role="nurse", certifications=[],
                    max_hours_per_week=48, leave_days={"2026-06-09"}),
        StaffRecord(id="n-02", name="Anjali", role="nurse", certifications=[],
                    max_hours_per_week=48),
    ]
    import datetime as dt
    start = dt.datetime(2026, 6, 9, tzinfo=dt.timezone.utc)
    assignments, _ = greedy_schedule(staff, window_start=start, window_days=1)
    on_leave_day = [
        a for a in assignments
        if a.staff_id == "n-01" and a.start.date().isoformat() == "2026-06-09"
    ]
    assert len(on_leave_day) == 0, "Leave days must be respected"


def test_fairness_score_range() -> None:
    import datetime as dt
    start = dt.datetime(2026, 6, 9, tzinfo=dt.timezone.utc)
    assignments, _ = greedy_schedule(STAFF, window_start=start, window_days=14)
    score = fairness_score(STAFF, assignments)
    assert 0.0 <= score <= 1.0


def test_no_staff_produces_conflict() -> None:
    assignments, conflicts = greedy_schedule([], window_days=1,
        window_start=__import__("datetime").datetime(2026, 6, 9, tzinfo=__import__("datetime").timezone.utc))
    assert len(assignments) == 0
    assert len(conflicts) > 0


# ---------------------------------------------------------------------------
# API integration test
# ---------------------------------------------------------------------------

def test_generate_roster_returns_valid_model() -> None:
    csv_path = _write_staff_csv(STAFF)
    result = generate_roster(csv_path, window_days=7)
    assert isinstance(result, RosterResult)
    assert 0.0 <= result.fairness_score <= 1.0
    assert result.generated_in_seconds < 60  # greedy is fast
    assert result.assignments


def test_load_staff_accepts_current_test_csv_headers() -> None:
    csv_path = _write_staff_csv(STAFF)
    staff = load_staff(csv_path)
    assert staff[0].id == "n-01"
    assert staff[0].max_hours_per_week == 48


def test_sick_call_replacement_picks_same_role_replacement() -> None:
    import datetime as dt

    start = dt.datetime(2026, 6, 9, tzinfo=dt.timezone.utc)
    assignments, _ = greedy_schedule(STAFF, window_start=start, window_days=1)
    roster = RosterResult(
        roster_id="rost-test",
        window_start=start,
        window_end=start + dt.timedelta(days=1),
        assignments=assignments,
        fairness_score=fairness_score(STAFF, assignments),
        unresolved_conflicts=[],
        generated_in_seconds=0.01,
    )
    target = next(a for a in assignments if a.role == "nurse")

    updated = find_sick_call_replacement(target.shift_id, target.staff_id, staff=STAFF, roster=roster)

    replacement = next(a for a in updated.assignments if a.shift_id == target.shift_id)
    assert replacement.staff_id != target.staff_id
    assert replacement.role == target.role
    assert replacement.is_replacement is True

