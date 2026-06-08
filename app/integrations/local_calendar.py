"""A small, self-hosted calendar "MCP" backed by Postgres. OWNER: Person A.

Replaces the Google Calendar dependency for the demo. It exposes exactly three
operations the clinic needs — **book**, **cancel**, **change** — plus a
``list_appointments`` helper the slot-finder uses to see what's busy.

State lives in the existing Postgres tables (``app/db/models.py``):
  - ``staff``        — doctors / nurses (id, name, role)
  - ``appointments`` — patient_id, doctor_id, slot, duration, status

Sessions: every function takes an optional SQLAlchemy ``session``; when omitted
it opens one from ``app.db.session.SessionLocal`` and commits/closes it. Tests
inject a SQLite session, so this module needs no live Postgres to verify.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import session as db_session
from app.db.models import Appointment, BookingStatusEnum, Staff

log = structlog.get_logger(__name__)

_DEFAULT_DURATION = 15  # minutes
_ACTIVE = (BookingStatusEnum.PROPOSED, BookingStatusEnum.CONFIRMED)


@contextmanager
def _session(session: Session | None) -> Iterator[tuple[Session, bool]]:
    """Yield (session, owns). When we opened it (owns=True) we commit/close."""
    if session is not None:
        yield session, False
        return
    s = db_session.SessionLocal()
    try:
        yield s, True
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def _aware(dt: datetime) -> datetime:
    """Treat naive datetimes (e.g. read back from SQLite) as UTC. No-op on Postgres."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _to_event(appt: Appointment) -> dict:
    """Shape an Appointment like a calendar event (compatible with calendar_mcp)."""
    start = _aware(appt.slot_iso)
    end = start + timedelta(minutes=appt.duration_minutes)
    return {
        "id": appt.id,
        "title": f"Appointment — {appt.patient_id}",
        "start_iso": start.isoformat(),
        "end_iso": end.isoformat(),
        "patient_id": appt.patient_id,
        "doctor_id": appt.doctor_id,
        "status": appt.status.value,
    }


def _overlaps(session: Session, doctor_id: str, start: datetime, end: datetime,
              exclude_id: str | None = None) -> bool:
    """True if the doctor already has an active appointment overlapping [start, end)."""
    stmt = select(Appointment).where(
        Appointment.doctor_id == doctor_id,
        Appointment.status.in_(_ACTIVE),
    )
    for appt in session.scalars(stmt):
        if exclude_id and appt.id == exclude_id:
            continue
        a_start = _aware(appt.slot_iso)
        a_end = a_start + timedelta(minutes=appt.duration_minutes)
        if a_start < end and a_end > start:
            return True
    return False


# ---------------------------------------------------------------------------
# The three operations
# ---------------------------------------------------------------------------


def book_appointment(
    patient_id: str,
    doctor_id: str,
    slot: datetime,
    duration_minutes: int = _DEFAULT_DURATION,
    notes: str | None = None,
    *,
    session: Session | None = None,
) -> dict:
    """Book a slot for a patient with a doctor.

    Raises ValueError if the doctor already has an overlapping active booking.
    Returns the created event dict (``id`` is the appointment id).
    """
    end = slot + timedelta(minutes=duration_minutes)
    with _session(session) as (s, _owns):
        if _overlaps(s, doctor_id, slot, end):
            raise ValueError(f"slot {slot.isoformat()} for {doctor_id} is already booked")

        appt = Appointment(
            id=f"appt-{uuid4().hex[:8]}",
            patient_id=patient_id,
            doctor_id=doctor_id,
            slot_iso=slot,
            duration_minutes=duration_minutes,
            status=BookingStatusEnum.CONFIRMED,
            notes=notes,
        )
        s.add(appt)
        s.flush()  # populate defaults before we read it back
        event = _to_event(appt)

    log.info("local_calendar.booked", appt_id=event["id"], doctor_id=doctor_id)
    return event


def cancel_appointment(
    appointment_id: str, reason: str | None = None, *, session: Session | None = None
) -> dict:
    """Cancel an appointment. Returns the updated event dict.

    Raises KeyError if the appointment does not exist.
    """
    with _session(session) as (s, _owns):
        appt = s.get(Appointment, appointment_id)
        if appt is None:
            raise KeyError(f"appointment {appointment_id} not found")
        appt.status = BookingStatusEnum.CANCELLED
        if reason:
            appt.notes = f"{appt.notes + ' | ' if appt.notes else ''}Cancelled: {reason}"
        s.flush()
        event = _to_event(appt)

    log.info("local_calendar.cancelled", appt_id=appointment_id, reason=reason)
    return event


def change_appointment(
    appointment_id: str,
    new_slot: datetime,
    duration_minutes: int | None = None,
    *,
    session: Session | None = None,
) -> dict:
    """Move an appointment to a new slot. Returns the updated event dict.

    Raises KeyError if not found, ValueError if the new slot clashes.
    """
    with _session(session) as (s, _owns):
        appt = s.get(Appointment, appointment_id)
        if appt is None:
            raise KeyError(f"appointment {appointment_id} not found")

        dur = duration_minutes or appt.duration_minutes
        end = new_slot + timedelta(minutes=dur)
        if _overlaps(s, appt.doctor_id, new_slot, end, exclude_id=appointment_id):
            raise ValueError(f"new slot {new_slot.isoformat()} clashes with another booking")

        appt.slot_iso = new_slot
        appt.duration_minutes = dur
        appt.status = BookingStatusEnum.CONFIRMED
        s.flush()
        event = _to_event(appt)

    log.info("local_calendar.changed", appt_id=appointment_id, new_slot=new_slot.isoformat())
    return event


# ---------------------------------------------------------------------------
# Read helper (used by the slot-finder)
# ---------------------------------------------------------------------------


def list_appointments(
    doctor_id: str,
    t_start: datetime,
    t_end: datetime,
    *,
    session: Session | None = None,
) -> list[dict]:
    """Active appointments for a doctor that overlap [t_start, t_end)."""
    with _session(session) as (s, _owns):
        stmt = select(Appointment).where(
            Appointment.doctor_id == doctor_id,
            Appointment.status.in_(_ACTIVE),
        )
        out: list[dict] = []
        for appt in s.scalars(stmt):
            a_start = _aware(appt.slot_iso)
            a_end = a_start + timedelta(minutes=appt.duration_minutes)
            if a_start < t_end and a_end > t_start:
                out.append(_to_event(appt))
    return out


def ensure_staff(staff_id: str, name: str, role: str, *, session: Session | None = None) -> None:
    """Idempotently upsert a doctor/nurse row — handy for demo seeding."""
    with _session(session) as (s, _owns):
        if s.get(Staff, staff_id) is None:
            s.add(Staff(id=staff_id, name=name, role=role))
            log.info("local_calendar.staff_added", staff_id=staff_id, role=role)
