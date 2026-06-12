"""Hugging Face Spaces entrypoint.

This file is owned by Person C. It contains no agent logic — only imports the
three per-person tabs and stitches them into one branded Gradio app so the three
people rarely touch this file at the same time.

The professional look — the CliniqAI design system from `design_handoff_cliniqai`
(deep-navy → bright-blue clinical palette, the quill mascot, Plus Jakarta Sans /
Newsreader-italic headings, cards / pills / banners / tables) — lives here as a
custom theme + global CSS, because the top-level ``gr.Blocks`` theme and CSS
govern every nested tab.

Set HF_SPACE_BACKEND_URL via Spaces Secrets to point at the deployed FastAPI.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Make `app/...` importable when running from deploy/hf_space/.
# Insert at the front unconditionally: this file is named app.py, so its own
# directory (sys.path[0]) would otherwise shadow the real `app` package — which
# happens once the project is installed editable (repo root already on sys.path,
# so a presence check would skip the insert).
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import gradio as gr  # noqa: E402

from app.ui.doctor_tab import build_tab as build_doctor_tab  # noqa: E402
from app.ui.nurse_admin_tab import build_tab as build_nurse_admin_tab  # noqa: E402
from app.ui.patient_tab import build_tab as build_patient_tab  # noqa: E402

BACKEND_URL = os.getenv("HF_SPACE_BACKEND_URL", "http://localhost:8000")

# ---------------------------------------------------------------------------
# Brand assets — the illustrated quill mascot (ported from design_handoff ui.jsx)
# ---------------------------------------------------------------------------

QUILL_SVG = """
<svg width="22" height="22" viewBox="0 0 32 32" fill="none">
  <defs>
    <linearGradient id="qfeather" x1="6" y1="4" x2="26" y2="26" gradientUnits="userSpaceOnUse">
      <stop stop-color="#eaf4ff"/><stop offset="1" stop-color="#bcd9ff"/>
    </linearGradient>
  </defs>
  <path d="M25.5 5.2C18 4.4 9.6 8.2 7.4 16.8c-.7 2.6-.5 5 .2 6.9L23 8.3c.5-.5 1.3.2.9.8L9.9 24.6c1.8.8 4.2 1 6.8.3 8.6-2.3 12.4-10.8 11.6-18.3a1.4 1.4 0 0 0-2.8-.4Z"
    fill="url(#qfeather)" stroke="#ffffff" stroke-width="0.8" stroke-linejoin="round"/>
  <path d="M23.6 8.2 9 23.4" stroke="#5b8fe0" stroke-width="1.1" stroke-linecap="round"/>
  <path d="M22 10.5l-3.2-.5M19.4 13.2l-3.4-.7M16.6 16l-3.5-.6M13.8 18.8l-3.3-.5" stroke="#7fa9e8" stroke-width="0.9" stroke-linecap="round"/>
  <path d="M9 23.4 6.2 26.2" stroke="#dbeaff" stroke-width="1.6" stroke-linecap="round"/>
  <circle cx="5.4" cy="27" r="1.5" fill="#7dd3fc"/>
