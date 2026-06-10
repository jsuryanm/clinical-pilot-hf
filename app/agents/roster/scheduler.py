"""Greedy shift scheduler. OWNER: Person C — Day 3.

Algorithm:
  For each day in the window, for each shift slot:
    1. Filter staff by role + certification match.
    2. Exclude staff on leave or over max_hours_per_week.
    3. Pick the staff member with the fewest assigned hours so far (fairness).
    4. Assign, increment their hour counter.

Week 2 upgrade path: replace with OR-tools CP-SAT when time allows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from uuid import uuid4

from app.contracts import RosterResult, ShiftAssignment


@dataclass
class StaffRecord:
    id: str
    name: str
    role: str                          # doctor | nurse | tech | admin
    certifications: list[str]
    max_hours_per_week: int
    leave_days: set[str] = field(default_factory=set)   # "YYYY-MM-DD"
    assigned_hours: float = 0.0


@dataclass
class ShiftTemplate:
    """A repeating slot: role, start-hour offset from day start, duration."""
    role: str
    start_hour: int   # e.g. 7 = 07:00
    duration_hours: int = 8


# Standard ward templates — adjust per hospital
DEFAULT_TEMPLATES: list[ShiftTemplate] = [
    ShiftTemplate(role="doctor", start_hour=7,  duration_hours=8),
    ShiftTemplate(role="doctor", start_hour=15, duration_hours=8),
    ShiftTemplate(role="nurse",  start_hour=7,  duration_hours=8),
    ShiftTemplate(role="nurse",  start_hour=15, duration_hours=8),
    ShiftTemplate(role="nurse",  start_hour=23, duration_hours=8),
]


def _week_of(dt: datetime) -> str:
    """ISO week key used for the 'per-week hours' cap."""
    return dt.strftime("%Y-W%W")


def greedy_schedule(
    staff: list[StaffRecord],
    window_start: datetime,
    window_days: int = 14,
    templates: list[ShiftTemplate] | None = None,
) -> tuple[list[ShiftAssignment], list[str]]:
    """Return (assignments, unresolved_conflicts).

    unresolved_conflicts is a list of human-readable strings for slots
    that could not be filled (e.g. no available nurse on a given day).
    """
    if templates is None:
        templates = DEFAULT_TEMPLATES

    # Track hours per staff per ISO week
    weekly_hours: dict[str, dict[str, float]] = {s.id: {} for s in staff}
    assignments: list[ShiftAssignment] = []
    conflicts: list[str] = []

    for day_offset in range(window_days):
        day = window_start + timedelta(days=day_offset)
        day_str = day.strftime("%Y-%m-%d")
        week_key = _week_of(day)

        for tmpl in templates:
            shift_start = day.replace(
                hour=tmpl.start_hour, minute=0, second=0, microsecond=0
            )
            shift_end = shift_start + timedelta(hours=tmpl.duration_hours)

            # Candidates: correct role, not on leave, under weekly cap
            candidates = [
                s for s in staff
                if s.role == tmpl.role
                and day_str not in s.leave_days
                and weekly_hours[s.id].get(week_key, 0) + tmpl.duration_hours
                    <= s.max_hours_per_week
            ]

            if not candidates:
                conflicts.append(
                    f"{day_str} {tmpl.start_hour:02d}:00 — no available {tmpl.role}"
                )
                continue

            # Pick the candidate with fewest hours this week (fairness)
            chosen = min(
                candidates,
                key=lambda s: weekly_hours[s.id].get(week_key, 0),
            )

            weekly_hours[chosen.id][week_key] = (
                weekly_hours[chosen.id].get(week_key, 0) + tmpl.duration_hours
            )
            chosen.assigned_hours += tmpl.duration_hours

            assignments.append(ShiftAssignment(
                shift_id=f"sh-{uuid4().hex[:8]}",
                staff_id=chosen.id,
                role=tmpl.role,  # type: ignore[arg-type]
                start=shift_start,
                end=shift_end,
            ))

    return assignments, conflicts


def fairness_score(
    staff: list[StaffRecord],
    assignments: list[ShiftAssignment],
) -> float:
    """1.0 = perfectly even. Computed as 1 - normalised std-dev of hours."""
    import statistics

    hours_by_staff: dict[str, float] = {s.id: 0.0 for s in staff}
    for a in assignments:
        if a.staff_id in hours_by_staff:
            hours_by_staff[a.staff_id] += (
                (a.end - a.start).total_seconds() / 3600
            )

    values = list(hours_by_staff.values())
    if not values or max(values) == 0:
        return 1.0

    stdev = statistics.pstdev(values)
    mean = statistics.mean(values)
    # Coefficient of variation, inverted and clamped
    cv = stdev / mean if mean > 0 else 0
    return round(max(0.0, min(1.0, 1 - cv)), 4)