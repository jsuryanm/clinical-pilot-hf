# Person B — Patient Flow (Appointments, Communication, Discharge)

> Owner of every channel where the **patient** interacts with the system, and every workflow that fires once the doctor's note is approved.

---

## 1. What you own

| Area | Folder(s) |
|---|---|
| Appointment Agent | `app/agents/appointment/` |
| Clerical Agent | `app/agents/clerical/` |
| Discharge Agent | `app/agents/discharge/` |
| WhatsApp integration | `app/integrations/whatsapp.py` |
| Google Calendar MCP client | `app/integrations/calendar_mcp.py` |
| Gmail MCP client | `app/integrations/gmail_mcp.py` |
| Celery reminder tasks | `app/agents/appointment/tasks.py` |
| Patient Gradio tab | `app/ui/patient_tab.py` |
| Appointment / no-show evals | `evals/appointment/` |
| Tests | `tests/test_appointment/`, `tests/test_clerical/`, `tests/test_discharge/` |

## 2. What Person C gives you on Day 0

- `app/contracts.py` with stub `BookingResult`, `CommunicationDraft`, `DischargeCoordination`, `CliniqState`
- `app/llm/router.py` — call `router.complete(task="reminder", ...)` and it picks Llama-3.1-8B on Groq for speed
- `docker-compose.dev.yml` — Redis is up on `:6379` and Celery is wired
- `app/api/routers/appointment.py` — empty FastAPI router to fill in
- Postgres tables `patients`, `appointments`, `messages` already migrated (you only consume the SQLAlchemy models in `app/db/models.py`)

You **do not need** Person A's documentation agent to start — your booking and reminder flow is self-contained. For the post-visit summary and discharge flows you read a patient wiki page; until A's wiki is real you import `app.agents.documentation.mocks.fake_soap_draft`.

## 3. What you must publish for the rest of the team

- `app/agents/appointment/mocks.py` with `def fake_booking() -> BookingResult` — **Day 1**
- `app/agents/discharge/mocks.py` with `def fake_discharge() -> DischargeCoordination` — **Day 8**
- A WhatsApp simulator (`tests/wa_sim.py`) that pipes JSON payloads into your inbound handler so C can demo without a real WhatsApp number

---

## 4. Day-by-day

### Day 0 — Kickoff
- Pick a WhatsApp dev path: **Twilio Sandbox** for hackathon (free, instant approval). Note WhatsApp Business API formal approval as a post-hackathon task.
- Sign up for a Google Workspace dev account (free) and confirm Calendar + Gmail MCP servers reachable from C's docker network.
- Lock the `BookingResult` schema fields with C — needs `slot_iso`, `doctor_id`, `patient_id`, `confirmation_sent_at`, `reminder_jobs`, `status`.

### Day 1 — Integration "hello world"s + mocks
- Twilio sandbox echo bot — a message arrives at `POST /webhook/whatsapp`, you log it and echo back.
- Calendar MCP `list_events` against a test calendar — confirm auth flow.
- Ship `mocks.fake_booking()` so C can wire it into the orchestrator.

### Day 2 — Booking happy path
- Inbound WhatsApp text → LLM parses intent → checks Calendar availability → creates event → confirms via WhatsApp.
- All against a stubbed "Dr. Test" calendar.
- Returns `BookingResult` with a Langfuse trace.

### Day 3 — Reminders via Celery
- `tasks.send_reminder(appointment_id, t_minus_minutes)` enqueued on booking.
- Two reminders by default: T-24h email (Gmail MCP) + T-2h WhatsApp.
- Reminder copy goes through `router.complete(task="reminder")` so it's localised (Hindi/English/code-mixed).

### Day 4 — Patient Gradio tab
- Single chat UI mimicking WhatsApp so a judge can demo without a phone.
- Behind the scenes: same code path as the real webhook.
- Show "Available slots" inline as buttons.

### Day 5 — No-show / waitlist
- If a confirmation isn't acknowledged 1h before slot, fire a "Are you still coming?" WhatsApp.
- If patient cancels or no-replies past slot start, mark `no_show`, pull the top waitlist entry, offer the slot.
- Eval: synthetic dataset of 200 bookings → measured `no_show_rate`.

