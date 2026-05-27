# Person A — Doctor Brain (Documentation & Knowledge)

> Owner of the **knowledge layer** and everything that goes *into* and *out of* the patient wiki. If a doctor sees it, you probably built it.

---

## 1. What you own

| Area | Folder(s) |
|---|---|
| Documentation Agent | `app/agents/documentation/` |
| Wiki Maintenance Agent | `app/agents/wiki/` |
| LLM Wiki (markdown corpus) | `wiki/` |
| Whisper integration | `app/integrations/whisper.py` |
| ChromaDB vector index | `app/retrieval/chroma_index.py` |
| BM25 keyword index | `app/retrieval/bm25_index.py` |
| Doctor Gradio tab | `app/ui/doctor_tab.py` |
| RAGAS / DeepEval suite | `evals/ragas/` |
| Tests | `tests/test_documentation/`, `tests/test_wiki/` |

## 2. What Person C gives you on Day 0 (so you are unblocked)

- `app/contracts.py` with stub `SOAPNoteDraft`, `PatientWikiPageRef`, `CliniqState`
- `app/llm/router.py` — call it as `router.complete(task="soap_note", messages=[...])` and it picks Qwen3-32B on Groq
- `docker-compose.dev.yml` — bring up Postgres, Redis, Langfuse on fixed ports
- An empty FastAPI router (`app/api/routers/documentation.py`) for you to fill in

You **do not need** the orchestrator, appointment agent, or any backend logic from B/C to start. You consume the contracts and run your agent standalone via a `python -m app.agents.documentation.cli` script.

## 3. What you must publish for the rest of the team

- `app/agents/documentation/mocks.py` — `def fake_soap_draft() -> SOAPNoteDraft` returning a realistic note. **Ship this on Day 1** so B and C can demo without you.
- `wiki/README.md` — describes the wiki page schema (frontmatter, sections, cross-link syntax) so C's Wiki tools and B's discharge agent can read pages safely.
- `app/retrieval/index_api.py` — single function `search(query, top_k, mode='hybrid') -> list[Hit]` that hides Chroma + BM25 behind one interface.

---

## 4. Day-by-day

### Day 0 — Kickoff (2 hrs)
- Lock the wiki page schema with C: frontmatter (`type`, `id`, `last_updated`, `supersedes`, `cross_refs`), required sections (`Summary`, `Current Guideline`, `Drug Interactions`, `History`).
- Pick the 5 seed conditions for Week 1. Recommended: **Hypertension, Type-2 Diabetes, Community-Acquired Pneumonia, Acute Gastroenteritis, Asthma exacerbation** — all common in Indian OPD, all have clear ICMR / WHO guidelines.
- Create `wiki/conditions/`, `wiki/drugs/`, `wiki/patients/`, `wiki/protocols/` empty dirs with `.gitkeep`.

### Day 1 — Wiki seed + retrieval bones
- Write the 5 condition pages using publicly available ICMR / NICE summaries (cite sources in frontmatter).
- Build `chroma_index.py` ingesting a 200-row sample of ICD-10 codes from the WHO file.
- Build `bm25_index.py` over the same sample.
- Wrap both behind `index_api.search()`.

### Day 2 — Whisper online
- Add `app/integrations/whisper.py` using `transformers` Whisper-large-v3 (HF inference endpoint for hackathon, local fallback documented).
- Add an audio file → transcript CLI: `python -m app.integrations.whisper sample.wav`.
- Smoke test on 3 Indian-English medical samples (record yourself reading a short consult).

### Day 3 — Documentation Agent v1
- Pipeline: transcript → retrieve patient wiki page + relevant guideline + ICD-10 candidates → prompt Qwen3-32B → return `SOAPNoteDraft`.
- Prompt lives in `app/agents/documentation/prompts/soap_v1.md` (versioned).
- Every retrieval result must be cited in the draft's `sources` field — this is the clinical-safety contract.

### Day 4 — Doctor Gradio tab
- Three panes: **Record / Upload Audio**, **Live Draft** (markdown), **Approve / Edit / Reject**.
- "Approve" calls `wiki.update_patient_page(patient_id, draft)` — this writes the markdown file and commits to a `wiki-history` git repo (audit trail).
- Show inline citations as hover tooltips.

### Day 5 — Evaluations
- 10 golden cases in `evals/ragas/golden/*.json` (transcript + expected SOAP fields).
- Run RAGAS `faithfulness`, `answer_relevancy`, `context_precision`.
- Target: `faithfulness ≥ 0.85` before demo.

### Day 6–7 — Polish
- Add 5 more wiki pages.
- Add doctor "edit reason" capture — this becomes training data later.
- Edge cases: empty audio, very long consults (chunked), Hindi-English code-mixed input.

### Day 8 — Wiki Maintenance Agent
- A scheduled job (Celery beat — C wires the schedule, you write the task) that:
  - Lints frontmatter (missing required fields)
  - Detects contradictions across pages (two drug pages with conflicting interactions)
  - Flags stale pages (`last_updated > 180 days`)
  - Writes a report to `wiki/_lint_report.md`

### Day 9 — Guideline ingestion
- CLI: `python -m app.agents.wiki ingest --source new_guideline.pdf`
- Agent reads the PDF, identifies which wiki pages it touches, drafts diff, marks superseded sections, updates `cross_refs`. Doctor approves the diff in the UI.

### Day 10–13 — Hardening
- Add 10 more wiki pages (target: 20 conditions, 30 drugs).
- Vision support: route lab-report image uploads to Gemma-4-31B via OpenRouter, extract values into structured fields the SOAP draft can cite.
- RAGAS gate: ≥ 0.85 on 50-case set, no regression on PRs.

### Day 14 — Demo prep
- Three rehearsed cases: (1) routine hypertension follow-up with vitals, (2) suspected pneumonia with chest X-ray upload, (3) diabetic with stale guideline that the wiki has just updated — show the doctor seeing the new recommendation surface.

---

## 5. Interfaces you publish

```python
# app/agents/documentation/api.py
def draft_soap(
    *, patient_id: str, audio_path: Path | None = None,
    transcript: str | None = None,
) -> SOAPNoteDraft: ...

def approve_draft(draft: SOAPNoteDraft, edits: dict | None = None) -> PatientWikiPageRef: ...

# app/retrieval/index_api.py
def search(query: str, top_k: int = 5, mode: Literal["vector","bm25","hybrid"] = "hybrid") -> list[Hit]: ...

# app/agents/wiki/api.py
def update_patient_page(patient_id: str, draft: SOAPNoteDraft) -> PatientWikiPageRef: ...
def get_patient_page(patient_id: str) -> str | None: ...   # returns markdown
def lint_wiki() -> WikiLintReport: ...
```

## 6. Definition of Done (your slice)

- [ ] `mocks.py` published Day 1 — unblocks B and C
- [ ] 20 wiki pages live
- [ ] SOAP draft completes in < 60s on Qwen3-32B
- [ ] RAGAS faithfulness ≥ 0.85 on 50-case set
- [ ] Doctor tab works end-to-end on HF Space
- [ ] Wiki lint report runs nightly, surfaces in nurse-admin tab (C exposes it)
- [ ] Every retrieval has a Langfuse trace attached
- [ ] Zero PHI in the repo

## 7. Things you can safely ignore

- The orchestrator routing logic (C)
- WhatsApp, Calendar, Gmail (B)
- Postgres schema — you read/write the wiki and ChromaDB only
- Roster, handover, discharge (B / C)
- Deployment — C handles `app.py` for HF Spaces; you just keep `doctor_tab.py` importable
