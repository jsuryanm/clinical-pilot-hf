"""Telegram bot notifications. OWNER: Person A.

A lightweight alternative/extra notification channel to Gmail and WhatsApp:
the clinic runs a Telegram bot and patients (or a shared clinic channel) receive
reminders instantly with zero SMTP/OAuth setup.

Set ``TELEGRAM_BOT_TOKEN`` (from @BotFather). ``TELEGRAM_CHAT_ID`` is the
default recipient when a call doesn't pass one. When the token is absent
(dev/test) ``send`` returns a stub instead of calling the API — mirrors the
``gmail_mcp`` / ``whatsapp`` stub behaviour so reminder tasks never crash.
"""

from __future__ import annotations

import os

import httpx
import structlog
from dotenv import load_dotenv

load_dotenv()

log = structlog.get_logger(__name__)

_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
_DEFAULT_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
_API_BASE = "https://api.telegram.org"


def send(body: str, chat_id: str | None = None) -> dict:
    """Send a Telegram message via the Bot API.

    Args:
        body: plain text message. Sent as-is, with no Markdown parsing —
            this avoids Telegram's "can't parse entities" errors when
            patient names, filenames, or other text contain characters
            like ``_``, ``*``, or `` ` `` that legacy Markdown treats as
            formatting markers.
        chat_id: numeric chat/channel id; falls back to ``TELEGRAM_CHAT_ID``.

    Returns:
        ``{"status": "sent", "message_id": ...}`` on success, or
        ``{"status": "stub", ...}`` when no bot token is configured.
    """
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")

    if not _TOKEN or not chat:
        log.warning("telegram.stub_mode", has_token=bool(_TOKEN), has_chat=bool(chat))
        return {"status": "stub", "chat_id": chat, "body": body}

    url = f"{_API_BASE}/bot{token}/sendMessage"
    payload = {"chat_id": chat, "text": body}
    with httpx.Client(timeout=15) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    message_id = (data.get("result") or {}).get("message_id")
    log.info("telegram.sent", chat_id=chat, message_id=message_id)
    return {"status": "sent", "chat_id": chat, "message_id": message_id}


# if __name__ == "__main__":
#     print("TOKEN SET:", bool(_TOKEN))
#     print("CHAT SET:", bool(_DEFAULT_CHAT_ID))

#     result = send("✅ Test message, setup complete!")
#     print(result)