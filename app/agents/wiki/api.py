"""Wiki Maintenance Agent — public API. OWNER: Person A.

For the hackathon only the patient-page read/write path is wired (Day 4). The
lint pass (``lint_wiki``) stays a stub — it is post-hackathon scope.

Patient pages live under ``wiki/patients/`` (gitignored — synthetic only). On
every approved encounter we:

1. append the encounter to the patient's markdown page (creating a schema-
   compliant skeleton on first write), and
2. append an audit record to ``data/wiki_history/<patient_id>.jsonl`` — the
   clinical audit trail (we keep PHI out of git, so the trail is a local,
   gitignored append-only log rather than a ``wiki-history`` git branch).
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import structlog

from app.contracts import PatientWikiPageRef, SOAPNoteDraft, WikiLintReport

log = structlog.get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _wiki_root() -> Path:
    """Wiki root. Override with ``CLINIQ_WIKI_DIR`` (tests point it at a tmp dir)."""
    return Path(os.getenv("CLINIQ_WIKI_DIR", str(_REPO_ROOT / "wiki")))


def _history_dir() -> Path:
    return Path(os.getenv("CLINIQ_WIKI_HISTORY_DIR", str(_REPO_ROOT / "data" / "wiki_history")))


def _patient_path(patient_id: str) -> Path:
    return _wiki_root() / "patients" / f"{patient_id}.md"


def get_patient_page(patient_id: str) -> str | None:
    """Return the raw markdown of the patient's wiki page, or None if absent."""
    path = _patient_path(patient_id)
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def _skeleton(patient_id: str, now: datetime) -> str:
    """Schema-compliant empty patient page (see wiki/README.md required sections)."""
    return (
        "---\n"
        "type: patient\n"
        f"id: {patient_id}\n"
        f"title: Patient {patient_id}\n"
        f"last_updated: {now.date().isoformat()}\n"
        "---\n\n"
        f"# Patient {patient_id}\n\n"
        "## Demographics\n\n_Not recorded._\n\n"
        "## Active Problems\n\n_None recorded._\n\n"
        "## Medications\n\n_None recorded._\n\n"
        "## Allergies\n\n_None recorded._\n\n"
        "## Encounter History\n\n"
    )


def _encounter_block(draft: SOAPNoteDraft, now: datetime) -> str:
    """Render one Encounter History entry from an approved SOAP draft."""
    icd = ", ".join(f"{s.code} ({s.label})" for s in draft.icd10_suggestions) or "—"
    srcs = ", ".join(f"`{c.source_type}:{c.source_id}`" for c in draft.sources) or "—"
    return (
        f"### {now.date().isoformat()} — encounter {draft.draft_id}\n\n"
        f"- **Subjective:** {draft.soap.subjective}\n"
        f"- **Objective:** {draft.soap.objective}\n"
        f"- **Assessment:** {draft.soap.assessment}\n"
        f"- **Plan:** {draft.soap.plan}\n"
        f"- **ICD-10:** {icd}\n"
        f"- **Sources:** {srcs}\n"
        f"- **Model:** {draft.model} (confidence {draft.confidence_overall:.2f})\n\n"
    )


def update_patient_page(patient_id: str, draft: SOAPNoteDraft) -> PatientWikiPageRef:
    """Append today's encounter to the patient's wiki page; record an audit entry."""
    now = datetime.now(timezone.utc)
    path = _patient_path(patient_id)
    path.parent.mkdir(parents=True, exist_ok=True)

    content = path.read_text(encoding="utf-8") if path.exists() else _skeleton(patient_id, now)
    content = content.rstrip() + "\n\n" + _encounter_block(draft, now)
    path.write_text(content, encoding="utf-8")

    version = hashlib.sha1(content.encode("utf-8")).hexdigest()[:12]
    _append_audit(patient_id, draft, version, now)

    try:
        page_path = str(path.relative_to(_REPO_ROOT))
    except ValueError:  # wiki dir overridden outside the repo (e.g. tests)
        page_path = str(path)

    log.info("wiki.patient_page_updated", patient_id=patient_id, version=version)
    return PatientWikiPageRef(
        patient_id=patient_id,
        page_path=page_path,
        version=version,
        last_updated=now,
    )


def _append_audit(
    patient_id: str, draft: SOAPNoteDraft, version: str, now: datetime
) -> None:
    """Append an immutable audit record (best-effort — never breaks the write)."""
    try:
        history_dir = _history_dir()
        history_dir.mkdir(parents=True, exist_ok=True)
        record = {
            "ts": now.isoformat(),
            "patient_id": patient_id,
            "draft_id": draft.draft_id,
            "version": version,
            "model": draft.model,
            "sources": [f"{c.source_type}:{c.source_id}" for c in draft.sources],
        }
        with (history_dir / f"{patient_id}.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")
    except Exception:  # noqa: BLE001 — audit logging must never break the encounter
        log.warning("wiki.audit_append_failed", patient_id=patient_id, exc_info=True)


def lint_wiki() -> WikiLintReport:
    """Run the nightly lint pass (post-hackathon — stub)."""
    raise NotImplementedError("Person A — post-hackathon")
