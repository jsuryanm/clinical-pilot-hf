"""Fake Clerical Agent output. OWNER: Person B."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app.contracts import Channel, CommunicationDraft


def fake_referral_letter(patient_id: str = "p-001") -> CommunicationDraft:
    return CommunicationDraft(
        draft_id=f"ref-{uuid4().hex[:8]}",
        channel=Channel.EMAIL,
        to="cardiology.dept@example.org",
        subject="Referral — Patient p-001 — uncontrolled HTN",
        body=(
            "Dear Cardiology team,\n\n"
            "Referring 52M, known hypertensive, BP 162/98 today despite increased "
            "amlodipine. Requesting your opinion regarding workup for secondary causes "
            "and add-on management. SOAP note and BP log attached.\n\n"
            "Regards,\nDr. Sharma"
        ),
        requires_approval=True,
        related_patient_id=patient_id,
    )


def fake_post_discharge_followup(patient_id: str = "p-001") -> CommunicationDraft:
    return CommunicationDraft(
        draft_id=f"pdf-{uuid4().hex[:8]}",
        channel=Channel.WHATSAPP,
        to="+91-98XXXXXX01",
        body=(
            "Hello! 3 days since your discharge — how are you feeling? Reply 1 if "
            "everything is fine, 2 if you'd like a doctor to call you, 3 for any new "
            "symptoms. Sent ts: " + datetime.now(timezone.utc).isoformat(timespec="minutes")
        ),
        requires_approval=False,
        related_patient_id=patient_id,
    )
