"""Gmail MCP client. OWNER: Person B.

Calls the Gmail MCP server at GMAIL_MCP_URL.
Auth: Bearer token from GMAIL_MCP_TOKEN.
Stubs when token is absent so reminder tasks don't crash in dev.
"""

from __future__ import annotations

import os

import httpx
import structlog

log = structlog.get_logger(__name__)

_BASE = os.getenv("GMAIL_MCP_URL", "https://gmailmcp.googleapis.com")
_TOKEN = os.getenv("GMAIL_MCP_TOKEN", "")
_HEADERS = {"Authorization": f"Bearer {_TOKEN}", "Content-Type": "application/json"} if _TOKEN else {}


def send(to: str, subject: str, body_html: str) -> dict:
    """Send an email via the Gmail MCP server.

    Returns {'messageId': ..., 'status': 'sent'} on success.
    Returns {'status': 'stub', 'to': to} when GMAIL_MCP_TOKEN is not set.
    """
    if not _TOKEN:
        log.warning("gmail_mcp.stub_mode", to=to, subject=subject)
        return {"status": "stub", "to": to, "subject": subject}

    body = {"to": to, "subject": subject, "bodyHtml": body_html}
    with httpx.Client(timeout=15) as client:
        resp = client.post(f"{_BASE}/send", json=body, headers=_HEADERS)
        resp.raise_for_status()
        data = resp.json()

    log.info("gmail_mcp.sent", to=to, subject=subject, message_id=data.get("messageId"))
    return data
