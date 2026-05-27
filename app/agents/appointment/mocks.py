"""Fake Appointment Agent output.

OWNER: Person B — replace with the real agent on Day 2.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.contracts import (
    BookingResult,
    BookingStatus,
    Channel,
    CommunicationDraft,
    ReminderJob,
)


def fake_booking(patient_id: str = "p-001", doctor_id: str = "d-001") -> BookingResult:
    slot = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=2, hours=3)
    appt_id = f"appt-{uuid4().hex[:8]}"
    return BookingResult(
        appointment_id=appt_id,
        patient_id=patient_id,
        doctor_id=doctor_id,
        slot_iso=slot,
        duration_minutes=15,
        status=BookingStatus.CONFIRMED,
        confirmation_sent_at=datetime.now(timezone.utc),
        reminder_jobs=[
            ReminderJob(
                job_id=f"rem-{uuid4().hex[:6]}",
                channel=Channel.EMAIL,
                fire_at=slot - timedelta(hours=24),
                enqueued=True,
            ),
            ReminderJob(
                job_id=f"rem-{uuid4().hex[:6]}",
                channel=Channel.WHATSAPP,
                fire_at=slot - timedelta(hours=2),
                enqueued=True,
            ),
        ],
        calendar_event_id="gcal-stub-001",
        notes="Booked from WhatsApp inbound; preferred OPD-2.",
    )


def fake_communication(patient_id: str = "p-001") -> CommunicationDraft:
    return CommunicationDraft(
        draft_id=f"comm-{uuid4().hex[:8]}",
        channel=Channel.WHATSAPP,
        to="+91-98XXXXXX01",
        body=(
            "Namaste! Your appointment with Dr. Sharma is confirmed for "
            "Friday at 3:00 PM. Reply 1 to confirm, 2 to reschedule."
        ),
        requires_approval=False,
        related_patient_id=patient_id,
    )