### Day 6–7 — Polish
- Localisation: Hindi, English, code-mixed Hinglish. Use Llama-3.1-8B (fast, cheap) for translation.
- Edge cases: double-booking, doctor leave (read from C's roster output), patient typos in dates.

### Day 8 — Discharge Agent skeleton
- Trigger: nurse-admin tab (C) calls `POST /discharge/{patient_id}` when patient is clinically cleared.
- Agent fans out in parallel:
  1. Reads SOAP + wiki page (A's API) → drafts discharge summary
  2. Pharmacy task: extract meds from SOAP → format for pharmacy queue (table row in Postgres)
  3. Family notification: WhatsApp to registered contact
  4. Follow-up appointment: book a slot 7 days out
  5. Billing trigger: write a `billing_ready` event row
- Returns a `DischargeCoordination` payload listing all 5 sub-task statuses.

### Day 9 — Post-discharge 72h follow-up
- Celery beat schedule: at `discharge_time + 72h`, send a WhatsApp check-in.
- Inbound reply → Clerical Agent classifies (`reassuring | needs_review | needs_urgent_callback`).
- Urgent routes to nurse-admin tab inbox; needs_review queued for doctor.

### Day 10 — Clerical Agent referral letter
- Trigger: doctor approves a SOAP note flagged `referral_needed`.
- Agent drafts a referral letter using the wiki page + SOAP + receiving specialist's known preferences.
- Goes into doctor's approval queue (A's tab) — does **not** auto-send.

### Day 11 — Evals
- No-show eval ≤ 8% on 500-booking synthetic.
- Waitlist conversion ≥ 70% on the same set.
- 72h follow-up routing accuracy ≥ 90% on 50 hand-labelled replies.

### Day 12 — Patient post-visit summary
- 30 min after doctor approves a SOAP note, send the patient a plain-language summary (Llama-3.1-8B, 6th-grade reading level, Hindi + English).
- Includes: what we found, what to do at home, when to come back, red flags.

### Day 13–14 — Demo prep
- Three rehearsed flows:
  1. Booking via WhatsApp → reminder → patient shows up
  2. Patient no-shows → waitlist auto-fills
  3. Discharge → 5 parallel tasks fire → 72h follow-up arrives → patient says "still coughing" → routed to OPD inbox

---

## 5. Interfaces you publish

```python
# app/agents/appointment/api.py
def handle_inbound_message(channel: Literal["whatsapp","web"], payload: dict) -> CommunicationDraft: ...
def book(patient_id: str, requested_window: tuple[datetime, datetime], doctor_id: str | None = None) -> BookingResult: ...
def cancel(appointment_id: str, reason: str) -> BookingResult: ...

# app/agents/discharge/api.py
def initiate_discharge(patient_id: str) -> DischargeCoordination: ...
def discharge_status(patient_id: str) -> DischargeCoordination: ...

# app/agents/clerical/api.py
def draft_referral(soap_id: str, receiving_specialist: str) -> CommunicationDraft: ...
def classify_inbound_reply(message: str, context: dict) -> Literal["reassuring","needs_review","needs_urgent_callback"]: ...
```

## 6. Definition of Done (your slice)

- [ ] `mocks.py` files shipped Day 1 and Day 8
- [ ] WhatsApp booking happy path works end-to-end on HF Space (via web simulator)
- [ ] Reminders fire on Celery beat in real time
- [ ] No-show rate ≤ 8% in eval, waitlist conversion ≥ 70%
- [ ] Discharge fans out 5 parallel sub-tasks, all logged
- [ ] 72h follow-up routing ≥ 90% on labelled set
- [ ] Every LLM call traced in Langfuse
- [ ] No PHI in repo — synthetic patients only

## 7. Things you can safely ignore

- Whisper, SOAP drafting, wiki structure (A)
- Orchestrator / state machine / LiteLLM internals (C)
- Roster, handover (C)
- AWS / HF Spaces deploy plumbing (C)
- Postgres migrations (C runs Alembic; you just import models)
