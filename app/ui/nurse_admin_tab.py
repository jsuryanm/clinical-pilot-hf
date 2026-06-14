"""Nurse + Admin tab. OWNER: Person C — Day 5."""

from __future__ import annotations

from datetime import datetime, timezone

import gradio as gr


# ---------------------------------------------------------------------------
# Handover helpers
# ---------------------------------------------------------------------------


def _generate_handover(ward_id: str) -> tuple[str, list]:
    try:
        from app.agents.handover.api import generate_handover

        brief = generate_handover(
            ward_id=ward_id.strip() or "ward-A",
            shift_end_ts=datetime.now(timezone.utc),
        )
        info = (
            f"**Brief ID:** `{brief.brief_id}` &nbsp;|&nbsp; "
            f"**Estimated read:** {brief.estimated_read_minutes} min &nbsp;|&nbsp; "
            f"**Shift end:** {brief.shift_end_ts.strftime('%H:%M UTC')}"
        )
        rows = [
            [
                p.bed or "—",
                p.priority.value.upper(),
                p.patient_id,
                p.one_liner,
                "; ".join(p.actions_pending) if p.actions_pending else "—",
            ]
            for p in brief.patients
        ]
        return info, rows
    except Exception as exc:
        return f"⚠️ {exc}", []


# ---------------------------------------------------------------------------
# Roster helpers
# ---------------------------------------------------------------------------


def _generate_roster(csv_path: str, window_days: int) -> tuple[str, list, str, object, object]:
    """Returns: info_md, df_rows, conflicts_text, roster_state, staff_state.

    When no CSV path is given, falls back to fake_roster() for demo.
    Sick-call replacement requires real staff loaded from a CSV.
    """
    try:
        csv_path = csv_path.strip()
        if csv_path:
            from pathlib import Path

            from app.agents.roster.api import generate_roster, load_staff

            path = Path(csv_path)
            staff = load_staff(path)
            result = generate_roster(path, window_days=int(window_days))
        else:
            from app.agents.roster.mocks import fake_roster

            result = fake_roster()
            staff = []   # sick-call won't work without real staff records

        info = (
            f"**Roster ID:** `{result.roster_id}` &nbsp;|&nbsp; "
            f"**Fairness score:** {result.fairness_score:.2f} &nbsp;|&nbsp; "
            f"**Generated in:** {result.generated_in_seconds:.3f}s &nbsp;|&nbsp; "
            f"**Assignments:** {len(result.assignments)}"
        )
        rows = [
            [
                a.shift_id,
                a.staff_id,
                a.role,
                a.start.strftime("%Y-%m-%d %H:%M"),
                a.end.strftime("%H:%M"),
                "✓ replacement" if a.is_replacement else "",
            ]
            for a in result.assignments[:60]  # cap display at 60 rows
        ]
        conflicts_text = (
            "\n".join(result.unresolved_conflicts)
            if result.unresolved_conflicts
            else "None"
        )
        return info, rows, conflicts_text, result, staff

    except Exception as exc:
        return f"⚠️ {exc}", [], "", None, []


def _find_replacement(
    shift_id: str,
    sick_staff_id: str,
    roster_state: object,
    staff_state: object,
) -> tuple[str, list]:
    if roster_state is None:
        return "⚠️ Generate a roster first.", []
    shift_id = shift_id.strip()
    sick_staff_id = sick_staff_id.strip()
    if not shift_id or not sick_staff_id:
        return "⚠️ Enter both shift ID and sick staff ID.", []

    try:
        from app.agents.roster.api import find_sick_call_replacement

        updated = find_sick_call_replacement(
            shift_id,
            sick_staff_id,
            staff=staff_state or [],
            roster=roster_state,
        )
        # Check whether a replacement was actually slotted in
        replacement = next(
            (a for a in updated.assignments if a.shift_id == shift_id and a.is_replacement),
            None,
        )
        if replacement:
            msg = (
                f"✅ **{sick_staff_id}** covered by **{replacement.staff_id}** "
                f"on shift `{shift_id}`."
            )
        else:
            conflict_msgs = [c for c in updated.unresolved_conflicts if shift_id in c]
            msg = f"⚠️ {conflict_msgs[0]}" if conflict_msgs else "⚠️ No valid replacement found."

        rows = [
            [
                a.shift_id,
                a.staff_id,
                a.role,
                a.start.strftime("%Y-%m-%d %H:%M"),
                a.end.strftime("%H:%M"),
                "✓ replacement" if a.is_replacement else "",
            ]
            for a in updated.assignments[:60]
        ]
        return msg, rows

    except Exception as exc:
        return f"⚠️ {exc}", []


