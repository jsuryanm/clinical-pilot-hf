# CliniqAI — Design Context

A single-source design brief for generating UI, branding, and visual design for
**CliniqAI**. Hand this file to a designer (or a design-generation AI) to get
on-brand mockups, components, or a full frontend without needing the codebase.

---

## 1. The product in one line

> **CliniqAI** — an AI co-pilot that handles the *administrative* layer of
> hospital work (documentation, appointments, rostering, handover, discharge) so
> doctors and nurses get their time back. **Clinicians stay in control of every
> clinical decision.**

**Context:** built for Indian hospitals, where doctors spend 2–3 hours/day on
paperwork, nurses build rosters by hand, and patients are discharged hours late
because departments wait on each other. CliniqAI automates the mechanical work —
never the medical judgment.

**Tagline:** *"Clinical operations, intelligently drafted — for modern hospitals."*

---

## 2. Brand identity

| Aspect | Direction |
|--------|-----------|
| **Name** | CliniqAI — wordmark sets `Cliniq` in slate-900 and `AI` in teal. |
| **Mascot / logo** | A **quill** 🪶 (feather pen) — the "drafts your notes for you" metaphor. Currently a Lucide *feather* SVG inside a teal→cyan rounded badge. Friendly, light, precise — not a cartoon. |
| **Personality** | Calm, competent, trustworthy, fast. A senior resident who does your paperwork flawlessly — not a flashy chatbot. |
| **Voice & tone** | Plain, confident, clinical-clean. Short labels. No hype, no emoji-spam. Status is always explicit ("Draft ready", "API online"). |
| **Aesthetic reference** | Modern clinical B2B SaaS — think a calmer, hospital-tinted version of a clean dev-tool landing page: teal accent, white cards, lots of breathing room, subtle shadows. |

### Design principles
1. **Trust over flash.** This is healthcare. Favor legibility, whitespace, and
   restraint over gradients-everywhere.
2. **Doctor-in-the-loop, visibly.** Every AI output is a *draft* the human edits
   and approves. Surface confidence, citations, and an audit trail.
3. **Speed is the feature.** The UI should feel instant and get out of the way;
   show progress, never a blank screen.
4. **One product, three audiences.** Doctor, Patient, and Nurse/Admin surfaces
   share one design system but differ in density and tone.

---

## 3. Design tokens

The current implementation already uses these — reuse them for consistency.

### Color
| Role | Hex | Notes |
|------|-----|-------|
| Primary / accent | `#0d9488` (teal-600) | Buttons, links, active states |
| Primary gradient | `#0d9488` → `#0891b2` | Primary buttons, mascot badge |
| Mascot badge | `#14b8a6` → `#0891b2` | Quill background |
| Text primary | `#0f172a` (slate-900) | Headings, wordmark |
| Text secondary | `#475569` (slate-600) | Body |
| Text muted | `#64748b` / `#94a3b8` | Captions, footer |
| Surface / card | `#ffffff` | Panels, inputs |
| Canvas / background | `#f8fafc` (slate-50) | Page |
| Border | `#e2e8f0` (slate-200) | Cards, inputs, dividers |
| Success / live | `#10b981` (emerald-500) | Online dot, "done" status |
| Warning | `#f59e0b` (amber-500) | "watch" priority, pending |
| Danger / urgent | `#ef4444` (red-500) | "urgent" priority, failed |
| Dark canvas | `#0b1220` | Dark-mode page |

Semantic status colors matter — the app is full of **priority** and **state**
(urgent/watch/stable, queued/in-progress/done/failed/awaiting-approval).

### Typography
- **Font:** Inter (system-ui fallback). Sans-serif throughout.
- **Scale:** wordmark ~27px/800; section titles ~17–18px/700; body ~13.5–14px;
  captions ~12px. Tight letter-spacing on the wordmark (`-0.025em`).
- **Monospace** for IDs / codes (patient ids `p-001`, draft ids `soap-8b1745b5`,
  ICD-10 codes `I10`, shift ids `sh-xxxx`).

### Shape & depth
- **Radius:** 12px buttons, 14–16px cards, 18px header, 999px pills.
- **Shadows:** very soft (`0 1px 2px rgba(15,23,42,.05)`); one elevated glow on
  the header (`0 14px 30px -18px rgba(13,148,136,.45)`).
- **Spacing:** generous; max content width ~1180px, centered.

---

## 4. Information architecture — three surfaces

One app, top-level tabs. Each is a distinct persona surface.

### 🩺 Doctor — Consultation Documentation
**User:** a physician finishing a consult.
**Job:** turn a spoken/typed consult into an approved SOAP note in <60s.
**Layout:** two-column. Left = inputs, right = editable draft.
- **Inputs (left):** patient ID, audio record/upload (mic + file), or paste
  transcript; primary "Draft SOAP note" button.
