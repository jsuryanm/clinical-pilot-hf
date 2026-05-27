"""Nurse + Admin tab. OWNER: Person C — Day 5."""

from __future__ import annotations

import gradio as gr


def build_tab() -> gr.Blocks:
    with gr.Blocks() as tab:
        gr.Markdown("# 🩺 Nurse & Admin")
        with gr.Tabs():
            with gr.Tab("Handover"):
                gr.Markdown("Current shift handover brief will render here.")
                gr.Button("Regenerate brief")
                gr.DataFrame(
                    headers=["Bed", "Patient", "Priority", "One-liner"],
                    value=[["A-12", "p-007", "URGENT", "Post-op fever — review wound"]],
                )
            with gr.Tab("Roster"):
                gr.Markdown("14-day roster + sick-call replacement.")
                gr.Button("Generate roster", variant="primary")
                gr.Button("Mark staff sick")
            with gr.Tab("Discharge queue"):
                gr.Markdown("Patients flagged ready for discharge — click to fan out subtasks.")
                gr.Button("Mark patient ready for discharge")
            with gr.Tab("Wiki health"):
                gr.Markdown("Wiki lint report (from Person A's nightly job).")
    return tab
