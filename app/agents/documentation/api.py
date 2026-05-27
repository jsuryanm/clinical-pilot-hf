"""Documentation Agent — public API. OWNER: Person A."""

from __future__ import annotations

from pathlib import Path

from app.contracts import PatientWikiPageRef, SOAPNoteDraft


def draft_soap(
    *,
    patient_id: str,
    audio_path: Path | None = None,
    transcript: str | None = None,
) -> SOAPNoteDraft:
    """Build a SOAP note draft from audio or a transcript.

    Day 3 deliverable for Person A. Pipeline:
        transcript -> retrieve wiki + guidelines + ICD-10 -> Qwen3-32B -> validate
    """
    raise NotImplementedError("Person A — Day 3")


def approve_draft(draft: SOAPNoteDraft, edits: dict | None = None) -> PatientWikiPageRef:
    """Persist a SOAP draft, update the patient wiki page, return its ref."""
    raise NotImplementedError("Person A — Day 4")
