"""Postgres-backed mini calendar MCP tests. OWNER: Person A.

Runs against an in-memory SQLite DB (shared connection via StaticPool) so no
live Postgres is needed — the model layer is the same.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.models import Base, Patient, Staff
from app.integrations import local_calendar

_DAY = datetime(2026, 7, 1, 9, 0, tzinfo=timezone.utc)


@pytest.fixture()
def SessionMaker():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, future=True)
    # seed a patient + doctor (FK targets)
    with maker() as s:
        s.add(Patient(id="p-001", name="Test Patient"))
        s.add(Staff(id="d-001", name="Dr. Rao", role="doctor"))
        s.commit()
    return maker


@pytest.fixture()
def session(SessionMaker):
    s = SessionMaker()
    yield s
    s.close()


# --- the three operations -----------------------------------------------------


def test_book_creates_confirmed_appointment(session) -> None:
    ev = local_calendar.book_appointment("p-001", "d-001", _DAY, session=session)
    assert ev["id"].startswith("appt-")
    assert ev["status"] == "confirmed"
    assert ev["doctor_id"] == "d-001"
    assert ev["start_iso"] == _DAY.isoformat()


def test_double_booking_same_slot_raises(session) -> None:
    local_calendar.book_appointment("p-001", "d-001", _DAY, session=session)
    with pytest.raises(ValueError):
        local_calendar.book_appointment("p-001", "d-001", _DAY, session=session)


def test_non_overlapping_slot_is_allowed(session) -> None:
    local_calendar.book_appointment("p-001", "d-001", _DAY, session=session)
    later = _DAY + timedelta(minutes=15)
    ev = local_calendar.book_appointment("p-001", "d-001", later, session=session)
    assert ev["status"] == "confirmed"


def test_cancel_sets_status(session) -> None:
    ev = local_calendar.book_appointment("p-001", "d-001", _DAY, session=session)
    out = local_calendar.cancel_appointment(ev["id"], reason="patient request", session=session)
    assert out["status"] == "cancelled"


def test_cancel_unknown_raises(session) -> None:
    with pytest.raises(KeyError):
        local_calendar.cancel_appointment("appt-nope", session=session)


def test_change_moves_slot(session) -> None:
    ev = local_calendar.book_appointment("p-001", "d-001", _DAY, session=session)
    new_slot = _DAY + timedelta(hours=2)
    out = local_calendar.change_appointment(ev["id"], new_slot, session=session)
    assert out["start_iso"] == new_slot.isoformat()


def test_cancelled_slot_frees_for_rebooking(session) -> None:
    ev = local_calendar.book_appointment("p-001", "d-001", _DAY, session=session)
    local_calendar.cancel_appointment(ev["id"], session=session)
    # slot is free again now that the first booking is cancelled
    ev2 = local_calendar.book_appointment("p-001", "d-001", _DAY, session=session)
    assert ev2["status"] == "confirmed"


def test_list_appointments_window(session) -> None:
    local_calendar.book_appointment("p-001", "d-001", _DAY, session=session)
    hits = local_calendar.list_appointments(
        "d-001", _DAY - timedelta(hours=1), _DAY + timedelta(hours=1), session=session
    )
    assert len(hits) == 1
    none = local_calendar.list_appointments(
        "d-001", _DAY + timedelta(days=1), _DAY + timedelta(days=2), session=session
    )
    assert none == []


# --- calendar_mcp delegation (CALENDAR_BACKEND=local) -------------------------


def test_calendar_mcp_routes_to_local(SessionMaker, monkeypatch) -> None:
    monkeypatch.setenv("CALENDAR_BACKEND", "local")
    monkeypatch.setattr("app.db.session.SessionLocal", SessionMaker)
    from app.integrations import calendar_mcp

    # create_event -> book_appointment (patient id parsed from description)
    ev = calendar_mcp.create_event(
        calendar_id="d-001",
        title="Appointment — p-001",
        t_start=_DAY,
        t_end=_DAY + timedelta(minutes=15),
        description="Patient: p-001",
    )
    assert ev["id"].startswith("appt-")

    # list_events -> list_appointments sees the booking
    events = calendar_mcp.list_events("d-001", _DAY - timedelta(hours=1), _DAY + timedelta(hours=1))
    assert any(e["id"] == ev["id"] for e in events)

    # delete_event -> cancel_appointment
    assert calendar_mcp.delete_event("d-001", ev["id"]) is True
    after = calendar_mcp.list_events("d-001", _DAY - timedelta(hours=1), _DAY + timedelta(hours=1))
    assert all(e["id"] != ev["id"] for e in after)
