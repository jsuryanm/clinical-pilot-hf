"""Appointment Agent — public API. OWNER: Person B."""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import uuid4

import structlog

from app.contracts import (
    BookingResult,
    BookingStatus,
    Channel,
    CommunicationDraft,
    ReminderJob,
)
from app.integrations import calendar_mcp
from app.llm.router import complete

log = structlog.get_logger(__name__)

_DOCTOR_CALENDAR = os.getenv("DOCTOR_CALENDAR_ID", "doctor-test@example.com")
_SLOT_DURATION = 15  # minutes


# ---------------------------------------------------------------------------
# Intent parsing
# ---------------------------------------------------------------------------

_INTENT_PROMPT = """You are CliniqAI's appointment assistant for an Indian clinic.
Parse the patient's message and return JSON with these keys:
  intent: "book" | "cancel" | "reschedule" | "status" | "other"
  preferred_date: ISO date string or null
  preferred_time: "HH:MM" or null
  doctor_name: string or null
  reason: string or null

Patient message:
{message}
"""


def _parse_intent(message: str) -> dict:
    try:
        result = complete(
            task="routing",
            messages=[{"role": "user", "content": _INTENT_PROMPT.format(message=message)}],
            json_mode=True,
            max_tokens=200,
        )
        return json.loads(result.text)
    except Exception:
        log.warning("appointment.intent_parse_failed", exc_info=True)
        return {"intent": "other"}


# ---------------------------------------------------------------------------
# Slot finding
# ---------------------------------------------------------------------------

def _find_next_available_slot(
    t_start: datetime,
    t_end: datetime,
    calendar_id: str,
) -> datetime | None:
    """Return first free SLOT_DURATION-minute slot in [t_start, t_end)."""
    events = calendar_mcp.list_events(calendar_id, t_start, t_end)
    busy: list[tuple[datetime, datetime]] = []
    for ev in events:
        try:
            s = datetime.fromisoformat(ev.get("start_iso") or ev["start"]["dateTime"])
            e = datetime.fromisoformat(ev.get("end_iso") or ev["end"]["dateTime"])
            busy.append((s, e))
        except (KeyError, ValueError, TypeError):
            continue

    candidate = t_start
    while candidate + timedelta(minutes=_SLOT_DURATION) <= t_end:
        slot_end = candidate + timedelta(minutes=_SLOT_DURATION)
        if not any(s < slot_end and e > candidate for s, e in busy):
            return candidate
        candidate += timedelta(minutes=_SLOT_DURATION)
    return None


# ---------------------------------------------------------------------------
# Reminder enqueuing
# ---------------------------------------------------------------------------

