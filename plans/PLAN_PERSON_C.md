# Person C — Ops Core (Platform, Orchestration, Rostering)

> Owner of everything that ties the system together: the LangGraph orchestrator, the typed contracts everyone codes against, the FastAPI backend, the database, the LLM router, deployment — plus the **Rostering Agent** (the third shipping agent in the demo).

You ship the rails on **Day 0** so A and B can move on Day 1. You also own deploy, so you decide the last 36 hours of demo prep.

---

## 1. What you own (hackathon scope)

| Area | Folder(s) | Built? |
|---|---|---|
| Shared Pydantic contracts | `app/contracts.py` | **Yes** |
| LangGraph state & graph | `app/state.py`, `app/orchestrator.py` | **Yes** |
| **Agent memory layer** (LangGraph PostgresSaver + Mem0) | `app/memory/` | **Yes** |
| LiteLLM router | `app/llm/router.py` | **Yes** |
| Rostering Agent (**greedy** — no OR-Tools) | `app/agents/roster/` | **Yes** |
| FastAPI backend | `app/api/main.py`, `app/api/routers/*` (you wire — each person owns their router file) | **Yes** |
| Postgres schema + Alembic | `app/db/models.py`, `app/db/migrations/` | **Yes** |
| Langfuse plumbing | inside `app/llm/router.py` + middleware | **Yes** |
| Nurse + Admin Gradio tabs | `app/ui/nurse_admin_tab.py` | **Yes** |
| Docker / docker-compose (dev only) | `infra/docker-compose.dev.yml` | **Yes** |
| HF Space entrypoint | `deploy/hf_space/app.py`, `requirements.txt` | **Yes** |
| Orchestrator evals | `evals/orchestrator/` | **Yes** |
| Tests | `tests/test_orchestrator/`, `tests/test_roster/` | **Yes** |

### Deferred to post-hackathon

- **Handover Agent** — keep `app/agents/handover/api.py` as a stub returning `fake_handover()`. The orchestrator can still route to it; the demo describes it as "coming soon."
- **Discharge wiring** beyond the 2-stream teaser (if B does it).
- **Google Drive MCP** — only wire if rostering actually reads from Drive; a CSV in `data/` is fine for the demo.
- **AWS Free Tier** (EC2 + RDS + Terraform) — HF Space is the only target for the demo. AWS is post-hackathon.
- **OR-Tools / CP-SAT** roster solver — greedy is fine for the demo.
- **API-key auth, audit log surfaced in admin tab** — keep simple; basic API key OK, audit log can write to Postgres without UI surface for the demo.
- **ABDM integration, multi-hospital tenancy** — out of scope even post-hackathon until there's a customer.

## 2. What you must ship on Day 0 (everyone else is waiting)

The **critical-path 8-hour sprint** that unblocks A and B.

1. `app/contracts.py` — all Pydantic models, even if half the fields are `# TODO`. Frozen field names from this point on. Include stubs for `HandoverBrief` and `DischargeCoordination` so the orchestrator can route to "coming soon" agents.
2. `app/state.py` — `CliniqState: TypedDict` with append vs overwrite rules baked into reducer functions.
3. `app/llm/router.py` — `router.complete(task: str, messages: list[dict], **kwargs)` returning text + token counts. Routing rules from the README, hardcoded for now.
4. `app/api/main.py` — FastAPI app with `/health`, OpenAPI docs working, CORS open for HF Space.
5. `app/api/routers/` — one empty router per person (`documentation.py`, `appointment.py`, `roster.py`).
6. `app/db/models.py` — SQLAlchemy models for `patients`, `appointments`, `messages`, `staff`, `shifts`. Alembic migration `0001_init.py` runs clean. (Skip `discharges` for now; add when/if needed.)
7. `infra/docker-compose.dev.yml` — Postgres, Redis, Langfuse, Celery worker. Single `make up` brings everything online.
8. `deploy/hf_space/app.py` — imports `doctor_tab`, `patient_tab`, `nurse_admin_tab` and stitches them into a `gr.TabbedInterface`. Empty placeholders for now — A and B will fill them.

