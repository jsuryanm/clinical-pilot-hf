"""WhatsApp simulator — pipes JSON payloads into the inbound handler.

Person C can use this for demos without a real WhatsApp number.

Usage:
  # In Python
  from tests.wa_sim import simulate, conversation

  r = simulate("+919876543210", "Book appointment for tomorrow")
  print(r.body)

  # Or run interactively
  python -m tests.wa_sim
"""

from __future__ import annotations

import sys

from app.agents.appointment.api import handle_inbound_message
from app.contracts import CommunicationDraft


def simulate(
    sender_phone: str,
    message: str,
    channel: str = "whatsapp",
) -> CommunicationDraft:
    """Send a single inbound message and return the reply draft."""
    payload = {"from": sender_phone, "to": "+14155238886", "body": message, "media": []}
    return handle_inbound_message(channel=channel, payload=payload)  # type: ignore[arg-type]


def conversation(sender_phone: str, messages: list[str]) -> list[CommunicationDraft]:
    """Send a list of messages in sequence and return all reply drafts."""
    return [simulate(sender_phone, msg) for msg in messages]


# ---------------------------------------------------------------------------
# Interactive REPL
# ---------------------------------------------------------------------------

def _repl() -> None:
    phone = "+919876543210"
    print("CliniqAI WhatsApp Simulator")
    print(f"Simulating sender: {phone}")
    print("Type your message (Ctrl-C to quit)\n")
    while True:
        try:
            msg = input("You: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break
        if not msg:
            continue
        draft = simulate(phone, msg)
        print(f"Bot: {draft.body}\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Non-interactive: python -m tests.wa_sim "Book appointment for Monday"
        phone = sys.argv[1] if len(sys.argv) > 2 else "+919876543210"
        message = sys.argv[-1]
        draft = simulate(phone, message)
        print(draft.body)
    else:
        _repl()
