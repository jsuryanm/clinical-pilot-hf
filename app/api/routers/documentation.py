"""Documentation router — OWNER: Person A.

Wires Whisper + Documentation Agent to HTTP. Until A's real agent lands,
endpoints return the mock so the UI can render against realistic data.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.agents.documentation.mocks import fake_soap_draft
from app.contracts import SOAPNoteDraft

router = APIRouter()


@router.post("/draft", response_model=SOAPNoteDraft)
def draft(payload: dict) -> SOAPNoteDraft:
    """Generate a SOAP note draft from audio or transcript.

    TODO(Person A): replace mock with `app.agents.documentation.api.draft_soap(...)`.
    Expected payload: { patient_id: str, audio_b64?: str, transcript?: str }.
    """
    patient_id = payload.get("patient_id", "p-001")
    return fake_soap_draft(patient_id=patient_id)


@router.post("/approve", response_model=SOAPNoteDraft)
def approve(payload: dict) -> SOAPNoteDraft:
    """Approve (or edit-and-approve) a SOAP draft. Writes to wiki + DB.

    TODO(Person A): persist to soap_drafts + update patient wiki page.
    """
    return fake_soap_draft(patient_id=payload.get("patient_id", "p-001"))
