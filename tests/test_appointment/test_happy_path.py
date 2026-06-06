"""Appointment Agent — happy path tests. OWNER: Person B."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.contracts import BookingStatus, Channel


# ---------------------------------------------------------------------------
# Mocks
# ---------------------------------------------------------------------------

@pytest.fixture()
def mock_calendar():
    """Patch calendar_mcp so tests don't need a real Google Calendar."""
    with patch("app.agents.appointment.api.calendar_mcp") as m:
        m.list_events.return_value = []  # empty calendar = all slots free
        m.create_event.return_value = {"id": "gcal-test-001"}
        yield m


@pytest.fixture()
def mock_celery():
    """Patch Celery send_reminder so tests don't need a running broker."""
    with patch("app.agents.appointment.api.send_reminder") as m:
        m.apply_async.return_value = MagicMock()
        yield m


@pytest.fixture()
def now_window():
    now = datetime.now(timezone.utc)
    return now + timedelta(days=1, hours=9), now + timedelta(days=1, hours=17)


# ---------------------------------------------------------------------------
# book()
# ---------------------------------------------------------------------------

def test_book_returns_booking_result(mock_calendar, mock_celery, now_window):
    from app.agents.appointment.api import book

    result = book(patient_id="p-001", requested_window=now_window)

    assert result.patient_id == "p-001"
    assert result.status == BookingStatus.CONFIRMED
    assert result.appointment_id.startswith("appt-")
    assert result.calendar_event_id == "gcal-test-001"
    mock_calendar.create_event.assert_called_once()


def test_book_enqueues_reminders(mock_calendar, mock_celery, now_window):
    from app.agents.appointment.api import book

    result = book(patient_id="p-001", requested_window=now_window)

    # Should have 2 reminder jobs: T-24h email and T-2h WhatsApp
    assert len(result.reminder_jobs) == 2
    channels = {j.channel for j in result.reminder_jobs}
    assert Channel.EMAIL in channels
    assert Channel.WHATSAPP in channels
    for job in result.reminder_jobs:
        assert job.enqueued is True


def test_book_no_slot_raises(mock_calendar, mock_celery):
    """When the calendar is fully booked, book() should raise ValueError."""
    from app.agents.appointment.api import book, _SLOT_DURATION

    now = datetime.now(timezone.utc)
    w_start = now + timedelta(hours=1)
    w_end = w_start + timedelta(minutes=_SLOT_DURATION - 1)  # window too narrow

    # Make every possible slot busy
    mock_calendar.list_events.return_value = [
        {
            "start_iso": w_start.isoformat(),
            "end_iso": (w_start + timedelta(hours=8)).isoformat(),
        }
    ]

    with pytest.raises(ValueError, match="No available slot"):
        book(patient_id="p-001", requested_window=(w_start, w_end))


def test_book_skips_busy_slots(mock_calendar, mock_celery):
    """book() should skip over occupied slots and find the first free one."""
    from app.agents.appointment.api import book, _SLOT_DURATION

    now = datetime.now(timezone.utc)
    w_start = now + timedelta(days=1, hours=9)
    w_end = now + timedelta(days=1, hours=11)

    # Block the first slot
    mock_calendar.list_events.return_value = [
        {
            "start_iso": w_start.isoformat(),
            "end_iso": (w_start + timedelta(minutes=_SLOT_DURATION)).isoformat(),
        }
    ]

    result = book(patient_id="p-002", requested_window=(w_start, w_end))
    assert result.slot_iso >= w_start + timedelta(minutes=_SLOT_DURATION)


# ---------------------------------------------------------------------------
# handle_inbound_message()
# ---------------------------------------------------------------------------

def test_handle_inbound_book_intent(mock_calendar, mock_celery):
    from app.agents.appointment.api import handle_inbound_message

    with patch("app.agents.appointment.api._parse_intent") as mock_parse:
        mock_parse.return_value = {"intent": "book", "preferred_date": None}
        draft = handle_inbound_message(
            channel="whatsapp",
            payload={"from": "+919876543210", "body": "book appointment"},
        )

    assert draft.channel == Channel.WHATSAPP
    assert draft.to == "+919876543210"
    assert "confirmed" in draft.body.lower() or "appt-" in draft.body


def test_handle_inbound_other_intent():
    from app.agents.appointment.api import handle_inbound_message

    with patch("app.agents.appointment.api._parse_intent") as mock_parse:
        mock_parse.return_value = {"intent": "other"}
        draft = handle_inbound_message(
            channel="web",
            payload={"from": "demo", "body": "hello"},
        )

    assert "book" in draft.body.lower() or "appointment" in draft.body.lower()


# ---------------------------------------------------------------------------
# cancel()
# ---------------------------------------------------------------------------

def test_cancel_returns_cancelled_result():
    from app.agents.appointment.api import cancel

    result = cancel("appt-abc123", reason="patient no longer needed")
    assert result.status == BookingStatus.CANCELLED
    assert result.appointment_id == "appt-abc123"