- **Draft (right):** status banner, four editable fields — **S**ubjective,
  **O**bjective, **A**ssessment, **P**lan — plus a citations/audit panel
  (confidence %, referral flag, ICD-10 candidates, source citations, model id),
  then **Approve** / **Reject**.
- **Key UX:** the four SOAP fields are the hero. Confidence + citations build
  trust. Approve writes to the patient's wiki page.

### 💬 Patient — Appointment Assistant (WhatsApp-style)
**User:** a patient (demo simulates WhatsApp; prod is Twilio).
**Job:** book / change / cancel an appointment conversationally.
**Layout:** a chat thread.
- Chat bubbles, a message box, **Send**, and **quick-action** chips
  (📅 Book · ❌ Cancel · 🔄 Reschedule).
- **Key UX:** should feel like a friendly messaging app, warmer and simpler than
  the clinician surfaces. Larger tap targets, conversational copy.

### 📋 Nurse & Admin — Operations Console
**User:** charge nurse / ward admin.
**Job:** run handover, rostering, discharge, and wiki health.
**Layout:** sub-tabs, data-table heavy.
- **Handover:** ward picker → "Generate brief" → a patient table ordered
  **urgent → watch → stable** (bed, priority, patient, one-liner, pending
  actions). Priority needs color coding.
- **Roster:** CSV path + day-window slider → 14-day roster table (shift, staff,
  role, start/end, replacement flag) + a fairness score + unresolved conflicts;
  a **sick-call replacement** sub-form.
- **Discharge queue:** patient ID → a live subtask table (5 parallel streams:
  summary, pharmacy, family notification, follow-up booking, billing) with
  status icons (✅ done, 🔄 in-progress, ⏳ queued, ❌ failed, 👁️ awaiting approval).
- **Wiki health:** a lint report of stale/broken knowledge pages.
- **Key UX:** dense but scannable. Status pills, monospace IDs, sticky table
  headers, quiet zebra rows.

---

## 5. Signature components to design well

These recur and define the product feel:

1. **Status banner** — inline result state ("✅ Draft ready", "⚠️ No LLM key",
   "❌ failed: …"). Color-coded, non-modal.
2. **Confidence + citation panel** — the trust device: a confidence %, a
   referral flag, ICD-10 chips, and a list of source citations (the audit
   trail). This is what makes an *AI draft* clinically acceptable.
3. **Priority / status pills** — urgent/watch/stable, and task states. Need a
   clear semantic color set.
4. **Data tables** — rosters, handover, discharge. Readability at 30–60 rows.
5. **Chat thread** — the patient surface; warmer styling than the rest.
6. **ID tokens** — monospace, copyable, subtly tinted.
7. **Branded header** — quill mascot badge + wordmark + tagline + a live
   "API online" status pill.

---

## 6. Primary user journeys

- **Document a consult:** open Doctor → upload audio → *Draft* → review S/O/A/P +
  citations → edit → *Approve* → written to patient wiki.
- **Book an appointment:** open Patient → "Book appointment tomorrow" → agent
  proposes a slot → confirm → reminder scheduled.
- **End-of-shift handover:** open Nurse & Admin → Handover → *Generate brief* →
  read prioritized patients → action the pending items.
- **Cover a sick call:** Roster → generate → copy a shift id → enter absent staff
  → *Find replacement* → table updates with the cover.

---

## 7. Clinical-safety UX rules (non-negotiable)

- Always label AI output as a **draft**; never auto-commit clinical content.
- Always show **where it came from** (citations) and **how sure** (confidence).
- Make **edit + approve** the obvious path; rejecting must be one click.
- Be conservative: low confidence and "referral suggested" must be visually
  loud, not buried.

---

## 8. Constraints & platform

- **Today:** the UI is built entirely in **Gradio** (Python), themeable via a
  custom theme + CSS. No JS framework. See [`UI_REVAMP.md`](UI_REVAMP.md) for the
  current implementation of the tokens above.
- **If designing a bespoke frontend:** keep the token set and IA above; the
  backend is a FastAPI service (JSON), so a React/Next frontend could consume it
  directly. Design for both light and dark.
- **Deploy target:** Hugging Face Spaces (demo) — keep assets inline/light.

---

## 9. Quick reference for a design prompt

> Design a clinical operations web app called **CliniqAI** for Indian hospitals.
> Mascot is a **quill** (feather pen) in a teal→cyan badge. Palette: teal `#0d9488`
> accent, slate-900 text, slate-50 canvas, white cards, soft slate borders,
> semantic red/amber/emerald for status. Font: Inter. Rounded (12–18px), soft
> shadows, generous spacing, ~1180px centered. Three surfaces: a **Doctor**
> documentation screen (two-column, editable SOAP note + confidence/citations),
> a **Patient** WhatsApp-style appointment chat, and a **Nurse & Admin** console
> (data-table-heavy: handover, roster, discharge queue with status pills). Tone:
> calm, trustworthy, fast — healthcare-grade, doctor-in-the-loop. Light + dark.