</svg>
"""

# ---------------------------------------------------------------------------
# Theme — blue clinical palette + the handoff font stack
# ---------------------------------------------------------------------------

THEME = gr.themes.Soft(
    primary_hue=gr.themes.colors.blue,
    secondary_hue=gr.themes.colors.sky,
    neutral_hue=gr.themes.colors.slate,
    font=[
        gr.themes.GoogleFont("Plus Jakarta Sans"),
        gr.themes.GoogleFont("Inter"),
        "system-ui",
        "sans-serif",
    ],
    radius_size=gr.themes.sizes.radius_md,
    spacing_size=gr.themes.sizes.spacing_md,
).set(
    body_background_fill="#f5f8fe",
    body_background_fill_dark="#060c1c",
    block_background_fill="#ffffff",
    block_background_fill_dark="#0f1b34",
    block_border_color="#dce6f5",
    block_border_color_dark="#21345c",
    block_border_width="1px",
    block_radius="14px",
    block_shadow="0 1px 2px rgba(11,31,68,.05)",
    block_label_text_color="#44567a",
    block_label_text_color_dark="#adbcd6",
    block_label_text_weight="650",
    block_title_text_color="#0b1f44",
    block_title_text_color_dark="#eaf1ff",
    block_title_text_weight="700",
    button_large_radius="9px",
    button_small_radius="9px",
    button_primary_background_fill="#2563eb",
    button_primary_background_fill_hover="#1d4ed8",
    button_primary_text_color="#ffffff",
    button_primary_border_color="#2563eb",
    button_secondary_background_fill="#ffffff",
    button_secondary_background_fill_hover="#eef4ff",
    button_secondary_border_color="#cbd9ee",
    button_secondary_text_color="#0b1f44",
    input_background_fill="#ffffff",
    input_background_fill_dark="#0f1b34",
    input_border_color="#cbd9ee",
    input_border_color_dark="#2c4170",
    input_border_color_focus="#3b82f6",
    input_radius="9px",
)

# ---------------------------------------------------------------------------
# Global CSS — tokens (ported from styles.css) + chrome + Gradio mappings
# ---------------------------------------------------------------------------

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600;700&family=Newsreader:ital,wght@1,500;1,600&family=JetBrains+Mono:wght@500;600;700&display=swap');

:root {
  --blue-700:#1d4ed8; --blue-600:#2563eb; --blue-500:#3b82f6; --sky-500:#38bdf8;
  --grad-primary:linear-gradient(135deg,#2f6bff 0%,#1538a6 100%);
  --grad-mascot:linear-gradient(150deg,#3b82f6 0%,#1e3a8a 95%);
  --grad-header:linear-gradient(135deg,#0c2456 0%,#0a1730 70%);
  --canvas:#f5f8fe; --canvas-2:#eef4ff; --surface:#ffffff; --surface-2:#f6f9ff; --surface-3:#eef4ff;
  --border:#dce6f5; --border-2:#cbd9ee;
  --ink:#0b1f44; --ink-2:#44567a; --muted:#6b7d9e; --muted-2:#93a3c0;
  --success:#0ea672; --success-bg:#d6f5e8; --warning:#e08a00; --warning-bg:#fdeecb;
  --danger:#e23b48; --danger-bg:#fbdfe1; --info-bg:#dcebff;
  --accent-soft:#e2edff; --accent-softer:#eef4ff;
  --sh-sm:0 1px 2px rgba(11,31,68,.05); --sh-glow:0 6px 16px -8px rgba(37,99,235,.42);
  --r-sm:9px; --r-md:11px; --r-lg:14px;
  --font-head:'Plus Jakarta Sans',system-ui,sans-serif;
  --font-body:'Inter',system-ui,sans-serif;
  --font-serif:'Newsreader',Georgia,serif;
  --font-mono:'JetBrains Mono',ui-monospace,'SF Mono',monospace;
}
.dark, .gradio-container.dark {
  --canvas:#060c1c; --canvas-2:#0a1428; --surface:#0f1b34; --surface-2:#142242; --surface-3:#18294c;
  --border:#21345c; --border-2:#2c4170;
  --ink:#eaf1ff; --ink-2:#adbcd6; --muted:#7d8eb0; --muted-2:#5d6e90;
  --success-bg:rgba(14,166,114,.16); --warning-bg:rgba(224,138,0,.16); --danger-bg:rgba(226,59,72,.18);
  --info-bg:rgba(59,130,246,.16); --accent-soft:rgba(59,130,246,.16); --accent-softer:rgba(59,130,246,.09);
  --grad-header:linear-gradient(135deg,#0e2350 0%,#07101f 75%);
}

/* ---------- canvas ---------- */
.gradio-container {
  max-width: 1480px !important; margin: 0 auto !important; padding: 0 28px 64px !important;
  font-family: var(--font-body) !important;
  background:
    radial-gradient(760px 320px at 88% -6%, rgba(56,189,248,.10), transparent 62%),
    radial-gradient(620px 300px at 6% -2%, rgba(37,99,235,.07), transparent 58%),
    var(--canvas) !important;
}

/* ---------- app-nav chrome ---------- */
#appnav {
  position: sticky; top: 0; z-index: 50; backdrop-filter: blur(12px);
  margin: 0 -28px 4px !important; padding: 8px 28px !important;
  gap: 12px !important; align-items: center !important; flex-wrap: nowrap !important;
  background: color-mix(in srgb, var(--canvas) 82%, transparent) !important;
  border-bottom: 1px solid var(--border); border-radius: 0 !important;
}
#appnav-brand { flex: 1 1 auto; min-width: 0; }
.appnav-in { display: flex; align-items: center; gap: 16px; min-height: 54px; width: 100%; }
#theme-toggle {
  flex: 0 0 auto; min-width: 42px !important; max-width: 46px; height: 40px;
  border-radius: 9px !important; background: var(--surface) !important;
  border: 1px solid var(--border) !important; color: var(--ink-2) !important;
  font-size: 17px !important; padding: 0 !important; box-shadow: none !important;
}
#theme-toggle:hover { background: var(--surface-3) !important; color: var(--ink) !important; }
.appbrand { display: flex; align-items: center; gap: 10px; font-family: var(--font-head);
  font-weight: 800; font-size: 18px; letter-spacing: -.03em; color: var(--ink); }
.appbrand .ai { color: var(--blue-600); }
.mascot-badge { width: 32px; height: 32px; border-radius: 9px; background: var(--grad-mascot);
  display: grid; place-items: center; box-shadow: inset 0 1px 0 rgba(255,255,255,.3); flex-shrink: 0; }
.navright { margin-left: auto; display: flex; align-items: center; gap: 10px; }
.status-pill { display: inline-flex; align-items: center; gap: 7px; background: var(--surface);
  border: 1px solid var(--border); color: var(--ink-2); font-size: 11.5px; font-weight: 600;
  padding: 6px 11px; border-radius: 999px; font-family: var(--font-mono); letter-spacing: -.02em; }
.live-dot { width: 7px; height: 7px; border-radius: 999px; background: #14b86e; animation: cqpulse 2s infinite; }
@keyframes cqpulse { 0%{box-shadow:0 0 0 0 rgba(20,184,110,.5)} 70%{box-shadow:0 0 0 6px rgba(20,184,110,0)} 100%{box-shadow:0 0 0 0 rgba(20,184,110,0)} }

/* ---------- top tabs styled as the nav-tabs ---------- */
#cliniq-tabs > .tab-nav { border: none !important; gap: 4px; margin: 4px 0 14px; }
#cliniq-tabs > .tab-nav button {
  font-family: var(--font-head); font-weight: 600; font-size: 14px; color: var(--ink-2);
  background: transparent; border: 1px solid transparent !important; border-radius: 9px;
  padding: 8px 16px; transition: background .15s, color .15s;
}
#cliniq-tabs > .tab-nav button:hover { background: var(--surface-3); color: var(--ink); }
#cliniq-tabs > .tab-nav button.selected {
  background: var(--accent-soft); color: var(--blue-700); border-color: transparent !important;
}

/* ---------- page header (.intro) ---------- */
.cq-intro { display: flex; align-items: center; gap: 14px; margin: 6px 0 14px; padding: 0 !important;
  background: transparent !important; border: none !important; box-shadow: none !important; }
.cq-intro .intro-icon { width: 46px; height: 46px; border-radius: 12px; flex-shrink: 0;
  background: var(--accent-soft); color: var(--blue-700); display: grid; place-items: center; }
.cq-intro h2 { font-family: var(--font-head); font-size: 27px; font-weight: 800; letter-spacing: -.025em;
  color: var(--ink); margin: 0; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.cq-intro h2 .serif-i { font-family: var(--font-serif); font-style: italic; font-weight: 500; color: var(--blue-600); }
.cq-intro p { margin: 5px 0 0; color: var(--ink-2); font-size: 14.5px; line-height: 1.55; max-width: 72ch; }
.ship-tag { font-family: var(--font-head); font-size: 10.5px; font-weight: 700; letter-spacing: .05em;
  text-transform: uppercase; color: var(--success); background: var(--success-bg); padding: 3px 9px; border-radius: 999px; }

/* ---------- sub-nav (nurse nested tabs) ---------- */
#nurse-subnav > .tab-nav { display: inline-flex !important; gap: 4px; background: var(--surface);
  border: 1px solid var(--border) !important; padding: 5px; border-radius: 12px; box-shadow: var(--sh-sm);
  margin-bottom: 16px; }
#nurse-subnav > .tab-nav button { font-family: var(--font-head); font-weight: 600; font-size: 13.5px;
  color: var(--ink-2); background: transparent; border: none !important; padding: 9px 16px; border-radius: 8px; }
#nurse-subnav > .tab-nav button:hover { background: var(--surface-3); color: var(--ink); }
#nurse-subnav > .tab-nav button.selected { background: var(--accent-soft); color: var(--blue-700); }

/* ---------- Gradio component polish ---------- */
.gradio-container .block { border-radius: var(--r-lg); }
.gradio-container button.primary { box-shadow: var(--sh-glow); font-family: var(--font-head); letter-spacing: -.01em; }
.gradio-container button.primary:active { transform: translateY(1px); }
.gradio-container input, .gradio-container textarea, .gradio-container select { font-family: var(--font-body); }
.gradio-container label span { font-family: var(--font-head); }

/* mono for IDs / code */
.gradio-container code, .gradio-container .cm-editor { font-family: var(--font-mono) !important; }

/* tables -> .tbl look */
.gradio-container table { border-collapse: collapse; font-size: 13px; }
.gradio-container table thead th {
  background: var(--surface-2) !important; text-transform: uppercase; letter-spacing: .04em;
  font-family: var(--font-head); font-weight: 700; font-size: 11.5px !important; color: var(--muted) !important;
}
.gradio-container table tbody tr:nth-child(even) { background: var(--surface-2); }

/* ---------- footer ---------- */
#cq-footer { text-align: center; color: var(--muted); font-size: 12.5px; margin-top: 26px;
  padding-top: 20px; border-top: 1px solid var(--border); }
#cq-footer .caps { display: inline-flex; gap: 16px; flex-wrap: wrap; justify-content: center; margin-top: 8px; }
#cq-footer .caps span { color: var(--ink-2); font-weight: 600; }
#cq-footer b { color: var(--blue-600); }
"""

