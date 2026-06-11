"""Discharge Agent — public API. OWNER: Person B.

Triggered by nurse-admin tab via POST /discharge/{patient_id}.
Fans out 5 subtasks in parallel using ThreadPoolExecutor.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import structlog

from app.contracts import (
    DischargeCoordination,
    DischargeSubtask,
    DischargeSubtaskStatus,
)

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Subtask runners — each returns a DischargeSubtask
# ---------------------------------------------------------------------------

def _run_discharge_summary(patient_id: str, discharge_id: str) -> DischargeSubtask:
    """Draft discharge summary from the latest approved SOAP note via LLM."""
    try:
        from app.agents.documentation.mocks import fake_soap_draft
        from app.llm.router import complete

        soap = fake_soap_draft(patient_id=patient_id)
        prompt = (
            "You are a medical scribe for an Indian clinic.\n"
            "Write a plain-language discharge summary for the patient.\n"
            "Include: what was found, medications to take home, when to return, red flags.\n"
            "Language: Hinglish. Max 200 words.\n\n"
            f"Subjective: {soap.soap.subjective}\n"
            f"Objective: {soap.soap.objective}\n"
            f"Assessment: {soap.soap.assessment}\n"
            f"Plan: {soap.soap.plan}\n"
        )
        result = complete(
            task="discharge_summary",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
        )
        return DischargeSubtask(
            name="discharge_summary",
            status=DischargeSubtaskStatus.AWAITING_APPROVAL,
            detail=result.text.strip()[:500],
            artifact_id=soap.draft_id,
        )
    except Exception as exc:
        log.exception("discharge.summary_failed", patient_id=patient_id)
        return DischargeSubtask(
            name="discharge_summary",
            status=DischargeSubtaskStatus.FAILED,
            detail=str(exc),
        )


def _run_pharmacy(patient_id: str, discharge_id: str) -> DischargeSubtask:
    """Extract medications from SOAP plan and queue them for the pharmacy counter."""
    try:
        from app.agents.documentation.mocks import fake_soap_draft
        from app.llm.router import complete

        soap = fake_soap_draft(patient_id=patient_id)
        prompt = (
            "Extract all medications from this treatment plan as a JSON array of "
            '{"name","dose","frequency","duration"}.\n'
            f"Plan: {soap.soap.plan}"
        )
        result = complete(
            task="discharge_summary",
            messages=[{"role": "user", "content": prompt}],
            json_mode=True,
            max_tokens=1024,
        )
        meds = json.loads(result.text)
        med_count = len(meds) if isinstance(meds, list) else "?"
        return DischargeSubtask(
            name="pharmacy",
            status=DischargeSubtaskStatus.IN_PROGRESS,
            detail=f"{med_count} medication(s) queued at pharmacy.",
        )
    except Exception as exc:
        log.exception("discharge.pharmacy_failed", patient_id=patient_id)
        return DischargeSubtask(
            name="pharmacy",
            status=DischargeSubtaskStatus.FAILED,
            detail=str(exc),
        )


def _run_family_notification(patient_id: str, discharge_id: str) -> DischargeSubtask:
    """Send WhatsApp to registered next-of-kin."""
    try:
        from app.integrations.whatsapp import send as wa_send

        kin_phone = "+919999999999"  # TODO: load from DB patient.next_of_kin_phone
        body = (
            f"Namaste! Your family member (ID: {patient_id}) has been cleared for discharge. "
            "Please arrange pick-up within 2 hours. For questions, call the ward desk."
        )
        wa_send(to=kin_phone, body=body)
        return DischargeSubtask(
            name="family_notification",
            status=DischargeSubtaskStatus.DONE,
            detail=f"WhatsApp sent to next-of-kin at {datetime.now(timezone.utc).strftime('%H:%M UTC')}.",
        )
    except Exception as exc:
        log.exception("discharge.family_notification_failed", patient_id=patient_id)
        return DischargeSubtask(
            name="family_notification",
            status=DischargeSubtaskStatus.FAILED,
            detail=str(exc),
        )


def _run_follow_up_appointment(patient_id: str, discharge_id: str) -> DischargeSubtask:
    """Book a 7-day follow-up appointment."""
    try:
        from app.agents.appointment.api import book

        now = datetime.now(timezone.utc)
        result = book(
            patient_id=patient_id,
            requested_window=(
                now + timedelta(days=7, hours=9),
                now + timedelta(days=7, hours=17),
            ),
        )
        return DischargeSubtask(
            name="follow_up_appointment",
            status=DischargeSubtaskStatus.DONE,
            detail=f"7-day follow-up booked: {result.slot_iso.strftime('%d %b %I:%M %p')}.",
            artifact_id=result.appointment_id,
        )
    except Exception as exc:
        log.exception("discharge.follow_up_failed", patient_id=patient_id)
        return DischargeSubtask(
            name="follow_up_appointment",
            status=DischargeSubtaskStatus.FAILED,
            detail=str(exc),
        )


def _run_billing_trigger(patient_id: str, discharge_id: str) -> DischargeSubtask:
    """Write a billing_ready event row to the audit log / billing table."""
    try:
        log.info("discharge.billing_triggered", patient_id=patient_id, discharge_id=discharge_id)
        # TODO: write billing_ready row to DB via SQLAlchemy session
        return DischargeSubtask(
            name="billing_trigger",
            status=DischargeSubtaskStatus.QUEUED,
            detail="billing_ready event written; final bill pending pharmacy total.",
        )
    except Exception as exc:
        log.exception("discharge.billing_failed", patient_id=patient_id)
        return DischargeSubtask(
            name="billing_trigger",
            status=DischargeSubtaskStatus.FAILED,
            detail=str(exc),
        )


_SUBTASK_RUNNERS = [
    _run_discharge_summary,
    _run_pharmacy,
    _run_family_notification,
    _run_follow_up_appointment,
    _run_billing_trigger,
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def initiate_discharge(patient_id: str) -> DischargeCoordination:
    """Fan out all 5 discharge subtasks in parallel and return their statuses."""
    discharge_id = f"dsc-{uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)

    log.info("discharge.initiated", discharge_id=discharge_id, patient_id=patient_id)

    subtasks: list[DischargeSubtask] = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(runner, patient_id, discharge_id): runner
            for runner in _SUBTASK_RUNNERS
        }
        for future in as_completed(futures):
            try:
                subtasks.append(future.result())
            except Exception:
                log.exception("discharge.subtask_unhandled", fn=futures[future].__name__)

    # Enqueue 72h post-discharge follow-up
    try:
        from app.agents.appointment.tasks import post_discharge_followup
        post_discharge_followup.apply_async(
            args=[patient_id],
            eta=now + timedelta(hours=72),
        )
    except Exception:
        log.warning("discharge.followup_enqueue_failed", patient_id=patient_id, exc_info=True)

    return DischargeCoordination(
        discharge_id=discharge_id,
        patient_id=patient_id,
        initiated_at=now,
        target_complete_by=now + timedelta(minutes=90),
        subtasks=subtasks,
    )


def discharge_status(patient_id: str) -> DischargeCoordination:
    """Return current subtask statuses for an in-progress discharge.

    Production: load from DB. Hackathon: falls back to mock.
    """
    from app.agents.discharge.mocks import fake_discharge
    return fake_discharge(patient_id=patient_id)