# ---------------------------------------------------------------------------
# Discharge helpers
# ---------------------------------------------------------------------------

_STATUS_ICON: dict[str, str] = {
    "done": "✅",
    "in_progress": "🔄",
    "queued": "⏳",
    "failed": "❌",
    "awaiting_approval": "👁️",
}


def _initiate_discharge(patient_id: str) -> tuple[str, list]:
    patient_id = patient_id.strip()
    if not patient_id:
        return "⚠️ Enter a patient ID.", []
    try:
        from app.agents.discharge.api import initiate_discharge

        coord = initiate_discharge(patient_id)
        info = (
            f"**Discharge ID:** `{coord.discharge_id}` &nbsp;|&nbsp; "
            f"**Target complete by:** {coord.target_complete_by.strftime('%H:%M UTC')}"
        )
        rows = [
            [
                _STATUS_ICON.get(s.status.value, "❓")
                + " "
                + s.status.value.replace("_", " ").title(),
                s.name.replace("_", " ").title(),
                s.detail or "—",
                s.artifact_id or "—",
            ]
            for s in coord.subtasks
        ]
        return info, rows
    except Exception as exc:
        return f"⚠️ {exc}", []


# ---------------------------------------------------------------------------
# Wiki health helpers
# ---------------------------------------------------------------------------


def _run_wiki_lint() -> tuple[str, list]:
    try:
        from app.agents.wiki.api import lint_wiki

        report = lint_wiki()
        stamp = report.generated_at.strftime("%Y-%m-%d %H:%M UTC")
        if not report.issues:
            return f"✅ No issues found. Corpus is clean as of {stamp}.", []
        info = f"**{len(report.issues)} issue(s)** found as of {stamp}."
        rows = [
            [i.kind.replace("_", " ").title(), i.page_path, i.detail]
            for i in report.issues
        ]
        return info, rows
    except Exception as exc:
        return f"⚠️ {exc}", []


# ---------------------------------------------------------------------------
# Tab builder
# ---------------------------------------------------------------------------