BRAND_HTML = f"""
<div class="appnav-in">
  <span class="appbrand"><span class="mascot-badge">{QUILL_SVG}</span>Cliniq<span class="ai">AI</span></span>
  <span class="navright">
    <span class="status-pill"><span class="live-dot"></span>API online · v0.4</span>
  </span>
</div>
"""

# Runtime light/dark toggle. Gradio drives dark mode via a `dark` class on
# <body>; we flip it (+ <html>) and persist the choice to localStorage.
TOGGLE_JS = """() => {
  const d = !document.body.classList.contains('dark');
  document.body.classList.toggle('dark', d);
  document.documentElement.classList.toggle('dark', d);
  const b = document.querySelector('#theme-toggle button') || document.querySelector('#theme-toggle');
  if (b) b.textContent = d ? '\\u2600\\ufe0f' : '\\ud83c\\udf19';
  try { localStorage.setItem('cq_theme', d ? 'dark' : 'light'); } catch (e) {}
}"""

# Restore the persisted theme on load and sync the toggle glyph.
THEME_INIT_JS = """() => {
  try {
    const t = localStorage.getItem('cq_theme');
    if (t === 'dark') { document.body.classList.add('dark'); document.documentElement.classList.add('dark'); }
    else if (t === 'light') { document.body.classList.remove('dark'); document.documentElement.classList.remove('dark'); }
    const d = document.body.classList.contains('dark');
    const b = document.querySelector('#theme-toggle button') || document.querySelector('#theme-toggle');
    if (b) b.textContent = d ? '\\u2600\\ufe0f' : '\\ud83c\\udf19';
  } catch (e) {}
}"""

FOOTER_HTML = (
    '<div id="cq-footer">🪶 <b>CliniqAI</b> — clinical operations, intelligently drafted.'
    '<div class="caps"><span>Documentation</span><span>Appointments</span>'
    "<span>Handover</span><span>Roster</span><span>Discharge</span></div></div>"
)


def build_app() -> gr.Blocks:
    with gr.Blocks(
        title="CliniqAI", theme=THEME, css=CSS, js=THEME_INIT_JS, fill_width=True
    ) as demo:
        with gr.Row(elem_id="appnav"):
            gr.HTML(BRAND_HTML, elem_id="appnav-brand")
            theme_btn = gr.Button("🌙", elem_id="theme-toggle", scale=0, min_width=46)
        with gr.Tabs(elem_id="cliniq-tabs"):
            with gr.Tab("🩺  Doctor"):
                build_doctor_tab()
            with gr.Tab("💬  Patient"):
                build_patient_tab()
            with gr.Tab("📋  Nurse & Admin"):
                build_nurse_admin_tab()
        gr.HTML(FOOTER_HTML)
        theme_btn.click(fn=None, js=TOGGLE_JS)
    return demo


if __name__ == "__main__":
    build_app().launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,
    )
