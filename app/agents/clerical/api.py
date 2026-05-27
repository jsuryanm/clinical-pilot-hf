"""Clerical Agent — public API. OWNER: Person B."""

from __future__ import annotations

from typing import Literal

from app.contracts import CommunicationDraft


def draft_referral(soap_id: str, receiving_specialist: str) -> CommunicationDraft:
    raise NotImplementedError("Person B — Day 10")


def classify_inbound_reply(
    message: str, context: dict
) -> Literal["reassuring", "needs_review", "needs_urgent_callback"]:
    raise NotImplementedError("Person B — Day 9")
