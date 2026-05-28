# CliniqAI — Master Build Plan (Hackathon Scope)

> A 3-person, 2-week plan to ship **three agents** that solve the three biggest pain points doctors, nurses, and admins actually feel — and to architect (but not build) the rest so the demo can credibly say "coming soon."

---

## 0. Scope discipline — what we will and will not build

The original blueprint had seven agents and a wall of integrations. For a 2-week hackathon, that is a velocity trap. We are cutting hard.

### Ship in the demo (built end-to-end)

| Agent | Pain point | Owner |
|---|---|---|
| **Documentation Agent** | Doctor paperwork (2–3 hr/day) | Person A |
| **Appointment Agent** | Booking, reminders, no-shows | Person B |
| **Duty Rostering Agent** | 14-day roster + sick-call replacement | Person C |

### Architected but described as "coming soon" in the demo

Handover Agent · Discharge Agent (skeleton only, 2 of 5 streams as illustration) · Post-Discharge Follow-Up · Clerical Agent (referrals) · Wiki Maintenance Agent · Insurance/Referral automation · Antibiotic Stewardship.

Stubs (`api.py`, `mocks.py`) for these may stay in the repo so the orchestrator can route to them, but no real implementation, no UI surface, no eval.

### Explicitly cut — do not touch during the hackathon

| Feature | Why cut |
|---|---|
| Antibiotic Stewardship Agent | Needs culture-result integration + clinical validation. Too specialised for a demo. |
| ABDM / ABHA integration | Regulatory; requires API registration with the Indian government. |
| Multi-hospital tenancy | Architecture concern, not a demo concern. |
| WhatsApp Business API | Meta approval takes days. **Use a Gradio chat widget instead.** |
| OR-Tools constraint solver for rostering | Greedy heuristic is fast enough and easier to debug under time pressure. |
| Full discharge coordination (all 5 streams) | Show 2 streams (summary + family notification) working, describe the rest. |
| Insurance claim automation | Complex edge cases, not the core demo story. |

---

## 1. How the work is split

Each person owns one of the three shipping agents end-to-end (data → agent → API → UI tab). No one waits on anyone else after Day 0.

| Person | Theme | Owns |
|---|---|---|
| **Person A — "Doctor Brain"** | Documentation & knowledge | Documentation Agent, LLM Wiki (5 seeded conditions), ChromaDB + BM25 RAG, Whisper, Doctor Gradio tab, RAGAS evals |
| **Person B — "Patient Flow"** | Booking & reminders | Appointment Agent, Google Calendar MCP, Gmail MCP, Celery reminders, **Gradio chat widget** (in place of WhatsApp), Patient Gradio tab |
| **Person C — "Ops Core"** | Platform & rostering | Orchestrator, LangGraph state + shared Pydantic contracts, LiteLLM routing, **agent memory layer (LangGraph PostgresSaver + Mem0)**, Rostering Agent (greedy), FastAPI backend, Postgres schema, Langfuse, Docker / HF Spaces deploy, Nurse + Admin Gradio tabs |

Per-person files: `PLAN_PERSON_A.md`, `PLAN_PERSON_B.md`, `PLAN_PERSON_C.md`.

---

## 2. The "no-blocking" contract

Three things lock on **Day 0** (90-min kickoff). After that, full parallel.

### 2.1. Shared Pydantic contracts (Person C publishes)

`app/contracts.py` ships Day 0 with stub Pydantic models for every cross-agent payload:

```python
class CliniqState(TypedDict): ...           # LangGraph shared state
class SOAPNoteDraft(BaseModel): ...          # Person A returns this
class BookingResult(BaseModel): ...          # Person B returns this
class RosterResult(BaseModel): ...           # Person C returns this
class CommunicationDraft(BaseModel): ...     # Person B returns this
class RoutingDecision(BaseModel): ...        # Person C (Orchestrator)
class PatientWikiPageRef(BaseModel): ...     # Person A owns; A and B read
# HandoverBrief / DischargeCoordination stay as stubs for the "coming soon" agents
```

Rule: **fields can only be added, never renamed or removed**, until the demo.

### 2.2. Mock services

Each person ships a `mocks.py` returning realistic fake payloads. The other two import this until the real thing is wired:

```
app/agents/documentation/mocks.py     # Person A
app/agents/appointment/mocks.py       # Person B
app/agents/roster/mocks.py            # Person C
```

This means Person C can demo orchestrator routing to a SOAP draft on Day 2 without Whisper being done.

### 2.3. Shared dev environment

`docker-compose.dev.yml` on Day 0: Postgres, Redis, **Qdrant** (for Mem0 long-term memory), Langfuse on fixed ports. `make up` for everyone.

### 2.4. Agent memory layer (Person C ships, A and B consume)

Two-tier memory, both backed by services that are already in `docker-compose.dev.yml`:

