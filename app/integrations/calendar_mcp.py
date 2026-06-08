"""Calendar MCP client. OWNER: Person B (Google path) + Person A (local path).

Two backends, selected by ``CALENDAR_BACKEND``:
  - ``local`` (default) — our own Postgres-backed mini calendar
    (``app/integrations/local_calendar.py``); no external dependency.
  - ``google`` — the Google Calendar MCP server at GOOGLE_CALENDAR_MCP_URL
    (Bearer token GOOGLE_CALENDAR_MCP_TOKEN; stubs when the token is absent).

The public surface (list_events / create_event / delete_event) is unchanged so
the appointment agent doesn't care which backend is active.
"""

from __future__ import annotations

import os
from datetime import datetime

import httpx
import structlog

log = structlog.get_logger(__name__)

_BACKEND = os.getenv("CALENDAR_BACKEND", "local").lower()
_BASE = os.getenv("GOOGLE_CALENDAR_MCP_URL", "https://calendarmcp.googleapis.com")
_TOKEN = os.getenv("GOOGLE_CALENDAR_MCP_TOKEN", "")
_HEADERS = {"Authorization": f"Bearer {_TOKEN}", "Content-Type": "application/json"} if _TOKEN else {}


def _use_local() -> bool:
    return os.getenv("CALENDAR_BACKEND", "local").lower() == "local"


def _patient_from(title: str, kwargs: dict) -> str:
    """Recover the patient id the agent encodes in the description/title."""
    desc = kwargs.get("description", "")
    if desc.startswith("Patient: "):
        return desc[len("Patient: "):].strip()
    if " — " in title:
        return title.split(" — ", 1)[1].strip()
    return "unknown"


def _get(path: str, params: dict | None = None) -> dict:
    with httpx.Client(timeout=10) as client:
        resp = client.get(f"{_BASE}{path}", params=params, headers=_HEADERS)
        resp.raise_for_status()
        return resp.json()


def _post(path: str, body: dict) -> dict:
    with httpx.Client(timeout=10) as client:
        resp = client.post(f"{_BASE}{path}", json=body, headers=_HEADERS)
        resp.raise_for_status()
        return resp.json()


def list_events(calendar_id: str, t_start: datetime, t_end: datetime) -> list[dict]:
    """Return events in [t_start, t_end) for calendar_id.

    Each item has: {id, title, start_iso, end_iso, attendees[]}
    Returns [] in stub mode (dev without token) — caller treats empty as available.
    """
    if _use_local():
        from app.integrations import local_calendar

        return local_calendar.list_appointments(calendar_id, t_start, t_end)

    if not _TOKEN:
        log.warning("calendar_mcp.stub_mode", op="list_events")
        return []

    data = _get(
        f"/calendars/{calendar_id}/events",
        params={"timeMin": t_start.isoformat(), "timeMax": t_end.isoformat()},
    )
    return data.get("items", [])


def create_event(
    calendar_id: str,
    title: str,
    t_start: datetime,
    t_end: datetime,
    **kwargs,
) -> dict:
    """Create a calendar event; returns the created event dict (with `id`).

    kwargs forwarded to the MCP body (description, attendees, location, etc.).
    """
    if _use_local():
        from app.integrations import local_calendar

        duration = int((t_end - t_start).total_seconds() // 60) or 15
        return local_calendar.book_appointment(
            patient_id=_patient_from(title, kwargs),
            doctor_id=calendar_id,
            slot=t_start,
            duration_minutes=duration,
            notes=kwargs.get("description"),
        )

    if not _TOKEN:
        log.warning("calendar_mcp.stub_mode", op="create_event")
        return {
            "id": f"gcal-stub-{t_start.strftime('%Y%m%dT%H%M')}",
            "title": title,
            "start_iso": t_start.isoformat(),
            "end_iso": t_end.isoformat(),
        }

    body = {
        "calendarId": calendar_id,
        "summary": title,
        "start": {"dateTime": t_start.isoformat()},
        "end": {"dateTime": t_end.isoformat()},
        **kwargs,
    }
    return _post(f"/calendars/{calendar_id}/events", body)


def delete_event(calendar_id: str, event_id: str) -> bool:
    """Delete a calendar event. Returns True on success."""
    if _use_local():
        from app.integrations import local_calendar

        try:
            local_calendar.cancel_appointment(event_id, reason="deleted via calendar_mcp")
        except KeyError:
            return False
        return True

    if not _TOKEN:
        log.warning("calendar_mcp.stub_mode", op="delete_event")
        return True

    url = f"{_BASE}/calendars/{calendar_id}/events/{event_id}"
    with httpx.Client(timeout=10) as client:
        resp = client.delete(url, headers=_HEADERS)
        resp.raise_for_status()
    log.info("calendar_mcp.event_deleted", event_id=event_id)
    return True
