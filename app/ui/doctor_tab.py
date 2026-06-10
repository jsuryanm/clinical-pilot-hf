"""Doctor-facing UI tab. OWNER: Person A — Day 4.

Three panes: record/upload audio (or paste a transcript), the live SOAP draft
in editable S/O/A/P fields, and approve / reject. "Approve" writes the draft to
the patient's wiki page via the Documentation Agent.

If no LLM provider key is configured the draft step falls back to the mock SOAP
draft so the tab still demos end-to-end on a fresh HF Space — the status banner
says so explicitly.
"""

from __future__ import annotations

import os

import gradio as gr

from app.agents.documentation.api import approve_draft, draft_soap
from app.agents.documentation.mocks import fake_soap_draft
from app.contracts import SOAPNoteDraft

_BLANK = ("", "", "", "")


def _llm_configured() -> bool:
    return any(os.getenv(k) for k in ("GROQ_API_KEY", "OPENROUTER_API_KEY", "OLLAMA_BASE_URL"))


def _citations_md(draft: SOAPNoteDraft) -> str:
    icd = "\n".join(
        f"- `{s.code}` {s.label} ({s.confidence:.0%})" for s in draft.icd10_suggestions
    ) or "_none_"
    cites = "\n".join(
        f"- **{c.source_type}** · `{c.source_id}`" + (f" — {c.snippet}" if c.snippet else "")
        for c in draft.sources
    ) or "_none_"
    refer = "⚠️ **Referral suggested**" if draft.referral_needed else "No referral flagged"
    return (
        f"**Confidence:** {draft.confidence_overall:.0%} · {refer}\n\n"
        f"**ICD-10 candidates**\n{icd}\n\n"
        f"**Citations (audit trail)**\n{cites}\n\n"
        f"_Model: `{draft.model}` · draft `{draft.draft_id}`_"
    )


def _draft(patient_id: str, audio_path: str | None, transcript: str):
    """Run the Documentation Agent and populate the editable draft panes."""
    patient_id = (patient_id or "").strip()
    transcript = (transcript or "").strip()
    if not patient_id:
        return (*_BLANK, "", None, "❌ Enter a patient id first.")
    if not transcript and not audio_path:
        return (*_BLANK, "", None, "❌ Record/upload audio or paste a transcript.")

    try:
        draft = draft_soap(
            patient_id=patient_id,
            transcript=transcript or None,
            audio_path=audio_path or None,
        )
        status = f"✅ Draft ready for **{patient_id}**. Review, edit, then Approve."
    except Exception as exc:  # noqa: BLE001 — keep the demo alive on LLM/index errors
        if _llm_configured():
            return (*_BLANK, "", None, f"❌ Drafting failed: {exc}")
        draft = fake_soap_draft(patient_id)
        status = "⚠️ No LLM key configured — showing a **mock** draft so the UI demos."

    return (
        draft.soap.subjective,
        draft.soap.objective,
        draft.soap.assessment,
        draft.soap.plan,
        _citations_md(draft),
        draft,
        status,
    )


def _approve(draft: SOAPNoteDraft | None, subj: str, obj: str, assess: str, plan: str):
    """Persist the (possibly edited) draft to the patient's wiki page."""
    if draft is None:
        return "❌ Nothing to approve — draft a note first."
    try:
        ref = approve_draft(
            draft,
            edits={"subjective": subj, "objective": obj, "assessment": assess, "plan": plan},
        )
    except Exception as exc:  # noqa: BLE001
        return f"❌ Approve failed: {exc}"
    return f"✅ Written to `{ref.page_path}` (version `{ref.version}`)."


def _reject():
    return (*_BLANK, "", None, "🗑️ Draft discarded.")


def build_tab() -> gr.Blocks:
    with gr.Blocks() as tab:
        gr.Markdown("# 👨‍⚕️ Doctor — Consultation Documentation")
        gr.Markdown(
            "Record or upload the consult (or paste a transcript), generate the "
            "AI SOAP draft, edit any field, then **Approve** to write it to the "
            "patient's wiki page."
        )

        draft_state = gr.State(None)

        with gr.Row():
            with gr.Column(scale=1):
                patient_id = gr.Textbox(label="Patient ID", value="p-001", lines=1)
                audio = gr.Audio(
                    label="Record / upload consult",
                    sources=["microphone", "upload"],
                    type="filepath",
                )
                transcript = gr.Textbox(
                    label="…or paste a transcript",
                    placeholder="Doctor: how have you been? Patient: …",
                    lines=6,
                )
                draft_btn = gr.Button("Draft SOAP note", variant="primary")

            with gr.Column(scale=2):
                status = gr.Markdown("_Awaiting input._")
                subjective = gr.Textbox(label="Subjective", lines=3, interactive=True)
                objective = gr.Textbox(label="Objective", lines=3, interactive=True)
                assessment = gr.Textbox(label="Assessment", lines=3, interactive=True)
                plan = gr.Textbox(label="Plan", lines=4, interactive=True)
                citations = gr.Markdown("")
                with gr.Row():
                    approve_btn = gr.Button("Approve", variant="primary")
                    reject_btn = gr.Button("Reject", variant="stop")

        draft_btn.click(
            fn=_draft,
            inputs=[patient_id, audio, transcript],
            outputs=[subjective, objective, assessment, plan, citations, draft_state, status],
        )
        approve_btn.click(
            fn=_approve,
            inputs=[draft_state, subjective, objective, assessment, plan],
            outputs=[status],
        )
        reject_btn.click(
            fn=_reject,
            outputs=[subjective, objective, assessment, plan, citations, draft_state, status],
        )

    return tab
