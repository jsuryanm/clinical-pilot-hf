"""Discharge Agent — happy path tests. OWNER: Person B."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.contracts import DischargeSubtaskStatus


def _make_llm_mock(text: str = "test output") -> MagicMock:
    m = MagicMock()
    m.text = text
    return m


# ---------------------------------------------------------------------------
# initiate_discharge
# ---------------------------------------------------------------------------

def test_initiate_discharge_returns_coordination():
    from app.agents.discharge.api import initiate_discharge

    with (
        patch("app.agents.discharge.api.complete", return_value=_make_llm_mock("summary")),
        patch("app.integrations.whatsapp.send", return_value={"sid": "stub", "status": "queued", "to": "+91x"}),
        patch("app.agents.appointment.api.calendar_mcp") as mock_cal,
        patch("app.agents.discharge.api.post_discharge_followup") as mock_task,
    ):
        mock_cal.list_events.return_value = []
        mock_cal.create_event.return_value = {"id": "gcal-stub"}
        mock_task.apply_async.return_value = MagicMock()

        result = initiate_discharge("p-001")

    assert result.patient_id == "p-001"
    assert result.discharge_id.startswith("dsc-")
    assert len(result.subtasks) == 5


def test_initiate_discharge_has_all_five_subtasks():
    from app.agents.discharge.api import initiate_discharge

    expected_names = {
        "discharge_summary",
        "pharmacy",
        "family_notification",
        "follow_up_appointment",
        "billing_trigger",
    }

    with (
        patch("app.agents.discharge.api.complete", return_value=_make_llm_mock('["med"]')),
        patch("app.integrations.whatsapp.send", return_value={"sid": "s", "status": "q", "to": "+91x"}),
        patch("app.agents.appointment.api.calendar_mcp") as mock_cal,
        patch("app.agents.discharge.api.post_discharge_followup") as mock_task,
    ):
        mock_cal.list_events.return_value = []
        mock_cal.create_event.return_value = {"id": "gcal-stub"}
        mock_task.apply_async.return_value = MagicMock()

        result = initiate_discharge("p-002")

    actual_names = {s.name for s in result.subtasks}
    assert actual_names == expected_names


def test_initiate_discharge_subtask_failure_is_isolated():
    """If one subtask fails, the others should still complete."""
    from app.agents.discharge.api import initiate_discharge

    call_count = 0

    def maybe_fail(text: str = "ok") -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("simulated LLM failure")
        m = MagicMock()
        m.text = text
        return m

    with (
        patch("app.agents.discharge.api.complete", side_effect=maybe_fail),
        patch("app.integrations.whatsapp.send", return_value={"sid": "s", "status": "q", "to": "+91x"}),
        patch("app.agents.appointment.api.calendar_mcp") as mock_cal,
        patch("app.agents.discharge.api.post_discharge_followup") as mock_task,
    ):
        mock_cal.list_events.return_value = []
        mock_cal.create_event.return_value = {"id": "gcal-stub"}
        mock_task.apply_async.return_value = MagicMock()

        result = initiate_discharge("p-003")

    statuses = {s.status for s in result.subtasks}
    # At least one should be FAILED, but others should succeed
    assert DischargeSubtaskStatus.FAILED in statuses
    assert len(result.subtasks) == 5  # all 5 reported, even the failed one


def test_initiate_discharge_enqueues_72h_followup():
    from app.agents.discharge.api import initiate_discharge

    with (
        patch("app.agents.discharge.api.complete", return_value=_make_llm_mock("ok")),
        patch("app.integrations.whatsapp.send", return_value={"sid": "s", "status": "q", "to": "+91x"}),
        patch("app.agents.appointment.api.calendar_mcp") as mock_cal,
        patch("app.agents.discharge.api.post_discharge_followup") as mock_task,
    ):
        mock_cal.list_events.return_value = []
        mock_cal.create_event.return_value = {"id": "gcal-stub"}
        mock_task.apply_async.return_value = MagicMock()

        initiate_discharge("p-004")

    mock_task.apply_async.assert_called_once()
    _, kwargs = mock_task.apply_async.call_args
    assert "eta" in kwargs  # must be scheduled with an eta, not fired immediately
