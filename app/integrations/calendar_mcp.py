"""Google Calendar MCP client. OWNER: Person B — Day 1."""

from __future__ import annotations

from datetime import datetime


def list_events(calendar_id: str, t_start: datetime, t_end: datetime) -> list[dict]:
    raise NotImplementedError("Person B — Day 1")


def create_event(calendar_id: str, title: str, t_start: datetime, t_end: datetime, **kwargs) -> dict:
    raise NotImplementedError("Person B — Day 2")
