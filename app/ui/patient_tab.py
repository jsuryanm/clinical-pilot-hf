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
    history = history or []
    history.append({"role": "user",      "content": user_msg})
    history.append({"role": "assistant", "content": reply})
    return history, ""


def build_tab() -> gr.Blocks:
    with gr.Blocks() as tab:
        gr.HTML(
            '<div class="cq-intro">'
            '<div class="intro-icon"><svg width="22" height="22" viewBox="0 0 24 24" fill="none" '
            'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">'
            '<path d="M21 11.5a8.4 8.4 0 0 1-8.5 8.4 9 9 0 0 1-3.9-.9L3 21l1.9-5.1A8.4 8.4 0 1 1 21 '
            '11.5Z"/></svg></div>'
            '<div><h2>Appointment <span class="serif-i">assistant</span> '
            '<span class="ship-tag">Shipping</span></h2>'
            "<p>Patients book, change, or cancel conversationally — warmer and simpler than the "
            "clinician surfaces. The same handler runs as the real Twilio webhook (WhatsApp in "
            "production).</p></div></div>"
        )

        chatbot = gr.Chatbot(
            label="CliniqAI Appointment Assistant",
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
