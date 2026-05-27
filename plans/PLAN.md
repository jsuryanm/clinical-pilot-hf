# CliniqAI — Master Build Plan

> A 3-person, parallel-track plan to ship the Week 1 + Week 2 MVP and lay the rails for the post-hackathon agents. Optimised so **Persons A, B, and C never block each other**.

---

## 1. How the work is split

The seven CliniqAI agents and their supporting infrastructure cut along three natural seams. Each person owns one seam end-to-end (data layer → agent → API → UI tab). That way no one is waiting on anyone else to "finish their part first."

| Person | Theme | Owns |
|---|---|---|
| **Person A — "Doctor Brain"** | Knowledge & documentation | Documentation Agent, Wiki Maintenance Agent, LLM Wiki, ChromaDB + BM25 RAG, Whisper, Doctor Gradio tab, RAGAS evals |
| **Person B — "Patient Flow"** | Patient-facing automation | Appointment Agent, Clerical Agent, Discharge Agent, WhatsApp + Gmail + Calendar integrations, Celery reminders, Patient Gradio tab |
| **Person C — "Ops Core"** | Platform & coordination | Orchestrator, LangGraph state + shared Pydantic contracts, LiteLLM routing, Rostering Agent, Handover Agent, FastAPI backend, Postgres schema, Langfuse, Docker / AWS / HF Spaces deploy, Nurse + Admin Gradio tabs |

Each person has their own task file:

- `PLAN_PERSON_A.md`
- `PLAN_PERSON_B.md`
- `PLAN_PERSON_C.md`

---

## 2. The "no-blocking" contract

To let everyone work in parallel from Day 1, we lock three things on **Day 0** (a 90-minute kickoff meeting). After that, anyone can move at full speed.

### 2.1. Shared Pydantic contracts (Person C publishes)

Person C ships a single file, `app/contracts.py`, on Day 0 with **stub** Pydantic models for every cross-agent payload:

```python
# app/contracts.py — frozen on Day 0; additive-only changes after that
class CliniqState(TypedDict): ...           # LangGraph shared state
class SOAPNoteDraft(BaseModel): ...          # Person A returns this
class BookingResult(BaseModel): ...          # Person B returns this
class RosterResult(BaseModel): ...           # Person C returns this
class HandoverBrief(BaseModel): ...          # Person C returns this
class DischargeCoordination(BaseModel): ...  # Person B returns this
class CommunicationDraft(BaseModel): ...     # Person B returns this
class RoutingDecision(BaseModel): ...        # Person C (Orchestrator) returns this
class PatientWikiPageRef(BaseModel): ...     # Person A owns the wiki; A and B both read
```

Rule: **fields can only be added, never renamed or removed**, until the demo. If a field must change, post in the team channel; the other two have 24h to ack.

### 2.2. Mock services (everyone stubs the other two)

Each person ships a `mocks/` module that returns realistic fake payloads for their agent. The other two import this until the real thing is wired:

```
app/agents/documentation/mocks.py     # Person A — returns canned SOAPNoteDraft
app/agents/appointment/mocks.py       # Person B — returns canned BookingResult
app/agents/roster/mocks.py            # Person C — returns canned RosterResult
```

This means Person C can demo the orchestrator routing to a SOAP draft on Day 2 without Whisper being done, and Person B can demo a booking → calendar flow without the real orchestrator.

### 2.3. Shared dev environment

Person C ships a `docker-compose.dev.yml` on Day 0 with Postgres, Redis, and Langfuse running locally on fixed ports. Everyone runs `docker compose up` and gets the same backing services. No "works on my machine."

---

## 3. The repository layout (frozen Day 0)

```
clinical-pilot-hf/
├── app/
│   ├── contracts.py             # Person C — shared Pydantic models
│   ├── state.py                 # Person C — LangGraph CliniqState
│   ├── orchestrator.py          # Person C
│   ├── llm/
│   │   └── router.py            # Person C — LiteLLM router
│   ├── agents/
│   │   ├── documentation/       # Person A
│   │   ├── wiki/                # Person A
│   │   ├── appointment/         # Person B
│   │   ├── clerical/            # Person B
│   │   ├── discharge/           # Person B
│   │   ├── roster/              # Person C
│   │   └── handover/            # Person C
│   ├── retrieval/
│   │   ├── chroma_index.py      # Person A
│   │   └── bm25_index.py        # Person A
│   ├── integrations/
│   │   ├── whatsapp.py          # Person B
│   │   ├── calendar_mcp.py      # Person B
│   │   ├── gmail_mcp.py         # Person B
│   │   └── drive_mcp.py         # Person C
│   ├── db/
│   │   ├── models.py            # Person C — SQLAlchemy
│   │   └── migrations/          # Person C — Alembic
│   ├── api/
│   │   ├── main.py              # Person C — FastAPI entrypoint
│   │   └── routers/             # one file per person
│   └── ui/
│       ├── doctor_tab.py        # Person A
│       ├── patient_tab.py       # Person B
│       └── nurse_admin_tab.py   # Person C
├── wiki/                        # Person A — markdown pages
├── evals/
│   ├── ragas/                   # Person A
│   ├── appointment/             # Person B
│   └── orchestrator/            # Person C
├── infra/
│   ├── docker-compose.dev.yml   # Person C
│   ├── docker-compose.prod.yml  # Person C
│   └── terraform/               # Person C (post-hackathon)
├── deploy/
│   └── hf_space/                # Person C
│       ├── app.py               # imports tabs from all 3 people
│       └── requirements.txt
└── tests/
    ├── test_documentation/      # Person A
    ├── test_appointment/        # Person B
    └── test_orchestrator/       # Person C
```

