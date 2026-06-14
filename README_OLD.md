> ⚠️ **DEPRECATED — this is the original planning README (kept for historical / pitch context).**
> It describes the *intended* 2-week hackathon scope, where only Documentation, Appointment, and
> Rostering were "shipping" and the rest were "coming soon". The project has since moved past this
> plan — **all seven agents are now implemented and demoable.** For the current, accurate
> description of what the app does and how to run it, see **[`README.md`](README.md)**.

---

# CliniqAI — Clinical Operations AI for Indian Hospitals

> Giving doctors and nurses back the time they spend on paperwork, so they can focus on patients.

---

## The Problem

Indian doctors spend **2–3 hours every day** on paperwork. Nurses spend hours building rosters by hand. Receptionists book appointments over the phone. Patients get discharged 4–6 hours late because five departments are waiting on each other.

None of this work requires medical judgment. It is mechanical, repetitive, and automatable.

**What this system does:** A suite of AI agents handles the administrative layer of hospital operations — documentation, appointments, rostering, handovers, discharge, and follow-up — while doctors and nurses stay in control of every clinical decision.

> **Hackathon scope (2 weeks, 3 people):** we ship the three agents that solve the three biggest pain points — **Documentation**, **Appointment**, and **Duty Rostering**. The other agents (Handover, Discharge, Post-Discharge Follow-Up, Clerical, Wiki Maintenance) are architected and routable through the orchestrator, but described as "coming soon" in the demo. The full scope cut-list lives in [`plans/PLAN.md`](plans/PLAN.md).

---

## Core Features

Legend: ✅ shipping in hackathon · ⏳ coming soon (architected, not built) · ❌ explicitly out of scope for this hackathon

| Feature | Status | What it does |
|---|---|---|
| **Clinical Documentation** | ✅ | Doctor consults normally. Whisper transcribes audio. Agent drafts a complete SOAP note with ICD-10 codes and guideline suggestions in under 60 seconds. Doctor reviews and approves. |
| **Appointment Management** | ✅ | Patients book, change, and cancel via a chat widget (WhatsApp-styled). Agent checks Google Calendar availability, confirms slots via email, sends reminders, and manages waitlists. |
| **Duty Rostering** | ✅ | Generates a 14-day roster for 20+ staff in under 1 minute using a greedy heuristic. Handles leave, certifications, and shift limits. Finds sick-call replacements in under 15 minutes. |
| **Shift Handover** | ⏳ | Will read all vitals and clinical notes and produce a prioritised patient brief at shift end. |
| **Discharge Coordination** | ⏳ | Will fan out to pharmacy, family notification, follow-up booking, and billing in parallel. A 2-of-5 stream teaser may be shown in the demo. |
| **Post-Discharge Follow-Up** | ⏳ | Will send a check-in at 72 hours and route clinical replies to the outpatient team. |
| **Insurance & Referrals** | ❌ | Cut from hackathon — complex edge cases, not the core demo story. |
| **WhatsApp Business API** | ❌ | Cut from hackathon — Meta approval takes days. Demo uses a Gradio chat widget on the same handler code path. Production WhatsApp is a post-hackathon swap. |
| **Antibiotic Stewardship** | ❌ | Cut — requires culture-result integration and clinical validation. |
| **ABDM / ABHA integration, multi-hospital tenancy** | ❌ | Out of scope until there is a paying customer asking. |

---

## How the Knowledge System Works

### The Problem with Standard RAG

Standard RAG (Retrieval-Augmented Generation) splits documents into chunks and searches them at query time. In a clinical context this causes two problems:

1. When a guideline is updated, old and new versions coexist in the database. The AI may blend both and produce contradictory advice.
2. Patient history does not accumulate. Every query starts from scratch.

### The Karpathy LLM Wiki

Andrej Karpathy's LLM Wiki pattern solves this by having the AI maintain a structured wiki of markdown files — one page per patient, drug, condition, and protocol. When a new guideline arrives, the AI updates the relevant pages, marks superseded content, and updates cross-references. The next query reads a clean, current synthesis instead of a mix of old and new chunks.

### How This System Uses Both

