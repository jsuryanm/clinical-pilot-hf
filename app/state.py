"""LangGraph shared state.

Update rules (enforced by reducers below):
  * list fields always APPEND
  * scalar fields always OVERWRITE
  * no node mutates state directly — each returns only the fields it changes
"""

from __future__ import annotations

import operator
from datetime import datetime
from typing import Annotated, TypedDict

from app.contracts import (
    AgentError,
    BookingResult,
    CommunicationDraft,
    DischargeCoordination,
    HandoverBrief,
    PatientWikiPageRef,
    RosterResult,
    RoutingDecision,
    SOAPNoteDraft,
    TaskType,
)

# ---------------------------------------------------------------------------
# Reducers
# ---------------------------------------------------------------------------


def merge_messages(left: list[dict], right: list[dict]) -> list[dict]:
    """Conversation history is append-only."""
    return [*left, *right]


def overwrite_if_set(left, right):
    """Scalar overwrite — but None never clobbers an existing value."""
    return right if right is not None else left


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------


class CliniqState(TypedDict, total=False):
    # --- session bookkeeping ---
    session_id: str
    timestamp: datetime
    task_type: TaskType | None
    current_agent: str | None

    # --- conversation history (append-only) ---
    messages: Annotated[list[dict], merge_messages]

    # --- per-agent sub-state (overwrite on update) ---
    routing: RoutingDecision | None
    soap_draft: SOAPNoteDraft | None
    booking: BookingResult | None
    roster: RosterResult | None
    handover: HandoverBrief | None
    discharge: DischargeCoordination | None
    communication: CommunicationDraft | None
    wiki_ref: PatientWikiPageRef | None

    # --- retrieval scratch (append-only list of doc_ids) ---
    retrieved_guidelines: Annotated[list[str], operator.add]
    sent_communications: Annotated[list[str], operator.add]

    # --- error / escalation ---
    error: AgentError | None
    escalation_required: bool
    escalation_reason: str | None


def new_state(session_id: str) -> CliniqState:
    """Build an empty state for a new workflow run."""
    return CliniqState(
        session_id=session_id,
        timestamp=datetime.utcnow(),
        task_type=None,
        current_agent=None,
        messages=[],
        routing=None,
        soap_draft=None,
        booking=None,
        roster=None,
        handover=None,
        discharge=None,
        communication=None,
        wiki_ref=None,
        retrieved_guidelines=[],
        sent_communications=[],
        error=None,
        escalation_required=False,
        escalation_reason=None,
    )
