"""WhatsApp integration via Twilio sandbox. OWNER: Person B.

Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM in .env.local.
WhatsApp Business API formal approval is a post-hackathon task.
"""

from __future__ import annotations

import os

import structlog

log = structlog.get_logger(__name__)

_TWILIO_FROM = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")


def _client():
    """Lazy Twilio client — fails loudly if credentials are missing."""
    try:
        from twilio.rest import Client  # type: ignore[import-not-found]
    except ImportError as e:
        raise RuntimeError("twilio is not installed — pip install twilio") from e

    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    if not sid or not token:
        raise RuntimeError("TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN not set in env")
    return Client(sid, token)


def send(to: str, body: str) -> dict:
    """Send a WhatsApp message via Twilio sandbox.

    `to` must be E.164 e.g. '+919876543210'; 'whatsapp:' prefix added automatically.
    Returns Twilio message SID dict on success.
    """
    if not to.startswith("whatsapp:"):
        to = f"whatsapp:{to}"

    client = _client()
    msg = client.messages.create(from_=_TWILIO_FROM, to=to, body=body)
    log.info("whatsapp.sent", sid=msg.sid, to=to)
    return {"sid": msg.sid, "status": msg.status, "to": to}


def parse_inbound(twilio_payload: dict) -> dict:
    """Normalise Twilio's inbound webhook body to {from, to, body, media, message_sid}.

    Twilio sends form-encoded fields; FastAPI parses them into a dict before calling this.
    """
    def _strip(s: str) -> str:
        return s.removeprefix("whatsapp:")

    num_media = int(twilio_payload.get("NumMedia", "0") or 0)
    media = [
        {
            "url": twilio_payload.get(f"MediaUrl{i}", ""),
            "content_type": twilio_payload.get(f"MediaContentType{i}", ""),
        }
        for i in range(num_media)
    ]

    return {
        "from": _strip(twilio_payload.get("From", "")),
        "to": _strip(twilio_payload.get("To", "")),
        "body": twilio_payload.get("Body", "").strip(),
        "media": media,
        "message_sid": twilio_payload.get("MessageSid", ""),
    }
