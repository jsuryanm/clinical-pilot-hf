"""Rostering Agent - public API. OWNER: Person C."""

from __future__ import annotations

import csv
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.agents.roster.scheduler import StaffRecord, fairness_score, greedy_schedule
from app.contracts import RosterResult, ShiftAssignment


def load_staff(staff_csv: Path) -> list[StaffRecord]:
    """Parse staff CSVs used by the app and tests.

    Preferred columns are staff_id,name,role,certifications,leave_days,max_hours_per_week.
    Demo/test CSVs may use id and max_hours; both aliases are accepted.
    """
    members: list[StaffRecord] = []
    with open(staff_csv, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            members.append(
                StaffRecord(
                    id=_first(row, "staff_id", "id").strip(),
                    name=_first(row, "name").strip(),
                    role=_first(row, "role").strip().lower(),
                    certifications=_split(row.get("certifications", "")),
                    max_hours_per_week=int(_first(row, "max_hours_per_week", "max_hours", default="48")),
                    leave_days=set(_split(row.get("leave_days", ""))),
                )
            )
    return members


def generate_roster(staff_csv: Path, window_days: int = 14) -> RosterResult:
    started = time.perf_counter()
    staff = load_staff(Path(staff_csv))
    window_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    window_end = window_start + timedelta(days=window_days)
    assignments, conflicts = greedy_schedule(
        staff,
        window_start=window_start,
        window_days=window_days,
    )
    return RosterResult(
        roster_id=f"rost-{int(started * 1000)}",
        window_start=window_start,
        window_end=window_end,
        assignments=assignments,
        fairness_score=fairness_score(staff, assignments),
        unresolved_conflicts=conflicts,
        generated_in_seconds=round(time.perf_counter() - started, 4),
    )


def find_sick_call_replacement(
    shift_id: str,
    sick_staff_id: str,
    *,
    staff: list[StaffRecord],
    roster: RosterResult,
) -> RosterResult:
    """Replace a sick staff member with the lowest-load same-role candidate."""
    target = next((a for a in roster.assignments if a.shift_id == shift_id), None)
    if target is None or target.staff_id != sick_staff_id:
        return roster

    target_date = target.start.date().isoformat()
    target_duration = (target.end - target.start).total_seconds() / 3600
    hours = _assigned_hours(roster.assignments)

    candidates = [
        member
        for member in staff
        if member.id != sick_staff_id
        and member.role == target.role
        and target_date not in member.leave_days
        and hours.get(member.id, 0.0) + target_duration <= _window_hour_cap(member, roster)
        and not any(
            assignment.staff_id == member.id
            and _overlaps(assignment.start, assignment.end, target.start, target.end)
            for assignment in roster.assignments
        )
    ]
    candidates.sort(key=lambda member: (hours.get(member.id, 0.0), member.name))

    remaining = [assignment for assignment in roster.assignments if assignment.shift_id != shift_id]
    if not candidates:
        unresolved = [
            *roster.unresolved_conflicts,
            f"{shift_id}: no valid replacement for {sick_staff_id}",
        ]
        return roster.model_copy(
            update={
                "assignments": remaining,
                "unresolved_conflicts": unresolved,
                "fairness_score": fairness_score(staff, remaining),
            }
        )

    pick = candidates[0]
    updated_assignments = [
        *remaining,
        ShiftAssignment(
            shift_id=target.shift_id,
            staff_id=pick.id,
            role=target.role,
            start=target.start,
            end=target.end,
            is_replacement=True,
        ),
    ]
    updated_assignments.sort(key=lambda assignment: (assignment.start, assignment.role, assignment.staff_id))
    return roster.model_copy(
        update={
            "assignments": updated_assignments,
            "fairness_score": fairness_score(staff, updated_assignments),
        }
    )


def _first(row: dict[str, str], *keys: str, default: str = "") -> str:
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return default


def _split(value: str) -> list[str]:
    return [part.strip() for part in value.split(";") if part.strip()]


def _assigned_hours(assignments: list[ShiftAssignment]) -> dict[str, float]:
    hours: dict[str, float] = {}
    for assignment in assignments:
        duration = (assignment.end - assignment.start).total_seconds() / 3600
        hours[assignment.staff_id] = hours.get(assignment.staff_id, 0.0) + duration
    return hours


def _overlaps(left_start: datetime, left_end: datetime, right_start: datetime, right_end: datetime) -> bool:
    return left_start < right_end and right_start < left_end


def _window_hour_cap(member: StaffRecord, roster: RosterResult) -> float:
    days = max(1, (roster.window_end - roster.window_start).days)
    weeks = max(1.0, days / 7)
    return member.max_hours_per_week * weeks

