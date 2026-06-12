# CliniqAI — UI Revamp

A professional, clinical redesign of the Gradio interface. The goal was to move
from the default Gradio look to a polished, hospital-grade product feel —
inspired by clean B2B/SaaS layouts (teal accent, card surfaces, generous
spacing) — while keeping **100% Gradio** and changing **zero agent logic**.

> Mascot: a **quill** (🪶) — the "CliniqAI drafts your clinical notes" metaphor —
> rendered as an inline SVG badge in the header.

---

## 1. Design language

| Token | Value | Use |
|-------|-------|-----|
| Primary accent | `#0d9488` → `#0891b2` (teal → cyan gradient) | Buttons, links, mascot, active tab |
| Accent (mascot) | `#14b8a6` → `#0891b2` | Quill badge background |
| Text (primary) | `#0f172a` (slate-900) | Headings, wordmark |
| Text (secondary)| `#475569` / `#64748b` (slate-600/500) | Body, captions |
| Surface | `#ffffff` | Cards, inputs |
| Background | `#f8fafc` (slate-50) | Page canvas |
| Border | `#e2e8f0` (slate-200) | Card / input borders |
| Status (live) | `#10b981` (emerald-500) | "API online" dot |
| Font | **Inter**, system-ui fallback | Whole app |
| Radius | 12–18px | Cards, buttons, pills |

**Why teal/slate:** teal reads as *clinical / medical / trustworthy* and doubles
as the reference design's accent, while slate-on-white keeps the long data tables
(roster, discharge, handover) calm and readable.

Dark mode is supported via `.dark` overrides (slate-900 canvas, teal accents
preserved).

---

## 2. What changed

### New branded header
- Inline **SVG quill mascot** in a teal gradient badge.
- `Cliniq` + teal `AI` wordmark, with tagline *"Clinical operations,
  intelligently drafted — for modern hospitals."*
- A live **status pill** showing the backend API URL with a pulsing green dot.

### Top navigation
- The three tabs (**🩺 Doctor · 💬 Patient · 📋 Nurse & Admin**) are restyled
  from default Gradio tabs into a **pill-style nav** with hover and active states.

### Section intros
- Each tab's intro is now a **left-accent-bar card** (`.cliniq-intro`) instead of
  a bare `# H1`, giving every tab a consistent, scannable lead-in.

### Components
- **Primary buttons**: teal→cyan gradient with hover shading.
- **Cards / blocks / inputs**: white surfaces, soft slate borders, subtle shadow,
  rounded corners — applied globally via the theme so every existing component
  (DataFrames, chatbot, audio, textboxes) inherits the look with no per-widget
  edits.
- **Footer**: a quiet branded strip listing the five capability areas.

---

## 3. How it's implemented

All styling is centralized so the three per-person tab files stay focused on
their own logic.

```
deploy/hf_space/app.py        ← theme + global CSS + header/footer + mascot SVG
app/ui/doctor_tab.py          ← intro restyled to .cliniq-intro card
app/ui/patient_tab.py         ← intro restyled; removed stray inner theme
app/ui/nurse_admin_tab.py     ← intro restyled to .cliniq-intro card
```

- **Theme**: a `gr.themes.Soft(...)` built on `teal / cyan / slate` hues + Inter,
  then `.set(...)` overrides for backgrounds, borders, shadows, and the gradient
  primary button. The **top-level `gr.Blocks` theme governs every nested tab**,
  so it applies app-wide.
- **CSS**: a single stylesheet string passed to `gr.Blocks(css=...)`. Selectors
  target stable Gradio structure (`.gradio-container`, `#cliniq-tabs > .tab-nav`)
  plus our own `elem_id` / `elem_classes` hooks (`#cliniq-header`,
  `.cliniq-intro`, `#cliniq-footer`).
- **Mascot**: the Lucide *feather* icon (MIT) inlined as SVG — no asset hosting,
  crisp at any size, recolors with the theme.

No new dependencies. Still pure Gradio.

---

## 4. Before → after

| | Before | After |
|--|--------|-------|
| Header | `# 🪶 CliniqAI` markdown line | Branded header card: quill mascot badge, wordmark, tagline, live API pill |
| Tabs | Default Gradio tab bar | Pill nav with hover / active accent |
| Palette | Default Gradio Soft (indigo) | Clinical teal + slate, white cards |
| Tab intros | Plain `# H1` + paragraph | Accent-bar intro cards |
| Buttons | Default solid | Teal→cyan gradient primaries |
| Font | Gradio default | Inter |

---

## 5. Run it

```bash
make up && make migrate                              # DB up + schema (once)
PYTHONHASHSEED=0 uv run python scripts/seed_demo.py  # demo data (once)
uv run python deploy/hf_space/app.py                 # UI on http://localhost:7860
```

Open **http://localhost:7860**. The styling ships to the Hugging Face Space
automatically (it's all in `deploy/hf_space/app.py`).

---

## 6. Notes & future polish

- The redesign is presentation-only — **no agent, API, or data-flow logic was
  touched**, so it's safe to merge alongside feature work.
- Possible next steps: per-tab capability icons in the body, a compact "draft
  confidence" badge component, skeleton loaders during agent calls, and a
  light/dark toggle in the header.
