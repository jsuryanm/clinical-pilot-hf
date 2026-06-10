# Person B — Patient Flow (Appointments & Reminders)

> Owner of the patient-facing booking experience and every workflow that fires around an appointment. For the hackathon, the patient interaction lives in a **Gradio chat widget** styled to mimic WhatsApp — the real WhatsApp Business API needs Meta approval and is post-hackathon.

---

## 1. What you own (hackathon scope)

| Area | Folder(s) | Built? |
|---|---|---|
| Appointment Agent | `app/agents/appointment/` | **Yes** |
| Google Calendar MCP client | `app/integrations/calendar_mcp.py` | **Yes** |
| Gmail MCP client (booking confirmations) | `app/integrations/gmail_mcp.py` | **Yes** |
| Celery reminder tasks (T-24h email, T-1h chat) | `app/agents/appointment/tasks.py` | **Yes** |
| Patient Gradio tab — **chat widget** in place of WhatsApp | `app/ui/patient_tab.py` | **Yes** |
| Appointment / no-show evals | `evals/appointment/` | **Yes** |
| Tests | `tests/test_appointment/` | **Yes** |

### Deferred to post-hackathon

- **WhatsApp Business API** (`app/integrations/whatsapp.py`) — Meta approval is days; the Gradio chat widget hits the same handler code path, so the swap is a one-day job later.
- **Discharge Agent** full 5-stream fan-out — keep `app/agents/discharge/api.py` as a stub. For the demo, if there's time, wire **2 streams** (discharge summary draft + family WhatsApp/chat notification) as a teaser. Pharmacy / billing / follow-up booking — post-hackathon.
- **Post-discharge 72h follow-up** — Celery beat schedule + classifier; post-hackathon.
- **Clerical Agent** (referral letters, FAQ classification) — stub only.
- **Insurance claim automation** — explicitly cut.
- **Patient post-visit summary** — keep in plan as Day 10 if Week 1 stayed on track; otherwise drop.

## 2. What Person C gives you on Day 0

- `app/contracts.py` with stub `BookingResult`, `CommunicationDraft`, `CliniqState` (plus `DischargeCoordination` stub if you teaser-wire 2 streams)
- `app/llm/router.py` — `router.complete(task="reminder", ...)` picks Llama-3.1-8B on Groq for speed
- `docker-compose.dev.yml` — Redis is up on `:6379`, Qdrant for memory, Celery worker wired
- `app/api/routers/appointment.py` — empty FastAPI router to fill in
- Postgres tables `patients`, `appointments`, `messages` already migrated (you only consume the SQLAlchemy models in `app/db/models.py`)
- `app/memory/api.py` — `remember` / `recall` for patient prefs. Use cases: capture language preference ("prefers Hindi"), best-time-to-reach, no-show history → bias reminder copy and timing. **Plus:** the Gradio chat widget uses LangGraph's `PostgresSaver` (provided by C via `get_checkpointer()`) for multi-turn continuity — set `thread_id = f"chat::{patient_id}"` and history persists automatically across sessions.

You **do not need** Person A's documentation agent. Your booking + reminder flow is self-contained.

## 3. What you must publish for the rest of the team

- `app/agents/appointment/mocks.py` with `def fake_booking() -> BookingResult` — **Day 1**
- A chat simulator helper (`tests/chat_sim.py`) that pipes JSON payloads into your inbound handler so the orchestrator tests work without the Gradio UI loop

---

## 4. Day-by-day

### Day 0 — Kickoff
- **Drop the Twilio sandbox plan.** Confirm with the team that the demo patient channel is the Gradio chat widget. (`app/integrations/whatsapp.py` may live as a stub for the "coming soon" story but is not wired.)
- Sign up for a Google Workspace dev account (free) and confirm Calendar + Gmail MCP servers reachable from C's docker network.
- Lock the `BookingResult` schema fields with C — needs `slot_iso`, `doctor_id`, `patient_id`, `confirmation_sent_at`, `reminder_jobs`, `status`.

### Day 1 — Integration "hello world"s + mocks
- Calendar MCP `list_events` against a test calendar — confirm auth flow works.
- Ship `mocks.fake_booking()` so C can wire it into the orchestrator.
- Build the inbound handler signature: `handle_inbound_message(channel: Literal["chat","web"], payload: dict) -> CommunicationDraft`. Gradio chat will call this; a future WhatsApp webhook would call the same function.

### Day 2 — Booking happy path
- Inbound chat text → LLM parses intent → checks Calendar availability → creates event → confirms in chat.
- Against a stubbed "Dr. Test" calendar.
- Returns `BookingResult` with a Langfuse trace.

