"""Wiki Maintenance Agent — public API. OWNER: Person A."""

from __future__ import annotations

from app.contracts import PatientWikiPageRef, SOAPNoteDraft, WikiLintReport


def update_patient_page(patient_id: str, draft: SOAPNoteDraft) -> PatientWikiPageRef:
    """Append today's encounter to the patient's wiki page; commit to wiki-history."""
    raise NotImplementedError("Person A — Day 4")


def get_patient_page(patient_id: str) -> str | None:
    """Return the raw markdown of the patient's wiki page, or None."""
    raise NotImplementedError("Person A — Day 1")


def lint_wiki() -> WikiLintReport:
    """Run the nightly lint pass (Day 8)."""
    raise NotImplementedError("Person A — Day 8")