Each person only writes inside their owned folders. The Gradio entrypoint (`deploy/hf_space/app.py`) is owned by C but only imports — no logic — so merge conflicts are rare.

---

## 4. Two-week MVP schedule

### Week 1 — Documentation slice (everyone shipping in parallel)

| Day | Person A | Person B | Person C |
|---|---|---|---|
| **0** (kickoff) | Confirm wiki schema, pick 5 conditions | Confirm WhatsApp sandbox plan | Ship contracts.py, state.py, docker-compose, FastAPI skeleton, LiteLLM router |
| **1** | Seed 5 wiki pages, ChromaDB index of ICD-10 sample | Calendar MCP "hello world", Twilio sandbox WhatsApp echo | Orchestrator routing to mock agents end-to-end |
| **2** | Whisper integration + audio upload | Booking happy-path against mocked calendar | Postgres schema, Alembic migrations, Langfuse wired |
| **3** | Documentation Agent v1 producing SOAPNoteDraft | Reminder Celery task + Redis queue | Rostering Agent v1 from a CSV of staff |
| **4** | Doctor Gradio tab (record → draft → approve) | Patient Gradio tab (chat → booking) | Nurse tab (roster view), Handover Agent v1 |
| **5** | RAGAS eval scaffolding, 10 golden notes | No-show waitlist logic | Wire all three tabs into HF Space, end-to-end demo runs |
| **6–7** | Polish, edge cases, demo dataset | Polish, edge cases, demo dataset | Polish, deploy to HF Space + AWS Free Tier |

### Week 2 — Appointments slice + hardening

| Day | Person A | Person B | Person C |
|---|---|---|---|
| **8** | Wiki Maintenance Agent (lint pass) | Gmail MCP for booking confirmations | Discharge Agent skeleton (B owns logic, C wires) |
| **9** | Guideline ingestion (5 fresh docs) | Post-discharge 72h follow-up Celery beat | Sick-call replacement logic in Rostering |
| **10** | Add 10 more wiki pages, vision support via Gemma | Clerical Agent referral letter draft | Auth (simple API key), audit log |
| **11** | RAGAS gate ≥ 0.85 on 50 notes | No-show evals < 8% on synthetic data | Langfuse dashboards, latency budgets |
| **12** | Doctor approval UX polish | Patient summary post-visit message | Roster fairness eval, handover prioritisation eval |
| **13** | Demo script: 3-case clinical walkthrough | Demo script: WhatsApp booking + 72h follow-up | Demo script: full shift handover + discharge |
| **14** | Joint dress rehearsal, freeze, record submission video | | |

### Post-hackathon (in priority order)

1. **Discharge Agent** to production (B leads, C wires triggers)
2. **Post-discharge follow-up** automation (B)
3. **Insurance / referral** flow (B)
4. **ABDM** integration — ABHA linking, HFR/HPR registration (C, with policy input from A)
5. **Local Ollama** fallback path validated end-to-end (C)
6. **Multi-hospital tenancy** (C)

---

## 5. Cross-cutting decisions (locked on Day 0)

| Decision | Choice | Why |
|---|---|---|
| Python version | 3.12 | Matches stack table; type-hint syntax |
| Package manager | `uv` | Fast, lockfile-native, plays well with HF Spaces |
| Lint / format | `ruff` + `ruff format` | One tool, fast |
| Pre-commit | `ruff`, `pytest -k smoke`, `mypy --strict app/contracts.py` | Contracts file gets strict typing; rest is best-effort |
| Branching | `trunk-based`, short-lived feature branches, PR review by one other person | 3-person team, no point in heavyweight gitflow |
| Secrets | `.env.local` (gitignored), `infra/.env.example` checked in | Standard |
| LLM call budget | All calls go through `app/llm/router.py` — never call SDKs directly | One place to swap Groq → OpenRouter → Ollama |
| Logging | `structlog` JSON to stdout, Langfuse for LLM traces | Standard |
| Patient data in repo | **Synthetic only.** Never commit a real PHI byte. | DPDPA + repo is public |

---

## 6. Definition of Done (per agent)

An agent is "done" only when **all six** are true:

1. Returns a Pydantic model from `app/contracts.py` — no dicts, no strings
2. Has a `mocks.py` returning a realistic instance for the other two
3. Has a unit test (`tests/test_<agent>/test_happy_path.py`)
4. Emits a Langfuse trace on every call
5. Has a one-screen Gradio surface (or contributes to one)
6. Has at least one eval row (RAGAS, golden output, or numeric metric)

---

## 7. Risk register

| Risk | Owner | Mitigation |
|---|---|---|
| Whisper accuracy on Indian accents / code-mixed Hindi-English | A | Test on AI4Bharat IndicVoices sample early; fall back to Whisper large-v3 + post-prompt cleanup |
| WhatsApp Business API approval delays | B | Develop against Twilio sandbox; production number is post-hackathon |
| Groq free-tier rate limits during demo | C | LiteLLM auto-fallback to OpenRouter Gemma; offline Ollama as last resort |
| LangGraph state schema churn | C | Contracts.py is additive-only; deprecate fields with a comment, never delete |
| HF Spaces cold start on demo day | C | Keep Space warm with a cron ping in last 24h |
| One person sick / down | All | Each person's `mocks.py` keeps the demo runnable without them |

---

## 8. What to read next

- `PLAN_PERSON_A.md` — Doctor Brain track
- `PLAN_PERSON_B.md` — Patient Flow track
- `PLAN_PERSON_C.md` — Ops Core track
- `MARKET_ANALYSIS.md` — Market sizing, competition, positioning
- `MASCOT.md` — Mascot proposal + Claude generation prompt
