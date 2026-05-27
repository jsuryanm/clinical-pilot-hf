# Person C — Ops Core (Platform, Orchestration, Roster, Handover)

> Owner of everything that ties the system together: the LangGraph orchestrator, the typed contracts everyone codes against, the FastAPI backend, the database, the LLM router, deployments — plus two agents (Rostering, Handover) that fit the "ops" theme.

You ship the rails on **Day 0** so A and B can move on Day 1. You also own deploy, so you decide the last 36 hours of demo prep.

---

## 1. What you own

| Area | Folder(s) |
|---|---|
| Shared Pydantic contracts | `app/contracts.py` |
| LangGraph state & graph | `app/state.py`, `app/orchestrator.py` |
| LiteLLM router | `app/llm/router.py` |
| Rostering Agent | `app/agents/roster/` |
| Handover Agent | `app/agents/handover/` |
| Google Drive MCP client | `app/integrations/drive_mcp.py` |
| FastAPI backend | `app/api/main.py`, `app/api/routers/*` (you wire — each person owns their router file) |
| Postgres schema + Alembic | `app/db/models.py`, `app/db/migrations/` |
| Langfuse plumbing | inside `app/llm/router.py` + middleware |
| Nurse + Admin Gradio tabs | `app/ui/nurse_admin_tab.py` |
| Docker / docker-compose | `infra/` |
| HF Space entrypoint | `deploy/hf_space/app.py`, `requirements.txt` |
| AWS Free Tier deploy | EC2 + RDS scripts in `infra/` |
| Orchestrator evals | `evals/orchestrator/` |
| Tests | `tests/test_orchestrator/`, `tests/test_roster/`, `tests/test_handover/` |

## 2. What you must ship on Day 0 (everyone else is waiting on this)

This is the **critical-path 8-hour sprint** that unblocks A and B.

1. `app/contracts.py` — all Pydantic models, even if half the fields are `# TODO`. Frozen field names from this point on.
2. `app/state.py` — `CliniqState: TypedDict` with the append vs overwrite rules baked into reducer functions.
3. `app/llm/router.py` — `router.complete(task: str, messages: list[dict], **kwargs)` returning text + token counts. Routing rules from the README, hardcoded for now.
4. `app/api/main.py` — FastAPI app with `/health`, OpenAPI docs working, CORS open for HF Space.
5. `app/api/routers/` — one empty router per person (`documentation.py`, `appointment.py`, `roster.py` etc.).
6. `app/db/models.py` — SQLAlchemy models for `patients`, `appointments`, `messages`, `staff`, `shifts`, `discharges`. Alembic migration `0001_init.py` runs clean.
7. `infra/docker-compose.dev.yml` — Postgres, Redis, Langfuse, Celery worker. Single `make up` brings everything online.
8. `deploy/hf_space/app.py` — imports `doctor_tab`, `patient_tab`, `nurse_admin_tab` and stitches them into a `gr.TabbedInterface`. The other tabs can be empty placeholders today — they'll fill them in.

Post in the team channel when this is up. Day 1 starts the moment it lands.

## 3. What you must publish for the rest of the team

- `app/agents/roster/mocks.py` — `def fake_roster() -> RosterResult` by Day 3
- `app/agents/handover/mocks.py` — `def fake_handover() -> HandoverBrief` by Day 4
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
- All branches return mock payloads — full demo flows.

### Day 2 — Persistence + observability
- Alembic migrations clean on fresh Postgres.
- Langfuse wired: every `router.complete` call traced with task name, model, latency, tokens, cost estimate.
- Add a thin `app/api/middleware/audit.py` that logs every state-mutating API call to a `audit_log` table.

### Day 3 — Rostering Agent v1
- Input: CSV of 20 staff (name, role, certifications, leave, max-hours-per-week).
- Constraint solver — **start with a greedy heuristic, not OR-tools**, to ship fast. Note OR-tools as a Week 2 upgrade.
- Output: 14-day `RosterResult` with per-staff schedule + fairness score.
- Wall-clock target: < 5 min for 20 staff (greedy will be much faster, that's fine).

### Day 4 — Handover Agent v1
- Input: list of currently-admitted patients with vitals (read from Postgres) + last shift's notes.
- Pipeline per patient: pull wiki page (A's API) → summarise trend → assign priority (`stable | watch | urgent`).
- Output: `HandoverBrief` with patients ordered urgent-first, target ≤ 5 min read time.

### Day 5 — Nurse + Admin Gradio tab
- Two sub-tabs:
  - **Nurse:** view current handover brief, mark patients as "noted", flag concerns
  - **Admin:** roster view (drag-to-swap shifts), wiki lint report (from A), Langfuse cost meter
- Wire all three tabs together in `deploy/hf_space/app.py`, deploy a first HF Space.

### Day 6–7 — Polish, AWS skeleton
- AWS t2.micro EC2 with docker-compose-prod up; RDS t2.micro Postgres; Let's Encrypt SSL.
- HF Space pointed at the EC2 backend URL via Spaces Secrets.
- End-to-end demo runs from a clean clone.

### Day 8 — Discharge wiring (with B)
- Endpoint `POST /discharge/{patient_id}` in C's router, dispatches to B's agent.
- Add a "Mark Ready for Discharge" button to nurse-admin tab that calls the endpoint.

### Day 9 — Rostering: sick-call replacement
- New endpoint `POST /roster/sick_call`: nurse marks staff sick → agent finds best replacement under all constraints in ≤ 15 min.
- Surface decision rationale ("Picked Dr. Verma — same certification, under hours, off-day flexible") so the admin can sanity-check.

### Day 10 — Auth + audit
- Simple API-key auth (per-hospital), header `X-API-Key`.
- Audit log surfaced in admin tab.

### Day 11 — Langfuse dashboards
- Three dashboards: latency by agent, cost by model, error rate by agent.
- Set latency budgets (Documentation ≤ 60s, Reminder ≤ 5s, Routing ≤ 1s) and alert on violation.

### Day 12 — Roster fairness + handover prioritisation evals
- Roster: night-shift evenness across staff, leave-respected rate.
- Handover: priority concordance with a clinician's hand-labelled ranking on 10 cases.

### Day 13–14 — Demo prep
- Two rehearsed flows you drive:
  1. Generate a roster, sick-call a nurse, see the replacement appear in 30s
  2. Run a handover at "shift change", show the prioritised brief, mark one patient "ready for discharge" and watch B's agent fan out
- Burn-in run on a fresh AWS instance the morning of demo day.

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

# app/agents/handover/api.py
def generate_handover(ward_id: str, shift_end_ts: datetime) -> HandoverBrief: ...
```

## 6. Definition of Done (your slice)

- [ ] Day-0 rails landed and unblock A & B
- [ ] Orchestrator routes all 6 task types correctly on 30-case eval ≥ 95%
- [ ] Roster generates in < 5 min for 20 staff
- [ ] Sick-call replacement in < 15 min, picks valid candidate 100%
- [ ] Handover brief ≤ 5 min reading time, priority order matches clinician on ≥ 8/10
- [ ] Langfuse traces every LLM call across all 3 people's code
- [ ] HF Space + AWS EC2 deploy reproducible from `make deploy`
- [ ] No PHI in repo — synthetic data only

## 7. Things you can safely ignore

- Whisper / SOAP / wiki content (A)
- WhatsApp / Calendar / Gmail integrations (B)
- Patient-facing comms copy (B)
- Doctor-facing UX details (A)
- RAGAS / DeepEval framework (A)