- **LangGraph `PostgresSaver`** — short-term / thread checkpointing for graph resume, replay, time-travel debug, and multi-turn chat history. Built into LangGraph; backed by Postgres.
- **Mem0 (self-hosted OSS)** — long-term cross-session memory for learned preferences (doctor edits, patient comm prefs, scheduler history). Backed by Postgres + Qdrant.

A and B never import `mem0` or `langgraph.checkpoint` directly. They call `from app.memory.api import remember, recall`. See `PLAN_PERSON_C.md` §4.5 for the full design.

---

## 3. Repository layout (frozen Day 0)

```
clinical-pilot-hf/
├── app/
│   ├── contracts.py             # Person C
│   ├── state.py                 # Person C
│   ├── orchestrator.py          # Person C
│   ├── llm/router.py            # Person C — LiteLLM
│   ├── agents/
│   │   ├── documentation/       # Person A — BUILT
│   │   ├── appointment/         # Person B — BUILT
│   │   ├── roster/              # Person C — BUILT
│   │   ├── handover/            # stub only, "coming soon"
│   │   ├── discharge/           # stub only, "coming soon" (2-stream demo)
│   │   ├── clerical/            # stub only, "coming soon"
│   │   └── wiki/                # stub only, "coming soon"
│   ├── retrieval/
│   │   ├── chroma_index.py      # Person A
│   │   └── bm25_index.py        # Person A
│   ├── integrations/
│   │   ├── calendar_mcp.py      # Person B
│   │   ├── gmail_mcp.py         # Person B
│   │   ├── whisper.py           # Person A
│   │   └── drive_mcp.py         # Person C (optional, only if roster reads from Drive)
│   ├── db/
│   │   ├── models.py            # Person C — SQLAlchemy
│   │   └── migrations/          # Person C — Alembic
│   ├── api/
│   │   ├── main.py              # Person C — FastAPI
│   │   └── routers/             # one file per person
│   └── ui/
│       ├── doctor_tab.py        # Person A
│       ├── patient_tab.py       # Person B (Gradio chat widget lives here)
│       └── nurse_admin_tab.py   # Person C
├── wiki/                        # Person A — 5 seeded markdown pages
├── evals/
│   ├── ragas/                   # Person A
│   ├── appointment/             # Person B
│   └── orchestrator/            # Person C
├── infra/
│   └── docker-compose.dev.yml   # Person C
├── deploy/
│   └── hf_space/                # Person C — Gradio entrypoint
│       ├── app.py
│       └── requirements.txt
└── tests/
    ├── test_documentation/      # Person A
    ├── test_appointment/        # Person B
    └── test_orchestrator/       # Person C
```

The `whatsapp.py` integration stub may stay in the repo for the "coming soon" story but is **not wired** into any agent or UI.

`infra/docker-compose.prod.yml` and `infra/terraform/` are post-hackathon. HF Spaces is the only deploy target for the demo.

---

## 4. Two-week MVP schedule

### Week 1 — Documentation Agent (everyone shipping in parallel)

| Day | Person A (Doctor Brain) | Person B (Patient Flow) | Person C (Ops Core) |
|---|---|---|---|
| **0** (kickoff) | Confirm wiki schema, pick 5 conditions | Confirm Google Workspace dev account, Calendar + Gmail MCP reachable | Ship contracts.py, state.py, docker-compose, FastAPI skeleton, LiteLLM router |
| **1** | Seed 5 wiki pages, ChromaDB index of ICD-10 sample | Calendar MCP "hello world"; ship `mocks.fake_booking()` | Orchestrator routes to mock agents end-to-end |
| **2** | Whisper integration + audio upload | Booking happy-path against mocked calendar | Postgres schema, Alembic migrations, Langfuse wired |
| **3** | Documentation Agent v1 producing SOAPNoteDraft | Celery reminder task + Redis queue | Rostering Agent v1 (greedy) from staff CSV |
| **4** | Doctor Gradio tab (record → draft → approve) | Patient Gradio tab — **chat widget mimicking WhatsApp**, slot buttons | Nurse tab (roster view) |
| **5** | RAGAS eval scaffolding, 10 golden notes | Gmail MCP for booking confirmations | Wire all three tabs into HF Space, end-to-end demo runs |
| **6–7** | Polish, edge cases, demo dataset | Polish, edge cases, demo dataset | Polish, deploy to HF Space |

### Week 2 — Appointments hardening + Rostering polish

| Day | Person A | Person B | Person C |
|---|---|---|---|
| **8** | Add 5 more wiki pages (target 10) | Reminder copy localised (Hindi/English/Hinglish) via Llama-3.1-8B | Sick-call replacement logic in Rostering |
| **9** | RAGAS gate ≥ 0.85 on 30 notes | No-show / waitlist logic (synthetic eval) | Roster fairness eval |
| **10** | Doctor approval UX polish (citations as hover tooltips) | Patient post-visit summary (plain-language SMS-style) | Simple API key auth, audit log |
| **11** | Edge cases: long consults, code-mixed Hinglish | No-show eval < 8% on 200 synthetic bookings | Langfuse dashboards, latency budgets |
| **12** | Demo dataset: 3 rehearsed clinical cases | Demo dataset: booking + reminder + post-visit summary | Demo dataset: roster + sick-call replacement |
| **13** | **Joint dress rehearsal** + record submission video | | |
| **14** | Buffer / fixes from rehearsal | | |