### Day 3 — Reminders via Celery
- `tasks.send_reminder(appointment_id, t_minus_minutes)` enqueued on booking.
- Two reminders by default: T-24h email (Gmail MCP) + T-1h in-chat message.
- Reminder copy goes through `router.complete(task="reminder")` so it's localised (Hindi/English/code-mixed).

### Day 4 — Patient Gradio tab
- Single chat UI styled to feel like WhatsApp (avatar, message bubbles, "typing…" indicator).
- Behind the scenes: same `handle_inbound_message` path the future webhook will hit.
- Show "Available slots" inline as buttons.

### Day 5 — Gmail MCP confirmations
- Booking confirmation email sent via Gmail MCP on `BookingResult.status == "confirmed"`.
- Plain template, includes calendar `.ics` attachment.

### Day 6–7 — Polish
- Localisation: Hindi, English, code-mixed Hinglish (Llama-3.1-8B for speed).
- Edge cases: double-booking, doctor leave (read from C's roster output), patient typos in dates.

### Day 8 — Reminder copy hardening
- Tone-check reminder copy: warm, not robotic. Don't include clinical detail.

### Day 9 — No-show / waitlist
- If a confirmation isn't acknowledged 1h before slot, fire a "Are you still coming?" in-chat message.
- If patient cancels or no-replies past slot start, mark `no_show`, pull the top waitlist entry, offer the slot.
- Eval: synthetic dataset of 200 bookings → measured `no_show_rate`.

### Day 10 — Patient post-visit summary *(stretch)*
- 30 min after doctor approves a SOAP note (A's hook), send the patient a plain-language summary (Llama-3.1-8B, 6th-grade reading level, Hindi + English) via chat.
- Includes: what we found, what to do at home, when to come back, red flags.
- Drop this if Week 1 ran late — it's a nice-to-have, not the core demo.

### Day 11 — Evals
- No-show rate ≤ 8% on 200-booking synthetic.
- Waitlist conversion ≥ 70% on the same set.

### Day 12 — Demo dataset
- Two rehearsed flows:
  1. Booking via chat → confirmation email → T-1h reminder → patient shows up
  2. Patient no-shows → waitlist auto-fills, top-of-list gets the slot

### Day 13–14 — Joint dress rehearsal, fixes

### Stretch (only if everything above is green): Discharge teaser
- Wire `POST /discharge/{patient_id}` to fan out to **2 of 5** streams:
  1. Discharge summary draft (reads SOAP via A's mocks/API)
  2. Family notification via chat
- The other 3 streams (pharmacy, billing, follow-up booking) are described in the demo as "coming soon" and have stub `mocks.py` returning empty results.

---

## 5. Interfaces you publish

```python
# app/agents/appointment/api.py
def handle_inbound_message(channel: Literal["chat","web"], payload: dict) -> CommunicationDraft: ...
def book(patient_id: str, requested_window: tuple[datetime, datetime], doctor_id: str | None = None) -> BookingResult: ...
def cancel(appointment_id: str, reason: str) -> BookingResult: ...

# app/agents/discharge/api.py  (stub — initiate_discharge returns a 2-of-5 DischargeCoordination if stretch wired, else fake)
def initiate_discharge(patient_id: str) -> DischargeCoordination: ...

# app/agents/clerical/api.py  (stub only for hackathon)
def draft_referral(soap_id: str, receiving_specialist: str) -> CommunicationDraft: ...
```

## 6. Definition of Done (your slice)

- [ ] `mocks.py` shipped Day 1
- [ ] Booking happy path works end-to-end on HF Space (via Gradio chat widget)
- [ ] Reminders fire on Celery beat in real time (T-24h email + T-1h chat)
- [ ] No-show rate ≤ 8% in eval, waitlist conversion ≥ 70%
- [ ] Every LLM call traced in Langfuse
- [ ] No PHI in repo — synthetic patients only

## 7. Things you can safely ignore

- Whisper, SOAP drafting, wiki structure (A)
- Orchestrator / state machine / LiteLLM internals (C)
- Roster, handover (C / post-hackathon)
- HF Spaces deploy plumbing (C)
- Postgres migrations (C runs Alembic; you just import models)
- **WhatsApp Business API** — post-hackathon (your `handle_inbound_message` is designed so the swap is one day)
- **Twilio sandbox** — also dropped; no need
- Discharge full fan-out, post-discharge follow-up, Clerical Agent, insurance — all post-hackathon