| Layer | What it stores | Why |
|---|---|---|
| **LLM Wiki** | Patient histories, drug profiles, clinical protocols, SOPs | Evolving knowledge that needs to stay current and cross-referenced |
| **Vector + BM25 RAG** | ICD-10 / ICD-10-CM codes (74,000+), National Formulary of India, openFDA drug labels, SNOMED CT India Edition (incl. mental-health classifications via ICD-10 Chapter V) | Too large for the wiki; needs keyword-precise lookup |
| **PostgreSQL** | Appointments, lab results, roster history | Structured data that is better queried with SQL |
| **LangGraph State** | Current session data | In-memory working context for the active workflow |
| **Agent Memory** — short-term: **LangGraph `PostgresSaver`** · long-term: **Mem0 (self-hosted)** | Thread checkpoints + multi-turn chat history (short-term); learned doctor/patient/staff preferences across sessions (long-term) | Resume / replay graph runs, and let the agents get smarter about each user without retraining |

> **Note on DSM-5:** an earlier draft referenced DSM-5 here. APA copyright forbids ingesting DSM content into generative AI without a paid licence. We use **ICD-10 Chapter V (F00–F99) / ICD-11 Chapter 06** for mental-health classification instead, which are WHO-licensed and free. See [`plans/LEGAL_SOURCES.md`](plans/LEGAL_SOURCES.md) for the full rationale and the "do-not-upload" list.

---

## Knowledge Sources (Verified, Licensed, Local)

Every document below is **legally redistributable for our use** and has been downloaded and integrity-checked. Run `bash scripts/fetch_data.sh` on a fresh clone to pull all of them into `data/` (gitignored — distributed via a shared bucket, not git). For licensing rationale and the "do-not-upload" list, see [`plans/LEGAL_SOURCES.md`](plans/LEGAL_SOURCES.md).

### Classifications (BM25 + Chroma index)