Post in the team channel when this is up. Day 1 starts the moment it lands.

## 3. What you must publish for the rest of the team

- `app/agents/roster/mocks.py` — `def fake_roster() -> RosterResult` by Day 3
- `app/agents/handover/mocks.py` — `def fake_handover() -> HandoverBrief` by Day 1 (stub, for orchestrator routing) — no real implementation
- `app/orchestrator.py` should call **everyone's mocks** by Day 1 end so the full graph executes against fake data — this is the moment the team can demo "an end-to-end flow" even though no agent is real yet.

---

## 4. Day-by-day

### Day 0 — Rails (8 hr sprint)
- Ship the 8 items above.
- Open three PRs marked `infra-only` so A and B can review fast.
- Run a 30-min walkthrough call.

### Day 1 — Orchestrator routes to mocks
- LangGraph graph: `START → orchestrator (classify) → [doc | appt | roster | handover | discharge | clerical] → END`.
- Orchestrator uses a small fast model (Llama-3.1-8B) and a Pydantic-validated `RoutingDecision`.
- All branches return mock payloads — full demo flows possible.

### Day 2 — Persistence + observability + memory layer
- Alembic migrations clean on fresh Postgres.
- Langfuse wired: every `router.complete` call traced with task name, model, latency, tokens, cost estimate.
- Thin `app/api/middleware/audit.py` logs every state-mutating API call to an `audit_log` table.
- **Agent memory layer wired** — see Section 4.5 below. Both `PostgresSaver` (short-term) and `Mem0` (long-term) up by end of Day 2 so A and B can call `memory.add()` and `memory.search()` from Day 3 onwards.

### Day 3 — Rostering Agent v1 (greedy)
- Input: CSV of 20 staff (name, role, certifications, leave, max-hours-per-week).
- Constraint solver — **greedy heuristic.** No OR-Tools, no CP-SAT. Easier to debug under demo pressure.
- Output: 14-day `RosterResult` with per-staff schedule + simple fairness score (night-shift evenness).
- Wall-clock target: well under 5 min for 20 staff (greedy will be near-instant).

### Day 4 — Nurse + Admin Gradio tab (initial)
- Two sub-tabs:
  - **Nurse:** current roster view (read-only is fine for now)
  - **Admin:** roster regenerate button, Langfuse cost meter
- Don't try to support drag-to-swap shifts in the demo — read-only with a "regenerate" button is enough.

### Day 5 — Wire HF Space
- Pull A's `doctor_tab.py` and B's `patient_tab.py` into `deploy/hf_space/app.py`.
- Deploy first HF Space, share URL with team.

### Day 6–7 — Polish
- End-to-end demo runs from a clean clone (`make up && make demo`).
- HF Space stays warm.
- No AWS / Terraform — drop entirely from hackathon scope.

### Day 8 — Rostering: sick-call replacement
- New endpoint `POST /roster/sick_call`: nurse marks staff sick → agent finds best replacement under all constraints, target ≤ 15 min wall-clock.
- Surface decision rationale ("Picked Dr. Verma — same certification, under hours, off-day flexible") so the admin can sanity-check.

### Day 9 — Roster fairness eval
- Night-shift evenness across staff, leave-respected rate.
- One numeric score per roster generation; surface in admin tab.

### Day 10 — Auth + audit (lightweight)
- Simple API-key auth (per-hospital), header `X-API-Key`.
- Audit log writes to Postgres; surfacing in UI is post-hackathon.

### Day 11 — Langfuse dashboards
- Three dashboards: latency by agent, cost by model, error rate by agent.
- Latency budgets (Documentation ≤ 60s, Reminder ≤ 5s, Routing ≤ 1s) with alerts.

### Day 12 — Demo prep
- Two rehearsed flows you drive:
  1. Generate a roster from staff CSV, sick-call a nurse, see the replacement appear in <30s
  2. Walk through the orchestrator routing — show that the "coming soon" agents (Handover, Discharge, Clerical) are real nodes that just return placeholder payloads
