"""Handover Agent — public API. OWNER: Person C."""

from __future__ import annotations

from datetime import datetime

from app.contracts import HandoverBrief


def generate_handover(ward_id: str, shift_end_ts: datetime) -> HandoverBrief:
    raise NotImplementedError("Person C — Day 4")
