"""Appointment router — OWNER: Person B."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Request

from app.agents.appointment import api as appt_api
from app.contracts import BookingResult, CommunicationDraft

router = APIRouter()


@router.post("/book", response_model=BookingResult)
def book(payload: dict) -> BookingResult:
    """Book an appointment.

    Body: {patient_id, doctor_id (optional), window_start_iso, window_end_iso}
    """
    patient_id = payload.get("patient_id", "p-001")
    doctor_id = payload.get("doctor_id")
    try:
        w_start = datetime.fromisoformat(payload["window_start_iso"]).replace(tzinfo=timezone.utc)
        w_end = datetime.fromisoformat(payload["window_end_iso"]).replace(tzinfo=timezone.utc)
    except (KeyError, ValueError):
        now = datetime.now(timezone.utc)
        w_start = now + timedelta(days=1, hours=9)
        w_end = now + timedelta(days=8, hours=17)

    return appt_api.book(
        patient_id=patient_id,
        requested_window=(w_start, w_end),
        doctor_id=doctor_id,
    )


@router.post("/cancel", response_model=BookingResult)
def cancel(payload: dict) -> BookingResult:
    """Cancel an appointment. Body: {appointment_id, reason}"""
    appointment_id = payload.get("appointment_id", "")
    if not appointment_id:
        raise HTTPException(status_code=422, detail="appointment_id is required")
    return appt_api.cancel(appointment_id, reason=payload.get("reason", "patient request"))


@router.post("/webhook/whatsapp", response_model=CommunicationDraft)
async def whatsapp_webhook(request: Request) -> CommunicationDraft:
    """Twilio inbound webhook (form-encoded POST).

    Parses Twilio's payload, routes into the appointment agent, and echoes the reply
    back to the patient via Twilio (best-effort — webhook always returns 200).
    """
    from app.integrations.whatsapp import parse_inbound

    form_data = await request.form()
    parsed = parse_inbound(dict(form_data))
    draft = appt_api.handle_inbound_message(channel="whatsapp", payload=parsed)

    try:
        from app.integrations.whatsapp import send as wa_send
        wa_send(to=parsed["from"], body=draft.body)
    except Exception:
        pass  # reply failure must not break the webhook response

    return draft


@router.post("/inbound", response_model=CommunicationDraft)
def web_inbound(payload: dict) -> CommunicationDraft:
    """Web / simulator inbound — used by patient_tab.py and tests/wa_sim.py."""
    return appt_api.handle_inbound_message(channel="web", payload=payload)
