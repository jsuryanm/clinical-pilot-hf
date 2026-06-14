# CliniqAI — Clinical Operations AI for Indian Hospitals

> Giving doctors and nurses back the hours they lose to paperwork, so they can spend that time on patients.

Built for the **[Hugging Face "Build Small" Hackathon](https://huggingface.co/build-small-hackathon)** — a suite of small, open, ≤32B models doing real hospital back-office work, with a human approving every decision that touches a patient.

> **Status note:** This README describes **what actually runs today**, verified against the code and test suite. The original planning document (which scoped only 3 agents as "shipping") is preserved as **[`README_OLD.md`](README_OLD.md)** for pitch/historical context. Since then, **all seven agents have been implemented.**

---

## The Problem

Indian doctors spend **2–3 hours every day** on documentation. Nurses build duty rosters by hand over half a day. Receptionists book appointments by phone. Patients leave **4–6 hours late** because pharmacy, billing, and family hand-offs all wait on each other.

None of this needs medical judgment. It is mechanical, repetitive, and automatable — and that is exactly the layer CliniqAI takes over, while clinicians stay in control of every clinical call.

**The design rule:** *Agents prepare. Humans decide.* No agent sends or files anything patient-facing without explicit human approval.

---

## What the App Is

A single **Gradio** web app with three role-based consoles, backed by a **FastAPI** service and a **LangGraph** multi-agent orchestrator. Seven agents share one typed state object and return validated **Pydantic** outputs, so everything is parseable, logged, and auditable.

```
        Doctor console        Patient console        Nurse & Admin console
              │                      │                        │
              └──────────────┬───────┴────────────┬───────────┘
                             ▼                     ▼
                        FastAPI  ───────►  LangGraph Orchestrator
                                                   │
   ┌──────────┬───────────┬──────────┬────────────┬───────────┬──────────┐
 Documentation  Appointment  Roster   Handover    Discharge   Clerical   Wiki
   ▼            ▼            ▼          ▼            ▼           ▼          ▼
        Retrieval (Chroma + BM25)  ·  PostgreSQL  ·  LLM router (Groq / OpenRouter / Ollama)
```

---

## What Actually Works Today

Legend: ✅ working & demoable · 🟡 works, needs an API key / external creds to go fully live · ⚙️ wired, depends on a build/seed step

| Capability | Status | Notes |
|---|---|---|
| **Doctor console — SOAP documentation** | ✅ | Paste a transcript (or record audio), get an editable SOAP draft with ICD-10 suggestions + citations, edit, then **Approve** to write it to the patient's wiki page. Falls back to a realistic **mock draft** if no LLM key is set, so it always demos. |
| **Audio transcription (Whisper)** | 🟡 | Groq-hosted `whisper-large-v3-turbo`; needs `GROQ_API_KEY`. Transcript paste works with no key. |
| **Patient console — appointment chat** | ✅ | Chat widget routes to the Appointment Agent: parses intent, finds a free slot, books it, and replies with a confirmation + 1/2/0 confirm-reschedule-cancel flow. |
| **Appointment booking + reminders** | ✅ | Slot-finding over a calendar; queues T-24h email + chat reminders via Celery. Uses a **local calendar fallback** so it runs offline. |
| **Nurse — shift handover brief** | ✅ | Generates a prioritised ward brief (urgent → watch → stable) with per-patient one-liners and pending actions. |
| **Admin — duty rostering** | ✅ | Greedy 14-day roster from a staff CSV (or demo data) in well under a second, with a fairness score; plus same-role, lowest-load **sick-call replacement**. |
| **Nurse — discharge coordination** | ✅ | Fans out **5 subtasks in parallel** (summary, pharmacy, family notify, follow-up booking, billing) and reports each one's status; failures are isolated. |
| **Wiki health — lint report** | ✅ | One click runs `lint_wiki()` over the public corpus: missing frontmatter, stale pages (>180d), broken `[[cross-refs]]`. Currently **0 issues** across the seeded corpus. |
| **Orchestrator routing** | ✅ | LangGraph state graph routes each request to the right agent (6 agent nodes + orchestrator). |
| **Knowledge retrieval (Chroma + BM25)** | ⚙️ | Hybrid search is wired behind one `search()` API; populate the index with `scripts/build_indices.py`. |
| **LLM routing** | ✅ | LiteLLM picks Groq / OpenRouter / Ollama per task; degrades to mocks when no provider is configured. |
| **Patient notifications (Telegram / WhatsApp)** | 🟡 | Telegram (free Bot API) and WhatsApp (Twilio) send paths exist; both no-op safely to a stub until credentials are set, so nothing crashes in a dry run. |
| **Observability (Langfuse)** | 🟡 | LLM + retrieval calls are traced when Langfuse keys are present. |

### Agents — all seven implemented

| Agent | Does |
|---|---|
| **Documentation** | Transcript → retrieves patient history + guidelines + ICD-10 → drafts a SOAP note with citations → writes to the patient wiki on approval. |
| **Appointment** | Parses booking/cancel/reschedule intent, checks availability, books, confirms, and schedules reminders. |
| **Rostering** | Builds a fair 14-day roster from a CSV; resolves sick calls in real time. |
| **Handover** | Produces a prioritised end-of-shift patient brief. |
| **Discharge** | Coordinates the 5-stream discharge fan-out in parallel. |
| **Clerical** | Drafts referral letters and post-visit summaries (human-approved). |
| **Wiki Maintenance** | Updates patient pages and lints the knowledge corpus for staleness / broken links. |

---

## How It Works

### 1. The knowledge layer — wiki + RAG, not just chunks
CliniqAI follows the **LLM-Wiki** pattern: structured markdown pages (one per patient, drug, condition, protocol) that the system keeps current and cross-linked, instead of blindly chunking documents. When a guideline changes you update the page and mark the old content superseded — so the next query reads a clean synthesis, not a blend of old and new. Large reference data (ICD-10 codes, formularies) lives in a **Chroma + BM25 hybrid index** for keyword-precise lookup. Structured operational data (appointments, rosters) lives in **PostgreSQL**.

### 2. The orchestration layer — typed, auditable agents
Every request enters the **LangGraph** graph, the orchestrator classifies it, and it flows to the owning agent. Each agent returns a validated Pydantic model (`SOAPNoteDraft`, `BookingResult`, `RosterResult`, `HandoverBrief`, `DischargeCoordination`, `CommunicationDraft`, …). State updates follow strict rules — lists append, scalars overwrite, no node mutates shared state directly.

### 3. The model layer — small, open, swappable
Tasks are routed by **LiteLLM**: heavy reasoning (SOAP notes, handover, discharge summaries) → a 32B-class model on **Groq**; high-frequency simple replies → a fast 8B model; offline → **Ollama** locally. Every model in the routing table is free and **≤32B parameters** — the spirit of the Build Small hackathon. If no provider is configured, the app serves realistic mocks so the UI still demos end-to-end.

### 4. The safety layer
Every clinical output is traceable to a source page or guideline, nothing patient-facing is sent without human approval, and all agent actions are traceable via Langfuse.

---

## Why It's Beneficial

Carried forward from the original product thesis — these are the targets the workflows are built to hit:

| Workflow | Today (manual) | With CliniqAI |
|---|---|---|
| SOAP note sign-off | 8–10 min/consult | **< 90 sec** review-and-approve |
| Duty roster generation | 3–5 hours | **< 5 min** (sub-second in practice) |
| Sick-call replacement | 30–60 min | **< 15 min** |
| Discharge → patient leaves | 4–6 hours | **< 1.5 hours** (parallel fan-out) |
| No-show rate | 15–20% | **< 8%** (reminders + waitlist) |

The compounding win: a doctor reclaiming ~2 hours/day is the equivalent of adding clinical capacity **without hiring** — the most expensive constraint in Indian healthcare — while the patient experience (faster discharge, fewer missed appointments, clearer summaries) improves at the same time.

---

## Demo / Run It Locally

**Prereqs:** Docker (for Postgres/Redis), and [`uv`](https://docs.astral.sh/uv/). The app runs with **no API keys** thanks to mock fallbacks; add keys to `.env.local` to go fully live.

```bash
# 1. Install deps into the uv-managed venv (Python 3.12)
uv sync

# 2. Bring up Postgres + Redis
docker compose -f infra/docker-compose.dev.yml up -d

# 3. Create the schema and seed demo data
uv run alembic -c infra/alembic.ini upgrade head
PYTHONHASHSEED=0 uv run python scripts/seed_demo.py

# 4. Launch the Gradio app  →  http://127.0.0.1:7860
uv run python deploy/hf_space/app.py
```

Then click through the three consoles:

- **Doctor** → paste a consult transcript → **Draft SOAP note** → edit → **Approve**.
- **Patient** → type *"Book an appointment for tomorrow"* → confirm with **1**.
- **Nurse & Admin** → **Handover** (Generate brief) · **Roster** (Generate roster, then Find replacement) · **Discharge queue** (Initiate discharge) · **Wiki health** (**Run lint**).

Optional live integrations (add to `.env.local`, then restart):
`GROQ_API_KEY` (LLM + Whisper) · `OPENROUTER_API_KEY` (fallback) · `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` (free patient notifications) · `LANGFUSE_*` (tracing).

To deploy: the same `deploy/hf_space/app.py` runs on **Hugging Face Spaces** — push, set secrets in the Spaces panel, done.

---

## Testing

```bash
PYTHONHASHSEED=0 uv run pytest -q
```

**64 tests pass** today — documentation, rostering, handover, clerical, orchestrator routing, integrations, and contracts suites are all green. The appointment and discharge happy-path tests currently error/fail due to a **mock-patching harness issue** (they patch names that are imported lazily inside functions, so `mock.patch` can't find them) — the underlying agent code is verified working via direct smoke tests; only the test wiring needs the patch target corrected.

---

## Tech Stack (as actually wired)

**Backend:** Python 3.12 · FastAPI · LangGraph (orchestration) · LiteLLM (model routing) · Pydantic v2 (typed outputs) · SQLAlchemy + Alembic + PostgreSQL · Celery + Redis (reminders).
**AI & retrieval:** Groq Whisper (`whisper-large-v3-turbo`) · ChromaDB + rank-bm25 (hybrid search) · Langfuse (tracing).
**Frontend:** Gradio (three consoles, one-command HF Spaces deploy).
**Integrations:** Google Calendar (with offline local-calendar fallback) · Gmail · Telegram Bot API · WhatsApp (Twilio).

---

## Repository Map

| Path | What's there |
|---|---|
| `app/agents/` | The seven agents (`documentation`, `appointment`, `roster`, `handover`, `discharge`, `clerical`, `wiki`) |
| `app/orchestrator.py` | LangGraph state graph + routing |
| `app/ui/` | Gradio consoles: `doctor_tab`, `patient_tab`, `nurse_admin_tab` |
| `app/retrieval/` | Chroma + BM25 indices behind `index_api.search()` |
| `app/integrations/` | Calendar, Gmail, Telegram, WhatsApp, Whisper |
| `app/llm/router.py` | LiteLLM task routing + mock fallback |
| `wiki/` | The markdown knowledge corpus (10 condition pages seeded) |
| `deploy/hf_space/app.py` | Gradio entrypoint (local + HF Spaces) |
| `scripts/` | `seed_demo.py`, `build_indices.py`, `fetch_data.sh` |
| `plans/`, `README_OLD.md` | Original planning docs and pitch context |

---

## Team

Built by:

- [@drumilhved](https://huggingface.co/drumilhved)
- [@someonesphantom](https://huggingface.co/someonesphantom)
- [@Jayasuryan0419](https://huggingface.co/Jayasuryan0419)

---

## Clinical Safety

- Every clinical recommendation is traceable to a specific wiki page or guideline source.
- No agent sends a patient-facing communication without human approval.
- Patient data is handled in line with India's **Digital Personal Data Protection Act (DPDPA)**; synthetic data only in this repo.
- Full audit trail of agent actions via Langfuse.
