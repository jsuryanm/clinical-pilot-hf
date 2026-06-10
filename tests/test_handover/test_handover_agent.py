"""Handover agent unit tests."""

from __future__ import annotations

from datetime import datetime, timezone

from app.agents.handover.api import PatientRecord, build_brief, generate_handover
from app.contracts import HandoverBrief, Priority


def test_build_brief_orders_patients_by_priority() -> None:
    records = [
        PatientRecord(
            patient_id="p-stable",
            name="Stable Patient",
            bed="A-01",
            vitals={"spo2": 98},
            last_shift_notes="Comfortable, discharge paperwork pending.",
        ),
        PatientRecord(
            patient_id="p-urgent",
            name="Urgent Patient",
            bed="A-02",
            vitals={"temperature_c": 39.1, "heart_rate": 122},
            last_shift_notes="Fever with rising heart rate.",
        ),
        PatientRecord(
            patient_id="p-watch",
            name="Watch Patient",
            bed="A-03",
            vitals={"spo2": 93},
            last_shift_notes="Needs repeat observations.",
        ),
    ]

    brief = build_brief(
        "ward-A",
        datetime(2026, 6, 9, 19, 0, tzinfo=timezone.utc),
        records,
        wiki_lookup=lambda patient_id: f"wiki page for {patient_id}",
    )

    assert [p.priority for p in brief.patients] == [
        Priority.URGENT,
        Priority.WATCH,
        Priority.STABLE,
    ]


def test_generate_handover_returns_valid_contract() -> None:
    brief = generate_handover("ward-A", datetime(2026, 6, 9, 19, 0, tzinfo=timezone.utc))
    assert isinstance(brief, HandoverBrief)
    assert brief.ward_id == "ward-A"
    assert brief.patients
    assert brief.estimated_read_minutes <= 5