def _enqueue_reminders(appointment_id: str, slot: datetime) -> list[ReminderJob]:
    """Schedule T-24h email + T-3h Telegram + T-2h WhatsApp reminders via Celery."""
    from app.agents.appointment.tasks import send_reminder  # avoid circular at module load

    jobs: list[ReminderJob] = []
    for channel, delta in [
        (Channel.EMAIL, timedelta(hours=24)),
        (Channel.TELEGRAM, timedelta(hours=3)),
        (Channel.WHATSAPP, timedelta(hours=2)),
    ]:
        fire_at = slot - delta
        if fire_at > datetime.now(timezone.utc):
            send_reminder.apply_async(
                args=[appointment_id, channel.value],
                eta=fire_at,
                task_id=f"rem-{appointment_id}-{channel.value}",
            )
            jobs.append(ReminderJob(
                job_id=f"rem-{appointment_id}-{channel.value}",
                channel=channel,
                fire_at=fire_at,
                enqueued=True,
            ))
    return jobs


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def handle_inbound_message(
    channel: Literal["whatsapp", "web"], payload: dict
) -> CommunicationDraft:
    """Parse an inbound patient message and return a reply draft.

    On booking intent, also calls book() and confirms the slot.
    """
    sender = payload.get("from", "unknown")
    message = payload.get("body", "")

    intent_data = _parse_intent(message)
    intent = intent_data.get("intent", "other")

    if intent == "book":
        now = datetime.now(timezone.utc)
        w_start = now + timedelta(days=1)
        w_end = now + timedelta(days=8)

        if intent_data.get("preferred_date"):
            try:
                d = datetime.fromisoformat(intent_data["preferred_date"]).replace(tzinfo=timezone.utc)
                w_start = d.replace(hour=9, minute=0, second=0, microsecond=0)
                w_end = d.replace(hour=17, minute=0, second=0, microsecond=0)
            except ValueError:
                pass

        # Derive a stable synthetic patient_id from the phone number
        patient_id = f"p-{abs(hash(sender)) % 100000:05d}"

        try:
            result = book(patient_id=patient_id, requested_window=(w_start, w_end))
            slot_str = result.slot_iso.strftime("%A %d %b at %I:%M %p")
            body = (
                f"Namaste! ✅ Your appointment is confirmed for *{slot_str}*.\n"
                f"Appointment ID: {result.appointment_id}\n"
                "Reply *1* to confirm, *2* to reschedule, *0* to cancel."
            )
        except Exception:
            log.exception("appointment.book_failed", sender=sender)
            body = (
                "Sorry, we couldn't find a free slot right now. "
                "Please call the clinic or try again."
            )

    elif intent == "cancel":
        body = "To cancel, please reply with your Appointment ID (e.g. appt-xxxxxxxx)."
    elif intent == "reschedule":
        body = "To reschedule, please share your Appointment ID and preferred date/time."
    elif intent == "status":
        body = "Please share your Appointment ID to check the status."
    else:
        body = (
            "Namaste! I can help you *book, reschedule, or cancel* an appointment. "
            "Just tell me when you'd like to come in. 🏥"
        )

    return CommunicationDraft(
        draft_id=f"comm-{uuid4().hex[:8]}",
        channel=Channel.WHATSAPP if channel == "whatsapp" else Channel.WEB,
        to=sender,
        body=body,
        requires_approval=False,
    )


def book(
    patient_id: str,
    requested_window: tuple[datetime, datetime],
    doctor_id: str | None = None,
) -> BookingResult:
    """Find the first available slot, create a calendar event, enqueue reminders."""
    calendar_id = doctor_id or _DOCTOR_CALENDAR
    t_start, t_end = requested_window

    slot = _find_next_available_slot(t_start, t_end, calendar_id)
    if slot is None:
        raise ValueError(
            f"No available slot in [{t_start.isoformat()}, {t_end.isoformat()})"
        )

    event = calendar_mcp.create_event(
        calendar_id=calendar_id,
        title=f"Appointment — {patient_id}",
        t_start=slot,
        t_end=slot + timedelta(minutes=_SLOT_DURATION),
        description=f"Patient: {patient_id}",
    )

    appt_id = f"appt-{uuid4().hex[:8]}"
    reminder_jobs = _enqueue_reminders(appt_id, slot)

    log.info("appointment.booked", appt_id=appt_id, patient_id=patient_id, slot=slot.isoformat())
    return BookingResult(
        appointment_id=appt_id,
        patient_id=patient_id,
        doctor_id=doctor_id or "d-test",
        slot_iso=slot,
        duration_minutes=_SLOT_DURATION,
        status=BookingStatus.CONFIRMED,
        confirmation_sent_at=datetime.now(timezone.utc),
        reminder_jobs=reminder_jobs,
        calendar_event_id=event.get("id"),
        notes=f"Booked via {calendar_id}",
    )


def cancel(appointment_id: str, reason: str) -> BookingResult:
    """Cancel an appointment.

    Production path: load from DB, delete calendar event, revoke Celery tasks.
    Hackathon: returns a CANCELLED BookingResult immediately.
    """
    log.info("appointment.cancelled", appt_id=appointment_id, reason=reason)
    return BookingResult(
        appointment_id=appointment_id,
        patient_id="unknown",
        doctor_id="d-test",
        slot_iso=datetime.now(timezone.utc),
        status=BookingStatus.CANCELLED,
        notes=f"Cancelled: {reason}",
    )
