"""Handover Agent - public API.

Person C owns handover generation, but the agent does not make clinical
decisions. It summarises and orders patients so a nurse can review the brief.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from app.contracts import Citation, HandoverBrief, PatientBrief, Priority

_WPM = 200
_PRIORITY_ORDER = {Priority.URGENT: 0, Priority.WATCH: 1, Priority.STABLE: 2}


@dataclass
class PatientRecord:
    """Input row, normally read from Postgres by the service layer."""

    patient_id: str
    name: str
    bed: str | None
    vitals: dict[str, object]
    last_shift_notes: str


def build_brief(
    ward_id: str,
    shift_end_ts: datetime,
    records: list[PatientRecord],
    wiki_lookup,
) -> HandoverBrief:
    """Build a contract-valid handover brief from patient records.

    wiki_lookup(patient_id) is injected so the production path can call Person
    A's wiki API while tests and demos can stay deterministic.
    """
    patients = [_summarise_patient(record, wiki_lookup(record.patient_id)) for record in records]
    patients.sort(key=lambda patient: _PRIORITY_ORDER[patient.priority])

    words = sum(
        len(patient.one_liner.split())
        + sum(len(action.split()) for action in patient.actions_pending)
        for patient in patients
    )
    estimated_read_minutes = max(1, min(5, round(words / _WPM) or 1))

    return HandoverBrief(
        brief_id=f"hb-{uuid4().hex[:8]}",
        ward_id=ward_id,
        shift_end_ts=shift_end_ts,
        patients=patients,
        estimated_read_minutes=estimated_read_minutes,
    )


def generate_handover(ward_id: str, shift_end_ts: datetime) -> HandoverBrief:
    """Published interface with deterministic synthetic records for dev/demo."""
    records = [
        PatientRecord(
            patient_id="p-007",
            name="Demo urgent patient",
            bed="A-12",
            vitals={"temperature_c": 38.7, "heart_rate": 118},
            last_shift_notes="Fever with rising heart rate after surgery.",
        ),
        PatientRecord(
            patient_id="p-011",
            name="Demo watch patient",
            bed="A-09",
            vitals={"spo2": 94},
            last_shift_notes="Needs repeat observations before next antibiotic dose.",
        ),
        PatientRecord(
            patient_id="p-019",
            name="Demo stable patient",
            bed="A-04",
            vitals={"spo2": 98, "heart_rate": 78},
            last_shift_notes="Comfortable and awaiting discharge paperwork.",
        ),
    ]
    return build_brief(
        ward_id=ward_id,
        shift_end_ts=shift_end_ts or datetime.now(timezone.utc),
        records=records,
        wiki_lookup=lambda patient_id: f"Synthetic wiki history for {patient_id}.",
    )


def _summarise_patient(record: PatientRecord, wiki_excerpt: str) -> PatientBrief:
    priority = _priority_from_record(record)
    return PatientBrief(
        patient_id=record.patient_id,
        bed=record.bed,
        priority=priority,
        one_liner=_one_liner(record, priority)[:160],
        actions_pending=_actions_for(record, priority),
        sources=[
            Citation(
                source_type="wiki",
                source_id=f"patients/{record.patient_id}",
                snippet=wiki_excerpt[:160],
            )
        ],
    )


def _priority_from_record(record: PatientRecord) -> Priority:
    vitals = {key.lower(): value for key, value in record.vitals.items()}
    notes = record.last_shift_notes.lower()
    temperature = _as_float(vitals.get("temperature_c") or vitals.get("temp"))
    heart_rate = _as_float(vitals.get("heart_rate") or vitals.get("hr"))
    spo2 = _as_float(vitals.get("spo2"))

    if (
        "urgent" in notes
        or "deteriorat" in notes
        or (temperature is not None and temperature >= 38.5)
        or (heart_rate is not None and heart_rate >= 120)
        or (spo2 is not None and spo2 < 92)
    ):
        return Priority.URGENT
    if (
        "watch" in notes
        or "repeat" in notes
        or ("pending" in notes and "discharge" not in notes)
        or (heart_rate is not None and heart_rate >= 105)
        or (spo2 is not None and spo2 < 95)
    ):
        return Priority.WATCH
    return Priority.STABLE


def _actions_for(record: PatientRecord, priority: Priority) -> list[str]:
    notes = record.last_shift_notes.lower()
    if priority == Priority.URGENT:
        return ["Nurse-in-charge review before next round"]
    if priority == Priority.WATCH:
        return ["Repeat observations and review pending tasks"]
    if "discharge" in notes:
        return ["Confirm discharge paperwork status"]
    return []


def _one_liner(record: PatientRecord, priority: Priority) -> str:
    note = " ".join(record.last_shift_notes.split())
    prefix = f"{record.bed or 'No bed'} {priority.value}:"
    return f"{prefix} {note}" if note else f"{prefix} Review latest vitals and chart."


def _as_float(value: object) -> float | None:
    try:
        return float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
