"""Patient-facing UI tab. OWNER: Person B.

Mimics WhatsApp so demo judges can book / chat without a real phone.
Same code path runs as the real Twilio inbound webhook.
"""

from __future__ import annotations

import gradio as gr


def _chat_fn(message: str, history: list) -> str:
    """Route patient message through the appointment agent."""
    try:
        from app.agents.appointment.api import handle_inbound_message

        draft = handle_inbound_message(
            channel="web",
            payload={"from": "demo-user", "body": message},
        )
        return draft.body
    except Exception as exc:
        return f"[Error] {exc}"


def _submit(user_msg: str, history: list) -> tuple[list, str]:
    reply = _chat_fn(user_msg, history)
    return history + [[user_msg, reply]], ""


def build_tab() -> gr.Blocks:
    with gr.Blocks(theme=gr.themes.Soft()) as tab:
        gr.Markdown("## 📱 Patient — WhatsApp Simulator")
        gr.Markdown(
            "Type as if you were the patient on WhatsApp. "
            "The same code path runs as the real Twilio webhook."
        )

        chatbot = gr.Chatbot(
            label="CliniqAI Appointment Assistant",
            bubble_full_width=False,
            height=420,
        )
        msg_box = gr.Textbox(
            placeholder="e.g. 'Book appointment tomorrow' or 'Cancel appt-abc123'",
            label="Your message",
            lines=1,
        )

        with gr.Row():
            send_btn = gr.Button("Send ➤", variant="primary")
            clear_btn = gr.Button("Clear")

        gr.Markdown("**Quick actions:**")
        with gr.Row():
            book_btn = gr.Button("📅 Book appointment")
            cancel_btn = gr.Button("❌ Cancel appointment")
            reschedule_btn = gr.Button("🔄 Reschedule")

        book_btn.click(
            fn=lambda h: _submit("Book an appointment for the next available slot", h),
            inputs=[chatbot],
            outputs=[chatbot, msg_box],
        )
        cancel_btn.click(
            fn=lambda h: _submit("I want to cancel my appointment", h),
            inputs=[chatbot],
            outputs=[chatbot, msg_box],
        )
        reschedule_btn.click(
            fn=lambda h: _submit("I need to reschedule my appointment", h),
            inputs=[chatbot],
            outputs=[chatbot, msg_box],
        )

        send_btn.click(fn=_submit, inputs=[msg_box, chatbot], outputs=[chatbot, msg_box])
        msg_box.submit(fn=_submit, inputs=[msg_box, chatbot], outputs=[chatbot, msg_box])
        clear_btn.click(fn=lambda: ([], ""), outputs=[chatbot, msg_box])

    return tab