| Source | Local path | Size / Scope | Licence |
|---|---|---|---|
| **WHO ICD-10 2019 International** (ClaML XML) | `data/icd10/icd102019en.xml` | 9.1 MB · **11,243 category codes** | WHO classification — free with attribution |
| **CDC ICD-10-CM FY2026** (US clinical modification, billing-granular) | `data/icd10/icd10cm_2026/icd10cm-codes-2026.txt` | 6.1 MB · **74,719 codes** | US Government — public domain |
| **WHO ICD-10-CM tabular index 2026** | `data/icd10/icd10cm_2026/icd10cm-order-2026.txt` | 14 MB | US Government — public domain |
| **WHO ICD-11 license & terms** | `data/legal/icd11-license.pdf` | 5 pg | CC BY-ND 3.0 IGO — commercial use + AI training explicitly permitted |
| **SNOMED CT India Edition** | _(manual fetch — apply at [NRCeS](https://mlds.ihtsdotools.org/#/landing/IN))_ | full international + India drug extension | Free in India (member country) |

### Indian clinical guidelines (LLM Wiki synthesis sources)

| Source | Local path | Pages | Used for |
|---|---|---|---|
| **MoHFW — Standard Treatment Guidelines: Hypertension** | `data/mohfw/Hypertension_full.pdf` | **152** | Hypertension wiki page (Week 1 seed) |
| **ICMR — Type-1 Diabetes Management Guidelines** | `data/icmr/type1_diabetes.pdf` | **173** | T1D wiki page |
| **ICMR — Type-2 Diabetes Guidelines 2018** | `data/icmr/type2_diabetes_2018.pdf` | **82** | T2D wiki page (Week 1 seed) |
| **ICMR — Treatment Guidelines for Antimicrobial Use in Common Syndromes 2022** | `data/icmr/amr_treatment_2022_full.pdf` | **168** | CAP / UTI / sepsis / skin / CNS / GI infection pages |
| **ICMR — Diagnosis & Management of Carbapenem-Resistant Organisms 2022** | `data/icmr/cro_diagnosis_2022.pdf` | **24** | AMR escalation logic, handover red flags |
| **ICMR — Standard Treatment Workflows Vol 3 (2022)** | `data/icmr/stw_vol3_2022.pdf` | **80** | Broad cross-condition workflows |
| **AIIMS Rishikesh — Standard Treatment Guidelines Manual** | `data/mohfw/aiims_rishikesh_stg.pdf` | **431** | Cross-specialty reference; back-stop when ICMR is silent |

> **Wiki authorship rule:** these PDFs are *synthesis sources*, not the wiki. You **paraphrase + cite** them in markdown pages under `wiki/`. Never paste paragraphs verbatim — that's a derivative work and inherits any restrictions on the source. Citations go in each page's frontmatter (`source:` field — see [`wiki/README.md`](wiki/README.md)).

### Drug data

| Source | Local path | Scope | Licence |
|---|---|---|---|
| **National Formulary of India, 5th edn (2016)** | `data/nfi/NFI_2016.pdf` | 60 pg excerpt (full edn via IPC on request) | Government of India — open |
| **WHO Model List of Essential Medicines, 23rd edn (2023)** | `data/who/WHO_EML_23_2023.pdf` | 71 pg · ~600 medicines | CC BY-NC-SA 3.0 IGO (re-license for commercial) |
| **openFDA drug label sample** (live API) | `data/openfda/amlodipine_sample.json` | 238 amlodipine label hits | US Gov — public domain |
| **RxNorm / Loinc / WHO ATC** | _(manual — see `scripts/fetch_data.sh`)_ | optional cross-mapping | Free with attribution |

### Total today

**~91 MB · 14 files · 1,521 pages of guideline PDFs · 85,962 ICD codes ready to index.**

### What we deliberately did NOT download

- ❌ **DSM-5 / DSM-5-TR** — APA all-rights-reserved; explicitly forbidden in generative AI without paid licence
- ❌ **British National Formulary (BNF)** — proprietary
- ❌ **NICE guidelines** — UK Open Content Licence is UK-only; international use needs a fee
- ❌ **MIMS India / CIMS** — paid commercial
- ❌ Any medical textbook (Harrison's, Davidson's, Robbins, KDT, etc.) — copyrighted
- ❌ UpToDate / DynaMed / BMJ Best Practice — subscription proprietary

See [`plans/LEGAL_SOURCES.md`](plans/LEGAL_SOURCES.md) for the full rationale and replacement strategy.

---

## Recommended LLMs (Free, ≤ 32B Parameters)

Use **LiteLLM** to route tasks to the right model. Heavier reasoning tasks go to the strongest available model; simple, high-frequency tasks go to the fastest.

### Groq — Best for Speed (Free Tier)

Groq's free tier includes all models with no credit card required.

| Model | Parameters | Best For |
|---|---|---|
| **Qwen3 32B** `qwen/qwen3-32b` | 32B | Primary model — SOAP notes, handover briefs, discharge summaries. Supports a "thinking mode" for complex reasoning. |
| **Llama 3.1 8B** `llama-3.1-8b-instant` | 8B | High-frequency simple tasks — FAQ replies, appointment confirmations, reminder messages. Fastest model available at ~660 tokens/sec. |

### OpenRouter — Best Free Alternatives (No Credit Card)

Free models have a limit of 20 requests/minute and 200 requests/day. Use as a Groq fallback.

| Model | Parameters | Best For |
|---|---|---|
| **Gemma 4 31B** `google/gemma-4-31b-it:free` | 31B | Documentation and referral drafting. Supports vision (useful for reading uploaded lab reports). |
| **GPT-OSS 20B** `openai/gpt-oss-20b:free` | 20B | General agent tasks, roster conflict reasoning. |

### Ollama — Best for Local / Offline (Completely Free)

Run on your own machine — no API calls, no rate limits, no cost.

| Model | Parameters | Best For |
|---|---|---|
| **Qwen2.5 32B** `qwen2.5:32b` | 32B | Best local option for documentation and clinical reasoning. |
| **DeepSeek R1 Distill Qwen 32B** `deepseek-r1:32b` | 32B | Strong reasoning for handover synthesis and discharge coordination. |
| **Llama 3.1 8B** `llama3.1:8b` | 8B | Lightweight tasks on low-memory machines. |

### Recommended Routing Strategy

```
SOAP notes / Handover briefs / Discharge summaries  →  Qwen3 32B on Groq
FAQ replies / Appointment confirmations / Reminders  →  Llama 3.1 8B on Groq
Groq rate limit hit                                  →  Gemma 4 31B on OpenRouter
No internet / Offline demo                          →  Qwen2.5 32B via Ollama
```

---

## Agent Architecture

All agents are nodes in a **LangGraph** state graph. The Orchestrator classifies every incoming request and routes it to the right agent. Agents share a single typed state object that flows through the graph and accumulates updates at each step.

```
Incoming Signal (Chat widget / Voice / Form / Calendar / Timer)
         ↓
   [ Orchestrator ]
         ↓
  ┌──────┬──────┬────────┬─────────────┬─────────────┬────────────┐
  Doc ✅  Appt✅  Roster✅  Handover ⏳   Discharge ⏳   Clerical ⏳
         ↓ (shipping agents read and write to)
   [ Four-Layer Memory System ]
```

Every agent output that affects a patient requires **human approval** before it is sent or filed. Agents prepare. Humans decide.

---

## Agents — Goals and Responsibilities

### Orchestrator ✅
Classifies every incoming signal and routes it to the right agent. Coordinates multi-step workflows. Handles errors and escalations.

### Documentation Agent ✅ (shipping)
Reads the patient's history from the wiki, retrieves the relevant guidelines and ICD-10 codes, and drafts a SOAP note. Surfaces guideline suggestions inline. Updates the patient wiki page on approval.

### Appointment Agent ✅ (shipping)
Parses booking requests from the chat widget (or, post-hackathon, WhatsApp). Checks Google Calendar availability. Books slots, sends confirmations via Gmail, queues Celery reminders, manages waitlists, and handles no-shows.

### Rostering Agent ✅ (shipping)
Reads staff certifications and leave from a CSV (Google Drive integration is post-hackathon). Generates a fair, constraint-satisfying roster using a greedy heuristic (OR-Tools is post-hackathon). Finds real-time sick-call replacements.

### Handover Agent ⏳ (coming soon)
Will read shift vitals, medication logs, and clinical notes. Will identify deteriorating patients and generate a prioritised handover brief. Stubbed in the orchestrator for the hackathon.

### Discharge Agent ⏳ (coming soon)
Will trigger all discharge tasks in parallel: discharge summary, pharmacy, family, billing, follow-up. The demo may show a 2-of-5 stream teaser (summary + family notification).

### Clerical Agent ⏳ (coming soon)
Will draft referral letters, send post-visit patient summaries, and route inbound FAQ messages. Stubbed for the hackathon.

### Wiki Maintenance Agent ⏳ (coming soon)
Will ingest new guidelines and update wiki pages; lint for contradictions, stale content, broken cross-references. Stubbed for the hackathon.

---

## Agent State

Every workflow shares a single state object (LangGraph `TypedDict`) containing:

- **Session fields** — session_id, task_type, current_agent, timestamp
- **Messages** — full conversation history (append-only)
- **Per-agent sub-states** — documentation, appointment, roster, handover, discharge, clerical, wiki each have their own fields
- **Error fields** — error, escalation_required, escalation_reason

**Update rules:** List fields (retrieved guidelines, sent communications) always append. Scalar fields (draft document, booked slot) always overwrite. No node mutates state directly — each returns only the fields it changes.

---

## Structured Agent Outputs

Every agent returns a validated **Pydantic model**. This ensures the Orchestrator can always parse the output and route correctly, and that every output is typed, logged, and auditable.

Examples: `SOAPNoteDraft`, `BookingResult`, `RosterResult`, `HandoverBrief`, `DischargeCoordination`, `CommunicationDraft`, `RoutingDecision`.

---

## MCP Servers (Free, Officially Hosted)

| Server | URL | Used By |
|---|---|---|
| Google Calendar | `calendarmcp.googleapis.com` | Appointment Agent |
| Gmail | `gmailmcp.googleapis.com` | Appointment Agent (booking confirmations + T-24h reminders) |
| Google Drive | `drivemcp.googleapis.com` | (post-hackathon — Rostering reads a CSV from `data/` for the demo) |
| Context7 | `mcp.context7.com` | Development — live library docs for LangGraph, FastAPI |
| Hugging Face | `huggingface.co/mcp` | Model discovery for Whisper variants |

---

## Evaluation Metrics

### Documentation
- SOAP note completeness without doctor additions: **> 85%**
- Doctor sign-off time: **< 90 seconds** (baseline: 8–10 minutes)
- Doctor edit rate: **< 20%**

### Appointments
- No-show rate: **< 8%** (baseline: 15–20%)
- Waitlist slot conversion rate: **> 70%**

### Rostering
- Time to generate roster: **< 5 minutes** (baseline: 3–5 hours)
- Sick call replacement time: **< 15 minutes** (baseline: 30–60 minutes)

### Discharge
- Time from discharge flag to patient leaving: **< 1.5 hours** (baseline: 4–6 hours)
- 30-day readmission rate: **< 10%** (baseline: ~15%)

---

## Tech Stack

### Backend

| Tool | Reason |
|---|---|
| **Python 3.12** | Best AI/ML library ecosystem |
| **FastAPI** | Async-native, auto-generates OpenAPI docs |
| **LangGraph** | Stateful multi-agent orchestration with checkpointing and replay |
| **LiteLLM** | Routes tasks to Groq, OpenRouter, or Ollama with a single interface |
| **Pydantic v2** | Validates all agent structured outputs at runtime |
| **PostgreSQL** | Patient records, appointment history, staff records |
| **Celery + Redis** | Reminder scheduling and background task queue |
| **LangGraph `PostgresSaver`** | Short-term agent memory — graph checkpoints, replay, multi-turn chat threads |
| **Mem0 (self-hosted OSS)** | Long-term agent memory — learned doctor / patient / staff preferences across sessions. Backed by Postgres + Qdrant. |

### AI & Retrieval

| Tool | Reason |
|---|---|
| **Whisper large-v3** (via Hugging Face) | State-of-the-art speech-to-text with strong medical vocabulary accuracy |
| **ChromaDB** | Lightweight vector database for the RAG corpus |
| **BM25 (rank-bm25)** | Keyword-precision ICD-10 code lookup |
| **Langfuse** | Traces every agent call, token usage, latency, and cost |
| **RAGAS + DeepEval** | Evaluates retrieval quality and documentation accuracy |

### Frontend

| Tool | Reason |
|---|---|
| **Gradio** | Python-native UI; connects directly to FastAPI; deploys to Hugging Face Spaces with one command; supports chat, file upload, and tables |

### Integrations

| Tool | Reason |
|---|---|
| **Google Calendar / Gmail MCP** | Free official hosted MCP servers for calendar and email |
| **Gradio chat widget** | Stand-in for WhatsApp during the hackathon — same handler code path; WhatsApp Business API is a post-hackathon swap once Meta approves the number |

---

## Deployment

### Hugging Face Spaces (Hackathon target — Free)
The Gradio app deploys to Hugging Face Spaces. It requires a `requirements.txt` and an `app.py`. The Space builds on every push. Set the backend URL and API keys via the Spaces Secrets panel. **HF Spaces is the only deploy target for the hackathon demo.**

### AWS Free Tier (Post-hackathon)
For production, a **t2.micro EC2 instance** runs FastAPI, Redis, and Celery via Docker Compose. PostgreSQL runs on a **db.t2.micro RDS instance**. Both are free for 750 hours/month for 12 months. SSL via Let's Encrypt. Not in the hackathon scope.

**Total infrastructure cost at hackathon scale: ~$0**

---

## MVP Roadmap

**Week 1 — Documentation Agent (doctor's biggest pain point)**
- Whisper transcription of consultation audio
- LLM Wiki with 5 seeded condition pages
- SOAP note draft with ICD-10 codes in under 60 seconds
- Doctor approval UI in Gradio
- PostgreSQL patient records

**Week 2 — Appointment Agent + Duty Rostering Agent (nurse / admin pain points)**
- Google Calendar MCP for slot availability
- Booking confirmation email via Gmail MCP
- Celery reminder queue (T-24h email, T-1h chat)
- Gradio chat widget (stand-in for WhatsApp during demo)
- Greedy 14-day roster generation from a staff CSV
- Sick-call replacement finder

The three shipping agents above, working together, address the three biggest pain points and make for a compelling demo. The remaining agents (Handover, Discharge, Post-Discharge Follow-Up, Clerical, Wiki Maintenance) are routable through the orchestrator and described as "coming soon" — not fully implemented.

**Post-Hackathon (in order)**
1. Handover Agent
2. Discharge Agent (full 5-stream fan-out)
3. Post-Discharge 72h Follow-Up
4. Clerical Agent (referrals, FAQ classification)
5. Wiki Maintenance Agent
6. Insurance / Referral automation
7. WhatsApp Business API production number (one-day swap from the chat widget)
8. OR-Tools constraint solver upgrade for rostering
9. Local Ollama fallback path validated end-to-end

**Explicitly out of scope** until there is a paying customer asking: ABDM / ABHA integration, multi-hospital tenancy, Antibiotic Stewardship.

---

## Clinical Safety

- Every clinical recommendation is traceable to a specific wiki page or guideline source
- No agent sends a clinical communication without doctor approval
- All patient data handled in compliance with India's **Digital Personal Data Protection Act (DPDPA)**
- Full audit trail via Langfuse for every agent action

---