def build_tab() -> gr.Blocks:
    with gr.Blocks() as tab:
        gr.Markdown("# 🩺 Nurse & Admin")

        with gr.Tabs():

            # ----------------------------------------------------------------
            # Handover
            # ----------------------------------------------------------------
            with gr.Tab("Handover"):
                gr.Markdown(
                    "Generates the current ward handover brief from patient vitals "
                    "and shift notes. Patients are ordered **urgent → watch → stable**."
                )
                with gr.Row():
                    ward_input = gr.Textbox(
                        value="ward-A", label="Ward ID", scale=3
                    )
                    gen_handover_btn = gr.Button(
                        "Generate brief", variant="primary", scale=1
                    )

                brief_info_md = gr.Markdown("")
                patients_df = gr.DataFrame(
                    headers=["Bed", "Priority", "Patient ID", "One-liner", "Pending actions"],
                    datatype=["str", "str", "str", "str", "str"],
                    interactive=False,
                    label="Patients",
                )

                gen_handover_btn.click(
                    fn=_generate_handover,
                    inputs=[ward_input],
                    outputs=[brief_info_md, patients_df],
                )

            # ----------------------------------------------------------------
            # Roster
            # ----------------------------------------------------------------
            with gr.Tab("Roster"):
                gr.Markdown(
                    "Generate a 14-day duty roster. "
                    "Leave the CSV path blank to use demo data. "
                    "Sick-call replacement requires a real CSV (staff IDs must match the roster)."
                )

                # Stored across callbacks so sick-call can reference them
                roster_state = gr.State(None)
                staff_state = gr.State([])

                with gr.Row():
                    csv_input = gr.Textbox(
                        placeholder="raw_data/duty_roster/roster.csv",
                        label="Staff CSV path (leave blank for demo)",
                        scale=4,
                    )
                    window_slider = gr.Slider(
                        minimum=7, maximum=28, value=14, step=7, label="Days", scale=1
                    )

                gen_roster_btn = gr.Button("Generate roster", variant="primary")
                roster_info_md = gr.Markdown("")
                roster_df = gr.DataFrame(
                    headers=["Shift ID", "Staff ID", "Role", "Start", "End", "Note"],
                    datatype=["str", "str", "str", "str", "str", "str"],
                    interactive=False,
                    label="Assignments (first 60 shown)",
                )
                conflicts_box = gr.Textbox(
                    label="Unresolved conflicts", interactive=False, lines=3
                )

                gen_roster_btn.click(
                    fn=_generate_roster,
                    inputs=[csv_input, window_slider],
                    outputs=[roster_info_md, roster_df, conflicts_box, roster_state, staff_state],
                )

                gr.Markdown("---\n### Sick-call replacement")
                gr.Markdown(
                    "Copy a shift ID from the table above, enter the absent staff ID. "
                    "The agent picks the lowest-load, same-role, available replacement."
                )
                with gr.Row():
                    shift_id_input = gr.Textbox(
                        label="Shift ID", placeholder="sh-xxxxxxxx", scale=2
                    )
                    sick_staff_input = gr.Textbox(
                        label="Sick staff ID", placeholder="n-01", scale=2
                    )
                    sick_call_btn = gr.Button(
                        "Find replacement", variant="secondary", scale=1
                    )

                sick_call_result = gr.Markdown("")

                sick_call_btn.click(
                    fn=_find_replacement,
                    inputs=[shift_id_input, sick_staff_input, roster_state, staff_state],
                    outputs=[sick_call_result, roster_df],
                )

            # ----------------------------------------------------------------
            # Discharge queue
            # ----------------------------------------------------------------
            with gr.Tab("Discharge queue"):
                gr.Markdown(
                    "Enter the patient ID once a clinician marks them clinically ready. "
                    "All 5 subtasks are fanned out in parallel: "
                    "discharge summary, pharmacy, family notification, "
                    "follow-up booking, and billing trigger."
                )
                with gr.Row():
                    patient_id_input = gr.Textbox(
                        value="p-001",
                        label="Patient ID",
                        placeholder="p-001",
                        scale=3,
                    )
                    discharge_btn = gr.Button(
                        "Initiate discharge", variant="primary", scale=1
                    )

                discharge_info_md = gr.Markdown("")
                subtask_df = gr.DataFrame(
                    headers=["Status", "Subtask", "Detail", "Artifact ID"],
                    datatype=["str", "str", "str", "str"],
                    interactive=False,
                    label="Discharge subtask statuses",
                )

                discharge_btn.click(
                    fn=_initiate_discharge,
                    inputs=[patient_id_input],
                    outputs=[discharge_info_md, subtask_df],
                )

            # ----------------------------------------------------------------
            # Wiki health
            # ----------------------------------------------------------------
            with gr.Tab("Wiki health"):
                gr.Markdown(
                    "### Wiki lint report\n"
                    "Person A's nightly `lint_wiki()` job surfaces issues here. "
                    "It checks for: missing frontmatter fields, stale pages "
                    "(last updated > 180 days), broken `[[cross-refs]]`, "
                    "and contradictions between condition pages."
                )
                run_lint_btn = gr.Button("Run lint", variant="primary")
                lint_info_md = gr.Markdown("")
                lint_df = gr.DataFrame(
                    headers=["Issue", "Page", "Detail"],
                    datatype=["str", "str", "str"],
                    interactive=False,
                    label="Lint issues",
                )

                run_lint_btn.click(
                    fn=_run_wiki_lint,
                    inputs=[],
                    outputs=[lint_info_md, lint_df],
                )

    return tab