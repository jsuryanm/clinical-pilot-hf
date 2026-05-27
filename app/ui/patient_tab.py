"""Patient-facing UI tab. OWNER: Person B — Day 4.

Mimics WhatsApp so demo judges can book / chat without a real phone.
"""

from __future__ import annotations

import gradio as gr


def build_tab() -> gr.Blocks:
    with gr.Blocks() as tab:
        gr.Markdown("# 📱 Patient (WhatsApp simulator)")
        gr.Markdown(
            "Type as if you were the patient on WhatsApp. The same code path runs "
            "as the real webhook. _Owned by Person B — Day-4 deliverable._"
        )
        gr.ChatInterface(
            fn=lambda msg, hist: "[stub] Person B wires this to handle_inbound_message().",
            type="messages",
        )
    return tab
