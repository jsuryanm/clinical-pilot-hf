"""Celery app + reminder tasks. OWNER: Person B.

Run worker: `make worker`
Run beat:   `make beat`
"""

from __future__ import annotations

import os

import structlog
from celery import Celery
from celery.schedules import crontab

log = structlog.get_logger(__name__)

app = Celery(
    "cliniqai",
    broker=os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1"),
    backend=os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2"),
)
app.conf.timezone = "Asia/Kolkata"
app.conf.enable_utc = True


# ---------------------------------------------------------------------------
# LLM-rendered message copy
# ---------------------------------------------------------------------------

_REMINDER_PROMPT = """You are a friendly appointment reminder bot for an Indian clinic.
Write a short reminder (max 2 sentences) for a patient.
Language: Hinglish (mix of Hindi and English is fine).
Channel: {channel}.
Appointment ID: {appointment_id}.
Be warm, clear, and tell the patient to arrive 10 min early.
"""


def _render_reminder(appointment_id: str, channel: str) -> str:
    try:
        from app.llm.router import complete

        result = complete(
            task="reminder",
            messages=[{
                "role": "user",
                "content": _REMINDER_PROMPT.format(channel=channel, appointment_id=appointment_id),
            }],
            max_tokens=120,
        )
        return result.text.strip()
    except Exception:
        log.warning("tasks.reminder_llm_failed", appt_id=appointment_id, exc_info=True)
        return (
            f"Reminder: You have an upcoming appointment (ID: {appointment_id}). "
            "Please arrive 10 minutes early."
        )


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@app.task(name="appointment.send_reminder", bind=True, max_retries=3, default_retry_delay=60)
def send_reminder(self, appointment_id: str, channel: str) -> dict:
    """Dispatch a T-24h (email) or T-2h (WhatsApp) reminder.

    Enqueued by appointment.api.book() with an explicit eta.
    """
    body = _render_reminder(appointment_id, channel)

    try:
        if channel == "email":
            from app.integrations.gmail_mcp import send as gmail_send
            # TODO: load patient email from DB; placeholder for hackathon
            result = gmail_send(
                to="patient@example.com",
                subject=f"Appointment Reminder — {appointment_id}",
                body_html=f"<p>{body}</p>",
            )
        elif channel == "telegram":
            from app.integrations.telegram import send as tg_send
            # TODO: load patient telegram chat_id from DB; uses TELEGRAM_CHAT_ID default
            result = tg_send(body=body)
        else:
            from app.integrations.whatsapp import send as wa_send
            # TODO: load patient phone from DB
            result = wa_send(to="+919999999999", body=body)

        log.info("tasks.reminder_sent", appt_id=appointment_id, channel=channel)
        return {"appointment_id": appointment_id, "channel": channel, "sent": True, **result}

    except Exception as exc:
        log.warning("tasks.reminder_failed", appt_id=appointment_id, channel=channel, exc=str(exc))
        raise self.retry(exc=exc)


@app.task(name="appointment.check_no_show", bind=True, max_retries=2, default_retry_delay=300)
def check_no_show(self, appointment_id: str, patient_phone: str) -> dict:
    """Fire 1h before slot: ask 'Are you still coming?'

    Enqueued by book() at slot - 1h. If no reply by slot start, mark_no_show fires.
    """
    try:
        from app.integrations.whatsapp import send as wa_send

        body = (
            f"Hi! Your appointment ({appointment_id}) is in about 1 hour. "
            "Reply *YES* to confirm, or *NO* to cancel and free the slot."
        )
        wa_send(to=patient_phone, body=body)
        log.info("tasks.no_show_check_sent", appt_id=appointment_id)

        # Mark no-show 65 min from now if patient doesn't reply
        mark_no_show.apply_async(args=[appointment_id], countdown=65 * 60)
        return {"appointment_id": appointment_id, "check_sent": True}

    except Exception as exc:
        raise self.retry(exc=exc)


@app.task(name="appointment.mark_no_show")
def mark_no_show(appointment_id: str) -> dict:
    """Mark the appointment no_show and trigger waitlist offer.

    Only fires if appointment is still CONFIRMED (i.e. patient didn't confirm).
    """
    log.info("tasks.marking_no_show", appt_id=appointment_id)
    # TODO: check DB status first — skip if patient already confirmed
    # TODO: update DB status to no_show
    offer_waitlist_slot.delay(appointment_id)
    return {"appointment_id": appointment_id, "status": "no_show"}


@app.task(name="appointment.offer_waitlist_slot")
def offer_waitlist_slot(freed_appointment_id: str) -> dict:
    """Pull top waitlist patient and offer them the freed slot via WhatsApp."""
    log.info("tasks.offer_waitlist", freed_appt=freed_appointment_id)
    # TODO: query DB for top waitlist entry for same doctor / time window
    # TODO: send WhatsApp offer with 30-min reply window, re-offer if no reply
    return {"freed_appointment_id": freed_appointment_id, "offered": False, "stub": True}


@app.task(name="appointment.post_discharge_followup", bind=True, max_retries=3, default_retry_delay=120)
def post_discharge_followup(self, patient_id: str, patient_phone: str = "+919999999999") -> dict:
    """72h post-discharge WhatsApp check-in, routed by clerical agent."""
    try:
        from app.integrations.whatsapp import send as wa_send
        from app.llm.router import complete

        prompt = (
            "Write a warm 72-hour post-discharge WhatsApp check-in for an Indian patient. "
            "Ask how they feel. Options: reply 1=I'm fine, 2=Need a callback, 3=New symptoms. "
            "Max 3 sentences. Language: Hinglish."
        )
        result = complete(
            task="reminder",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
        )
        wa_send(to=patient_phone, body=result.text.strip())

        log.info("tasks.post_discharge_followup_sent", patient_id=patient_id)
        return {"patient_id": patient_id, "sent": True}

    except Exception as exc:
        log.warning("tasks.post_discharge_followup_failed", patient_id=patient_id, exc=str(exc))
        raise self.retry(exc=exc)


@app.task(name="appointment.sweep_overdue_followups")
def sweep_overdue_followups() -> dict:
    """Sweep for discharges where 72h has passed but follow-up was not sent."""
    # TODO: query DB for discharges where discharge_time + 72h <= now AND no followup sent
    log.info("tasks.sweep_overdue_followups")
    return {"swept": 0, "stub": True}


# ---------------------------------------------------------------------------
# Beat schedule
# ---------------------------------------------------------------------------

app.conf.beat_schedule = {
    "sweep-overdue-followups": {
        "task": "appointment.sweep_overdue_followups",
        "schedule": crontab(hour="*/6"),  # every 6 hours
    },
}
