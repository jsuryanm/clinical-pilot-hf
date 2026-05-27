"""WhatsApp integration. OWNER: Person B — Day 1.

Twilio sandbox for hackathon, WhatsApp Business API post-hackathon.
"""

from __future__ import annotations


def send(to: str, body: str) -> dict:
    """TODO(Person B): Twilio sandbox send."""
    raise NotImplementedError("Person B — Day 1")


def parse_inbound(twilio_payload: dict) -> dict:
    """Normalise Twilio's body shape to {from, to, body, media[]}."""
    raise NotImplementedError("Person B — Day 1")
