"""Wiki Maintenance Agent — public API. OWNER: Person A.

Two wired paths:

1. **Patient page read/write** (Day 4). On every approved encounter we append
   the encounter to the patient's markdown page (creating a schema-compliant
   skeleton on first write) and append an audit record to
   ``data/wiki_history/<patient_id>.jsonl`` — the clinical audit trail (we keep
   PHI out of git, so the trail is a local, gitignored append-only log rather
   than a ``wiki-history`` git branch). Patient pages live under
   ``wiki/patients/`` (gitignored — synthetic only).

2. **Lint pass** (``lint_wiki``) over the public corpus (conditions / drugs /
   protocols): missing required frontmatter fields, broken ``[[folder/id]]``
   cross-refs, and stale pages (``last_updated`` older than 180 days).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import structlog

from app.contracts import PatientWikiPageRef, SOAPNoteDraft, WikiLintIssue, WikiLintReport

log = structlog.get_logger(__name__)

_XREF_RE = re.compile(r"\[\[([a-z0-9_\-]+/[a-z0-9_\-]+)\]\]")
_STALE_AFTER_DAYS = 180
# Required frontmatter fields by page type (patient pages are excluded from lint).
_REQUIRED_FIELDS = {
    "condition": ("type", "id", "title", "last_updated", "source"),
    "drug": ("type", "id", "title", "last_updated", "source"),
    "protocol": ("type", "id", "title", "last_updated"),
}
_LINT_FOLDERS = ("conditions", "drugs", "protocols")

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


def _parse_frontmatter(raw: str) -> dict[str, str]:
    """Minimal YAML-frontmatter parser (flat scalar keys only)."""
    if not raw.startswith("---"):
        return {}
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" in line and not line.lstrip().startswith("-"):
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()
    return meta


def _page_exists(wiki_root: Path, ref: str) -> bool:
    return (wiki_root / f"{ref}.md").exists()


def lint_wiki() -> WikiLintReport:
    """Lint the public wiki corpus (conditions / drugs / protocols).

    Flags missing required frontmatter fields, broken ``[[folder/id]]``
    cross-refs, and stale pages (``last_updated`` older than 180 days).
    Patient pages are excluded (PHI / gitignored).
    """
    now = datetime.now(timezone.utc)
    wiki_root = _wiki_root()
    issues: list[WikiLintIssue] = []

    for folder in _LINT_FOLDERS:
        for path in sorted((wiki_root / folder).glob("*.md")):
            rel = f"{folder}/{path.stem}"
            raw = path.read_text(encoding="utf-8")
            meta = _parse_frontmatter(raw)
            ptype = meta.get("type", folder.rstrip("s"))

            # missing required fields
            for field in _REQUIRED_FIELDS.get(ptype, ("type", "id", "title", "last_updated")):
                if not meta.get(field):
                    issues.append(WikiLintIssue(
                        page_path=rel, kind="missing_field",
                        detail=f"missing required frontmatter field '{field}'",
                    ))

            # stale page
            last = meta.get("last_updated", "")
            try:
                updated = datetime.fromisoformat(last).replace(tzinfo=timezone.utc)
                if now - updated > timedelta(days=_STALE_AFTER_DAYS):
                    issues.append(WikiLintIssue(
                        page_path=rel, kind="stale",
                        detail=f"last_updated {last} is older than {_STALE_AFTER_DAYS} days",
                    ))
            except ValueError:
                issues.append(WikiLintIssue(
                    page_path=rel, kind="missing_field",
                    detail=f"unparseable last_updated: {last!r}",
                ))

            # broken cross-refs
            for ref in _XREF_RE.findall(raw):
                if not _page_exists(wiki_root, ref):
                    issues.append(WikiLintIssue(
                        page_path=rel, kind="broken_xref",
                        detail=f"cross-ref [[{ref}]] has no target page",
                    ))

    log.info("wiki.lint_done", n_issues=len(issues))
    return WikiLintReport(generated_at=now, issues=issues)