### "Coming soon" (described in demo, not built)

Handover Agent · Discharge Agent (a 2-stream skeleton may be wired as a teaser) · Post-Discharge Follow-Up · Clerical Agent · Wiki Maintenance Agent · Insurance/Referral.

### Post-hackathon (in priority order)

1. **Handover Agent** to v1 (C)
2. **Discharge Agent** full 5-stream fan-out (B leads, C wires triggers)
3. **Post-Discharge 72h follow-up** (B)
4. **Clerical Agent** (referrals, FAQ routing) (B)
5. **Wiki Maintenance Agent** (A)
6. **Insurance / referral** flow (B)
7. **WhatsApp Business API** production number (B, once Meta approves)
8. **OR-Tools constraint solver** upgrade for rostering (C)
9. **Local Ollama** fallback path validated end-to-end (C)
10. **Antibiotic Stewardship** (needs culture-result integration + clinical advisor)

Explicitly out of scope even post-hackathon until there is a paying customer asking: ABDM / ABHA integration, multi-hospital tenancy.

---

## 5. Cross-cutting decisions (locked on Day 0)

| Decision | Choice | Why |
|---|---|---|
| Python version | 3.12 | Matches stack; type-hint syntax |
| Package manager | `uv` | Fast, lockfile-native, plays well with HF Spaces |
| Lint / format | `ruff` + `ruff format` | One tool, fast |
| Pre-commit | `ruff`, `pytest -k smoke`, `mypy --strict app/contracts.py` | Contracts get strict typing; rest best-effort |
| Branching | Trunk-based, short-lived feature branches, PR review by one other person | 3-person team |
| Secrets | `.env.local` (gitignored), `infra/.env.example` checked in | Standard |
| LLM call budget | All calls go through `app/llm/router.py` — never call SDKs directly | One place to swap Groq → OpenRouter → Ollama |
| Logging | `structlog` JSON to stdout, Langfuse for LLM traces | Standard |
| Patient data in repo | **Synthetic only.** Never commit a real PHI byte. | DPDPA + repo is public |
| Patient comms channel for demo | **Gradio chat widget** in `patient_tab.py` | WhatsApp Business API approval is days; the chat widget is visually identical for a demo |
| Roster solver | **Greedy heuristic.** No OR-Tools, no CP-SAT. | Faster to debug under time pressure |

---

## 6. Definition of Done (per shipping agent)

An agent counts as "done" only when **all six** are true:

1. Returns a Pydantic model from `app/contracts.py` — no dicts, no strings
2. Has a `mocks.py` returning a realistic instance for the other two
3. Has a unit test (`tests/test_<agent>/test_happy_path.py`)
4. Emits a Langfuse trace on every call
5. Has a one-screen Gradio surface (or contributes to one)
6. Has at least one eval row (RAGAS, golden output, or numeric metric)

"Coming soon" agents only need (1) and (2) so the orchestrator can route to them without breaking.

---

## 7. Risk register

| Risk | Owner | Mitigation |
|---|---|---|
| Whisper accuracy on Indian accents / code-mixed Hindi-English | A | Test on AI4Bharat IndicVoices sample early; fall back to Whisper large-v3 + post-prompt cleanup |
| Groq free-tier rate limits during demo | C | LiteLLM auto-fallback to OpenRouter Gemma; offline Ollama as last resort |
| LangGraph state schema churn | C | Contracts.py is additive-only; deprecate with a comment, never delete |
| HF Spaces cold start on demo day | C | Keep Space warm with a cron ping in last 24h |
| Judges ask "where is WhatsApp?" | All | Honest answer: "Meta approval takes 7–10 days. The chat widget you see is the exact same code path the webhook would hit. Production WhatsApp is a 2-day post-hackathon swap." |
| Judges ask about the other 4 agents | All | Show the orchestrator routing to their stubs; describe the roadmap. Don't fake outputs. |
| One person sick / down | All | Each `mocks.py` keeps the demo runnable without them |

---

## 8. What to read next

- `PLAN_PERSON_A.md` — Doctor Brain track
- `PLAN_PERSON_B.md` — Patient Flow track
- `PLAN_PERSON_C.md` — Ops Core track
- `MARKET_ANALYSIS.md` — Market sizing, competition, positioning
- `MASCOT.md` — Mascot proposal + Claude generation prompt
- `LEGAL_SOURCES.md` — Licence-cleared data sources
