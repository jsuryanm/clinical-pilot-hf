"""Telegram channel tests. OWNER: Person A.

No network: stub mode is asserted directly, and the live path is exercised with
a patched httpx client.
"""

from __future__ import annotations

import importlib
from unittest.mock import MagicMock, patch

from app.contracts import Channel


def test_channel_enum_has_telegram() -> None:
    assert Channel.TELEGRAM.value == "telegram"


def test_send_stub_mode_without_token(monkeypatch) -> None:
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
    import app.integrations.telegram as tg

    tg = importlib.reload(tg)  # re-read env at import time
    out = tg.send("hello")
    assert out["status"] == "stub"


def test_send_live_path(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
    import app.integrations.telegram as tg

    tg = importlib.reload(tg)

    fake_resp = MagicMock()
    fake_resp.json.return_value = {"ok": True, "result": {"message_id": 99}}
    fake_resp.raise_for_status.return_value = None
    fake_client = MagicMock()
    fake_client.__enter__.return_value.post.return_value = fake_resp

    with patch.object(tg.httpx, "Client", return_value=fake_client):
        out = tg.send("appointment reminder")

    assert out["status"] == "sent"
    assert out["message_id"] == 99
    # ensure we posted to the sendMessage endpoint with the chat id
    _, kwargs = fake_client.__enter__.return_value.post.call_args
    assert kwargs["json"]["chat_id"] == "12345"


def test_reminder_task_routes_telegram(monkeypatch) -> None:
    """send_reminder(channel='telegram') must dispatch through telegram.send."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "")  # force stub so no network
    from app.agents.appointment import tasks

    with patch("app.integrations.telegram.send", return_value={"status": "stub"}) as m:
        # call the task body directly (bypass celery) via .run
        out = tasks.send_reminder.run("appt-123", "telegram")

    m.assert_called_once()
    assert out["channel"] == "telegram"
