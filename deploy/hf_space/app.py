"""Hugging Face Spaces entrypoint.

This file is owned by Person C. It contains no agent logic — only imports the
three per-person tabs and stitches them into a TabbedInterface so the three
people rarely touch this file at the same time.

Set HF_SPACE_BACKEND_URL via Spaces Secrets to point at the deployed FastAPI.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make `app/...` importable when running from deploy/hf_space/.
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import gradio as gr  # noqa: E402

from app.ui.doctor_tab import build_tab as build_doctor_tab  # noqa: E402
from app.ui.nurse_admin_tab import build_tab as build_nurse_admin_tab  # noqa: E402
from app.ui.patient_tab import build_tab as build_patient_tab  # noqa: E402

BACKEND_URL = os.getenv("HF_SPACE_BACKEND_URL", "http://localhost:8000")


def build_app() -> gr.Blocks:
    with gr.Blocks(title="CliniqAI") as demo:
        gr.Markdown(
            f"# 🪶 CliniqAI\nClinical operations AI for Indian hospitals. "
            f"Backend: `{BACKEND_URL}`"
        )
        with gr.Tabs():
            with gr.Tab("Doctor"):
                build_doctor_tab()
            with gr.Tab("Patient"):
                build_patient_tab()
            with gr.Tab("Nurse & Admin"):
                build_nurse_admin_tab()
    return demo


if __name__ == "__main__":
    build_app().launch(
        server_name="0.0.0.0",
        server_port=7860,
        theme=gr.themes.Soft(),
        share=True
    )