- Burn-in run on the HF Space the morning of demo day.

### Day 13–14 — Joint dress rehearsal, submission video, buffer

---

## 4.5. Agent memory layer (your responsibility)

CliniqAI has three places state needs to live, and they map cleanly to three storage layers. You own all three.

| Layer | What it stores | Backed by | Lifetime |
|---|---|---|---|
| **Working state** | The active LangGraph `CliniqState` — current transcript, in-flight retrieval hits, the agent's pending output | LangGraph in-process | Single graph invocation |
| **Short-term / thread memory** | Checkpoints of every graph step so a session can resume, replay, time-travel debug; multi-turn chat history for the patient widget | **`langgraph.checkpoint.postgres.PostgresSaver`** on the existing Postgres | Until thread is closed (typically a session, e.g. one OPD visit or one chat conversation) |
| **Long-term / cross-session memory** | Doctor edit preferences ("she always renames 'HTN' → 'Hypertension'"), patient comm preferences ("prefers Hindi, replies after 8pm"), nurse scheduling preferences ("never Sunday nights") | **Mem0 (self-hosted OSS)** on the existing Postgres + Qdrant | Persists across sessions; pruned by Mem0's auto-summarisation |

### Why this stack

- **LangGraph PostgresSaver** is built-in to LangGraph, ships with the version we already have, costs nothing extra, and is the only sane choice for graph checkpointing. It also handles the patient chat widget's multi-turn history (each `thread_id` is one conversation).
- **Mem0** (`pip install mem0ai`) is purpose-built for agent memory, integrates with LangGraph in one line, auto-extracts memories with an LLM call so we don't write `memory.add(...)` in every agent, and runs fully self-hosted on our existing infra. Considered alternatives: **LangMem** (newer, less mature, ties us tighter to LangChain), **Zep** (needs a separate Go service, heavier), **Letta / MemGPT** (research-grade, too complex for 2 weeks). Mem0 is the right point on the simplicity / capability curve.

### What lives in the new `app/memory/` module

```
app/memory/
├── __init__.py
├── checkpoint.py        # configures PostgresSaver, exports get_checkpointer()
├── longterm.py          # configures Mem0 client, exports get_mem0()
└── api.py               # thin facade so A and B never import mem0 / langgraph directly
```

### Public API (frozen Day 2 — additive only after that)

```python
# app/memory/api.py
from typing import Literal

MemoryScope = Literal["user", "session", "agent"]
# user   → tied to a patient_id or staff_id, persists forever
# session→ tied to a thread_id (one OPD visit / one chat), ephemeral-ish
# agent  → tied to an agent name, e.g. "documentation", for agent-level learned habits

def remember(*, scope: MemoryScope, key: str, text: str, metadata: dict | None = None) -> None:
    """Write a memory. Mem0 will dedupe + summarise behind the scenes."""

def recall(*, scope: MemoryScope, key: str, query: str, top_k: int = 5) -> list[Memory]:
    """Semantic search. Returns ranked Memory records."""

def get_checkpointer():
    """Returns the PostgresSaver instance for LangGraph's `graph.compile(checkpointer=...)`."""
```

A and B import only `remember` / `recall`. They never touch `mem0` or `langgraph.checkpoint` directly — that way if we swap memory backends post-hackathon, their code doesn't change.

### Concrete uses in the demo

