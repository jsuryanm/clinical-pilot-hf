"""Appointment router — OWNER: Person B."""

from __future__ import annotations

from fastapi import APIRouter

from app.agents.appointment.mocks import fake_booking
from app.contracts import BookingResult

router = APIRouter()


@router.post("/book", response_model=BookingResult)
def book(payload: dict) -> BookingResult:
    """TODO(Person B): replace with `app.agents.appointment.api.book(...)`."""
    return fake_booking(
        patient_id=payload.get("patient_id", "p-001"),
        doctor_id=payload.get("doctor_id", "d-001"),
    )


@router.post("/webhook/whatsapp")
def whatsapp_webhook(payload: dict) -> dict:
    """Twilio sandbox webhook.

    TODO(Person B): parse Twilio body, route into appointment agent.
    """
    return {"received": True, "echo": payload}
