"""Doctor-facing UI tab. OWNER: Person A — Day 4.

Three panes: record/upload audio, live draft, approve / edit / reject.
This stub renders a placeholder until A wires the real flow.
"""

from __future__ import annotations

import gradio as gr


def build_tab() -> gr.Blocks:
    with gr.Blocks() as tab:
        gr.Markdown("# 👨‍⚕️ Doctor")
        gr.Markdown(
            "Record the consult, review the AI-drafted SOAP note, approve or edit. "
            "_Tab owned by Person A — currently placeholder. Day-4 deliverable._"
        )
        with gr.Row():
            with gr.Column():
                gr.Audio(label="Record consult", sources=["microphone", "upload"])
                gr.Button("Draft SOAP note", variant="primary")
            with gr.Column():
                gr.Markdown("### Draft will appear here")
                gr.Code(value="", language="markdown", label="SOAP draft", interactive=True)
                with gr.Row():
                    gr.Button("Approve", variant="primary")
                    gr.Button("Edit & re-draft")
                    gr.Button("Reject", variant="stop")
    return tab
