"""Appointment Agent — public API. OWNER: Person B."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from app.contracts import BookingResult, CommunicationDraft


def handle_inbound_message(channel: Literal["whatsapp", "web"], payload: dict) -> CommunicationDraft:
    """Parse an inbound message, decide what to do, draft a reply."""
    raise NotImplementedError("Person B — Day 2")


def book(
    patient_id: str,
    requested_window: tuple[datetime, datetime],
    doctor_id: str | None = None,
) -> BookingResult:
    raise NotImplementedError("Person B — Day 2")


def cancel(appointment_id: str, reason: str) -> BookingResult:
    raise NotImplementedError("Person B — Day 3")
