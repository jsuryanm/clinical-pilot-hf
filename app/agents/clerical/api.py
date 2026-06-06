"""Clerical Agent — public API. OWNER: Person B."""

from __future__ import annotations

import json
from typing import Literal
from uuid import uuid4

import structlog

from app.contracts import Channel, CommunicationDraft
from app.llm.router import complete

log = structlog.get_logger(__name__)


_REFERRAL_PROMPT = """You are a medical scribe drafting a specialist referral letter for an Indian clinic.

Referring doctor: Dr. Sharma
Patient SOAP summary: {soap_summary}
Receiving specialist: {receiving_specialist}

Write a concise professional referral letter (max 150 words) including:
- Reason for referral
- Key clinical findings (from assessment/plan)
- Specific questions for the specialist
- Relevant medications

End with "Regards, Dr. Sharma"
"""

_CLASSIFY_PROMPT = """You are a triage assistant for an Indian clinic's post-discharge follow-up system.

Classify the patient's reply into exactly one of:
  reassuring               — patient is doing well, no concerns
  needs_review             — some concern but not urgent; doctor should review within 24h
  needs_urgent_callback    — urgent symptoms; doctor must call back immediately

Return JSON: {{"classification": "<one of above>", "reason": "<one sentence>"}}

Context: {context}
Patient reply: {message}
"""


def draft_referral(soap_id: str, receiving_specialist: str) -> CommunicationDraft:
    """Draft a referral letter from a SOAP note for the receiving specialist.

    Placed in doctor's approval queue — never auto-sent.
    """
    try:
        from app.agents.documentation.mocks import fake_soap_draft
        soap = fake_soap_draft()
        soap_summary = f"Assessment: {soap.soap.assessment}\nPlan: {soap.soap.plan}"
    except Exception:
        soap_summary = f"SOAP ID: {soap_id} (details unavailable)"

    result = complete(
        task="referral_letter",
        messages=[{
            "role": "user",
            "content": _REFERRAL_PROMPT.format(
                soap_summary=soap_summary,
                receiving_specialist=receiving_specialist,
            ),
        }],
        max_tokens=400,
    )

    log.info("clerical.referral_drafted", soap_id=soap_id, to=receiving_specialist)
    return CommunicationDraft(
        draft_id=f"ref-{uuid4().hex[:8]}",
        channel=Channel.EMAIL,
        to=f"{receiving_specialist.lower().replace(' ', '.')}@hospital.example.org",
        subject=f"Referral — {receiving_specialist} — SOAP {soap_id}",
        body=result.text.strip(),
        requires_approval=True,
        related_patient_id=None,
    )


def classify_inbound_reply(
    message: str,
    context: dict,
) -> Literal["reassuring", "needs_review", "needs_urgent_callback"]:
    """Classify a post-discharge patient reply for routing.

    Returns 'needs_review' on any failure — always err on the side of escalation.
    """
    try:
        result = complete(
            task="classify_reply",
            messages=[{
                "role": "user",
                "content": _CLASSIFY_PROMPT.format(
                    message=message,
                    context=json.dumps(context, ensure_ascii=False),
                ),
            }],
            json_mode=True,
            max_tokens=100,
        )
        data = json.loads(result.text)
        classification = data.get("classification", "needs_review")
        if classification not in ("reassuring", "needs_review", "needs_urgent_callback"):
            classification = "needs_review"
        log.info(
            "clerical.reply_classified",
            classification=classification,
            reason=data.get("reason", ""),
        )
        return classification  # type: ignore[return-value]

    except Exception:
        log.exception("clerical.classify_failed", message=message[:80])
        return "needs_review"
