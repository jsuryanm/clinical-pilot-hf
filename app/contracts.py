"""Shared Pydantic contracts — the team interface between A, B, and C.

RULES
-----
1. Field names are **frozen** as of Day 0. Additive changes only.
2. If you must change a field, post in the team channel; others have 24h to ack.
3. Every agent returns one of these models — no dicts, no strings.
4. This file is the only one we type-check with `mypy --strict`.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# Common / shared
# ---------------------------------------------------------------------------


class StrictModel(BaseModel):
    """Base class that forbids extra fields and freezes instances."""

    model_config = ConfigDict(extra="forbid", frozen=False, populate_by_name=True)


class TaskType(str, Enum):
    DOCUMENTATION = "documentation"
    APPOINTMENT = "appointment"
    ROSTER = "roster"
    HANDOVER = "handover"
    DISCHARGE = "discharge"
    CLERICAL = "clerical"
    WIKI_MAINT = "wiki_maintenance"


class Channel(str, Enum):
    WHATSAPP = "whatsapp"
    WEB = "web"
    EMAIL = "email"
    PHONE = "phone"
    TELEGRAM = "telegram"  # additive (Person A) — bot-based notifications


class Priority(str, Enum):
    STABLE = "stable"
    WATCH = "watch"
    URGENT = "urgent"


class Citation(StrictModel):
    """A pointer back to a wiki page, guideline, or retrieval hit. Required on
    every clinically-significant output for the audit trail."""

    source_type: Literal["wiki", "guideline", "icd10", "drug_db", "lab", "soap"]
    source_id: str
    title: str | None = None
    url: str | None = None
    snippet: str | None = None


class Hit(StrictModel):
    """A search hit from the retrieval layer (Chroma + BM25 hybrid)."""

    doc_id: str
    text: str
    score: float
    source: Literal["chroma", "bm25", "hybrid"]
    metadata: dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Wiki refs (Person A owns the wiki; A and B both read)
# ---------------------------------------------------------------------------


class PatientWikiPageRef(StrictModel):
    patient_id: str
    page_path: str  # e.g. "wiki/patients/p-001.md"
    version: str  # git sha or content hash
    last_updated: datetime


class WikiLintIssue(StrictModel):
    page_path: str
    kind: Literal["missing_field", "contradiction", "stale", "broken_xref"]
    detail: str


class WikiLintReport(StrictModel):
    generated_at: datetime
    issues: list[WikiLintIssue] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Documentation (Person A returns this)
# ---------------------------------------------------------------------------


class SOAPSection(StrictModel):
    subjective: str
    objective: str
    assessment: str
    plan: str


class ICD10Suggestion(StrictModel):
    code: str
    label: str
    confidence: float = Field(ge=0.0, le=1.0)


class SOAPNoteDraft(StrictModel):
    draft_id: str
    patient_id: str
    encounter_ts: datetime
    soap: SOAPSection
    icd10_suggestions: list[ICD10Suggestion] = Field(default_factory=list)
    guideline_suggestions: list[str] = Field(default_factory=list)
    sources: list[Citation] = Field(default_factory=list)
    referral_needed: bool = False
    confidence_overall: float = Field(ge=0.0, le=1.0, default=0.0)
    transcript_excerpt: str | None = None
    model: str  # e.g. "groq/qwen3-32b"


# ---------------------------------------------------------------------------
# Appointments (Person B returns this)
# ---------------------------------------------------------------------------


class BookingStatus(str, Enum):
    PROPOSED = "proposed"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    COMPLETED = "completed"
    WAITLISTED = "waitlisted"


class ReminderJob(StrictModel):
    job_id: str
    channel: Channel
    fire_at: datetime
    enqueued: bool = False


class BookingResult(StrictModel):
    appointment_id: str
    patient_id: str
    doctor_id: str
    slot_iso: datetime
    duration_minutes: int = 15
    status: BookingStatus
    confirmation_sent_at: datetime | None = None
    reminder_jobs: list[ReminderJob] = Field(default_factory=list)
    calendar_event_id: str | None = None
    notes: str | None = None


class CommunicationDraft(StrictModel):
    """Outbound message awaiting approval (or already sent if `sent_at` set)."""

    draft_id: str
    channel: Channel
    to: str  # phone number, email, etc
    subject: str | None = None
    body: str
    requires_approval: bool = True
    approved_by: str | None = None
    sent_at: datetime | None = None
    related_patient_id: str | None = None
    related_appointment_id: str | None = None


# ---------------------------------------------------------------------------
# Discharge (Person B returns this)
# ---------------------------------------------------------------------------


class DischargeSubtaskStatus(str, Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
    AWAITING_APPROVAL = "awaiting_approval"


class DischargeSubtask(StrictModel):
    name: Literal[
        "discharge_summary",
        "pharmacy",
        "family_notification",
        "follow_up_appointment",
        "billing_trigger",
    ]
    status: DischargeSubtaskStatus
    detail: str | None = None
    artifact_id: str | None = None  # FK back to SOAP draft, booking, etc.


class DischargeCoordination(StrictModel):
    discharge_id: str
    patient_id: str
    initiated_at: datetime
    subtasks: list[DischargeSubtask]
    target_complete_by: datetime
    completed_at: datetime | None = None


# ---------------------------------------------------------------------------
# Rostering (Person C returns this)
# ---------------------------------------------------------------------------


class ShiftAssignment(StrictModel):
    shift_id: str
    staff_id: str
    role: Literal["doctor", "nurse", "tech", "admin"]
    start: datetime
    end: datetime
    is_replacement: bool = False


class RosterResult(StrictModel):
    roster_id: str
    window_start: datetime
    window_end: datetime
    assignments: list[ShiftAssignment]
    fairness_score: float = Field(ge=0.0, le=1.0)  # higher is fairer
    unresolved_conflicts: list[str] = Field(default_factory=list)
    generated_in_seconds: float


# ---------------------------------------------------------------------------
# Handover (Person C returns this)
# ---------------------------------------------------------------------------


class PatientBrief(StrictModel):
    patient_id: str
    bed: str | None = None
    priority: Priority
    one_liner: str  # ≤ 160 chars
    actions_pending: list[str] = Field(default_factory=list)
    sources: list[Citation] = Field(default_factory=list)


class HandoverBrief(StrictModel):
    brief_id: str
    ward_id: str
    shift_end_ts: datetime
    patients: list[PatientBrief]  # ordered urgent → stable
    estimated_read_minutes: int


# ---------------------------------------------------------------------------
# Orchestrator routing (Person C returns this)
# ---------------------------------------------------------------------------


class RoutingDecision(StrictModel):
    task: TaskType
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str
    escalate: bool = False


# ---------------------------------------------------------------------------
# Error / escalation surface shared across all agents
# ---------------------------------------------------------------------------


class AgentError(StrictModel):
    agent: str
    code: str  # e.g. "llm_timeout", "calendar_conflict"
    message: str
    recoverable: bool = True


__all__ = [
    # enums
    "TaskType",
    "Channel",
    "Priority",
    "BookingStatus",
    "DischargeSubtaskStatus",
    # base
    "StrictModel",
    "Citation",
    "Hit",
    # wiki
    "PatientWikiPageRef",
    "WikiLintIssue",
    "WikiLintReport",
    # documentation
    "SOAPSection",
    "ICD10Suggestion",
    "SOAPNoteDraft",
    # appointments + comms
    "ReminderJob",
    "BookingResult",
    "CommunicationDraft",
    # discharge
    "DischargeSubtask",
    "DischargeCoordination",
    # roster
    "ShiftAssignment",
    "RosterResult",
    # handover
    "PatientBrief",
    "HandoverBrief",
    # orchestrator
    "RoutingDecision",
    # error
    "AgentError",
]