- **Doctor (A's slice):** when the doctor edits a SOAP draft, A calls `remember(scope="user", key=doctor_id, text="...")` with the diff. Next visit, A calls `recall(...)` and biases the prompt to apply learned preferences (e.g. "always expand abbreviations").
- **Patient chat (B's slice):** chat widget threads use `thread_id = f"chat::{patient_id}"`. The PostgresSaver gives multi-turn continuity automatically — no per-message DB writes needed. `remember(scope="user", key=patient_id, text="prefers Hindi")` captures cross-session prefs.
- **Roster (your slice):** after each generation, write fairness outliers as memories (`scope="agent", key="roster"`). On the next sick-call replacement, recall surfaces "Dr. Verma has done 3 weekend nights in a row" without re-scanning history.

### Day-by-day for the memory layer (folded into your timeline)

- **Day 0:** `app/memory/api.py` ships with stub implementations (in-memory dict) so A and B can write code against the real signatures.
- **Day 2:** `PostgresSaver` wired into `orchestrator.run`. Mem0 client connects to local Qdrant (already in `docker-compose.dev.yml`).
- **Day 3:** real `remember` / `recall` flowing into Mem0; one Langfuse trace per memory write so cost is visible.
- **Day 5:** the Doctor and Patient tabs both actively read from memory in the demo flow.
- **Day 11:** add a memory dashboard panel in the admin tab (count of memories per scope, last-write timestamp, cost-this-week).
- **Day 12:** demo flow includes "watch the doctor's preference get learned" — record a SOAP edit, do a second consultation, show the prompt picked up the preference.

### Things to ignore for the hackathon

- Memory **eviction policies** beyond Mem0's defaults — fine to let memories accumulate over 2 weeks.
- **Cross-tenant isolation** — we are single-tenant. Multi-tenant memory scoping is a post-hackathon problem.
- **Memory editing UI** — admin tab is read-only for memories.
- **GDPR/DPDPA right-to-erasure flow** — design the API to support it (`forget(scope, key)`) but only stub the implementation.

---

## 5. Interfaces you publish

```python
# app/orchestrator.py
def run(state: CliniqState) -> CliniqState: ...   # one end-to-end pass

# app/llm/router.py
def complete(*, task: str, messages: list[dict], **kwargs) -> CompletionResult: ...

# app/agents/roster/api.py
def generate_roster(staff_csv: Path, window_days: int = 14) -> RosterResult: ...
def find_sick_call_replacement(shift_id: str, sick_staff_id: str) -> RosterResult: ...

# app/agents/handover/api.py  (stub for hackathon)
def generate_handover(ward_id: str, shift_end_ts: datetime) -> HandoverBrief: ...   # returns fake_handover()

# app/memory/api.py  (see Section 4.5)
def remember(*, scope: MemoryScope, key: str, text: str, metadata: dict | None = None) -> None: ...
def recall(*, scope: MemoryScope, key: str, query: str, top_k: int = 5) -> list[Memory]: ...
def forget(*, scope: MemoryScope, key: str) -> int: ...   # stub for hackathon, returns 0
def get_checkpointer(): ...
```

## 6. Definition of Done (your slice)

- [ ] Day-0 rails landed and unblock A & B
- [ ] Orchestrator routes all task types correctly on 20-case eval ≥ 95%
- [ ] Roster generates in < 1 min for 20 staff (greedy is fast)
- [ ] Sick-call replacement in < 15 min, picks valid candidate 100%
- [ ] Langfuse traces every LLM call across all 3 people's code
- [ ] HF Space deploy reproducible from `make deploy`
- [ ] **`app/memory/api.py` shipped Day 2; PostgresSaver + Mem0 both live; A and B writing/reading memories by Day 3**
- [ ] **Demo includes one visible "learned preference" moment** (e.g. SOAP draft picks up doctor's renaming preference between two consultations)
- [ ] No PHI in repo — synthetic data only

## 7. Things you can safely ignore

- Whisper / SOAP / wiki content (A)
- Calendar / Gmail integrations (B)
- Patient-facing comms copy (B)
- Doctor-facing UX details (A)
- RAGAS / DeepEval framework (A)
- **WhatsApp** (cut from hackathon)
- **Handover Agent** real implementation, **Discharge Agent**, **Clerical Agent**, **Wiki Maintenance Agent** — all post-hackathon
- **OR-Tools / CP-SAT** — post-hackathon if ever
- **AWS / Terraform / RDS** — post-hackathon
- **ABDM / multi-hospital tenancy** — out of scope entirely
