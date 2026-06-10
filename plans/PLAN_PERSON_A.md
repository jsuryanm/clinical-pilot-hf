# Person A — Doctor Brain (Documentation & Knowledge)

> Owner of the **knowledge layer** and the documentation workflow doctors will touch in the demo. If a doctor sees it, you probably built it.

---

## 1. What you own (hackathon scope)

| Area | Folder(s) | Built? |
|---|---|---|
| Documentation Agent | `app/agents/documentation/` | **Yes** |
| LLM Wiki (markdown corpus, **10 seeded pages** target) | `wiki/` | **Yes** |
| Whisper integration | `app/integrations/whisper.py` | **Yes** |
| ChromaDB vector index | `app/retrieval/chroma_index.py` | **Yes** |
| BM25 keyword index | `app/retrieval/bm25_index.py` | **Yes** |
| Doctor Gradio tab | `app/ui/doctor_tab.py` | **Yes** |
| RAGAS suite (30-case gate) | `evals/ragas/` | **Yes** |
| Tests | `tests/test_documentation/` | **Yes** |

### Deferred to post-hackathon

- **Wiki Maintenance Agent** (lint pass, contradiction detection, stale-page flags) — keep `app/agents/wiki/api.py` as a stub only.
- **Guideline ingestion CLI** (drafting diffs from new PDFs).
- **Vision support** (lab-report image upload via Gemma) — not in the demo.
- **20+ wiki pages** — target 10 for the demo, expand later.
- **Doctor "edit reason" capture** as training data — out of scope.

## 2. What Person C gives you on Day 0 (so you are unblocked)

- `app/contracts.py` with stub `SOAPNoteDraft`, `PatientWikiPageRef`, `CliniqState`
- `app/llm/router.py` — call as `router.complete(task="soap_note", messages=[...])` (picks Qwen3-32B on Groq)
- `docker-compose.dev.yml` — Postgres, Redis, Qdrant, Langfuse on fixed ports
- An empty FastAPI router (`app/api/routers/documentation.py`)
- `app/memory/api.py` — `remember(scope, key, text)` and `recall(scope, key, query)` for cross-session memory. Use it to learn doctor edit preferences: when a doctor edits a SOAP draft, `remember(scope="user", key=doctor_id, text=diff_summary)`; on the next draft, `recall(...)` and inject preferences into the prompt. (Stub on Day 0, real Mem0 by Day 2.)

You **do not need** the orchestrator or other agents from B/C to start. Run your agent standalone via `python -m app.agents.documentation.cli`.

## 3. What you must publish for the rest of the team

- `app/agents/documentation/mocks.py` — `def fake_soap_draft() -> SOAPNoteDraft` returning a realistic note. **Ship Day 1.**
- `wiki/README.md` — wiki page schema (frontmatter, sections, cross-link syntax) so C's tools and the demo can read pages safely.
- `app/retrieval/index_api.py` — single function `search(query, top_k, mode='hybrid') -> list[Hit]` hiding Chroma + BM25 behind one interface.

---

## 4. Day-by-day

### Day 0 — Kickoff (2 hrs)
- Lock the wiki page schema with C: frontmatter (`type`, `id`, `last_updated`, `supersedes`, `cross_refs`, `source`), required sections (`Summary`, `Current Guideline`, `Drug Interactions`, `History`).
- Pick the 5 seed conditions for Week 1. Recommended: **Hypertension, Type-2 Diabetes, Community-Acquired Pneumonia, Acute Gastroenteritis, Asthma exacerbation** — all common in Indian OPD, all have clear ICMR / WHO guidelines.
- Create `wiki/conditions/`, `wiki/drugs/`, `wiki/patients/`, `wiki/protocols/` empty dirs with `.gitkeep`.

### Day 1 — Wiki seed + retrieval bones
- Write the 5 condition pages by paraphrasing publicly available ICMR / MoHFW / WHO summaries (cite sources in frontmatter).
- Build `chroma_index.py` ingesting a 200-row sample of ICD-10 codes from the WHO file.
- Build `bm25_index.py` over the same sample.
- Wrap both behind `index_api.search()`.

### Day 2 — Whisper online
- Add `app/integrations/whisper.py` using `transformers` Whisper-large-v3 (HF inference endpoint for hackathon, local fallback documented).
- Audio file → transcript CLI: `python -m app.integrations.whisper sample.wav`.
- Smoke test on 3 Indian-English medical samples (record yourself reading a short consult).

### Day 3 — Documentation Agent v1
- Pipeline: transcript → retrieve patient wiki page + relevant guideline + ICD-10 candidates → prompt Qwen3-32B → return `SOAPNoteDraft`.
- Prompt lives in `app/agents/documentation/prompts/soap_v1.md` (versioned).
- Every retrieval result must be cited in the draft's `sources` field — this is the clinical-safety contract.

### Day 4 — Doctor Gradio tab
- Three panes: **Record / Upload Audio**, **Live Draft** (markdown), **Approve / Edit / Reject**.
- "Approve" writes the markdown file to the patient page and commits to a `wiki-history` audit trail.
- Show inline citations as hover tooltips.

### Day 5 — Evaluations
- 10 golden cases in `evals/ragas/golden/*.json` (transcript + expected SOAP fields).
- Run RAGAS `faithfulness`, `answer_relevancy`, `context_precision`.
- Target: `faithfulness ≥ 0.85` before demo.

### Day 6–7 — Polish
- Edge cases: empty audio, very long consults (chunked), Hindi-English code-mixed input.
- Tighten doctor approval UX — keep it one-screen.

### Day 8 — Wiki growth
- Add 5 more wiki pages (target: 10 conditions total for demo).
- No Wiki Maintenance Agent in this hackathon — schedule for post-hackathon.

### Day 9 — RAGAS gate
- Expand RAGAS to 30 golden cases.
- Gate: ≥ 0.85 faithfulness, no regression on PRs.

### Day 10–11 — Hardening
- Approval UX polish (citation tooltips).
- Edge cases on long consults and Hinglish.

### Day 12 — Demo prep
- Three rehearsed cases:
  1. Routine hypertension follow-up with vitals
  2. Suspected pneumonia (audio only — no image upload for hackathon)
  3. Diabetic with stale guideline that the wiki has just updated — show the doctor seeing the new recommendation surface

### Day 13–14 — Joint dress rehearsal, submission video, buffer

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

# app/agents/wiki/api.py  (stub — only update_patient_page is wired; the rest are placeholders)
def update_patient_page(patient_id: str, draft: SOAPNoteDraft) -> PatientWikiPageRef: ...
def get_patient_page(patient_id: str) -> str | None: ...   # returns markdown
# def lint_wiki() -> WikiLintReport: ...   # post-hackathon
```

## 6. Definition of Done (your slice)

- [ ] `mocks.py` published Day 1 — unblocks B and C
- [ ] **10 wiki pages** live
- [ ] SOAP draft completes in < 60s on Qwen3-32B
- [ ] RAGAS faithfulness ≥ 0.85 on **30-case** set
- [ ] Doctor tab works end-to-end on HF Space
- [ ] Every retrieval has a Langfuse trace attached
- [ ] Zero PHI in the repo

## 7. Things you can safely ignore

- The orchestrator routing logic (C)
- Calendar, Gmail (B)
- Postgres schema — you read/write the wiki and ChromaDB only
- Roster (C)
- Handover, Discharge, Clerical, Wiki Maintenance — all post-hackathon
- Deployment — C handles `app.py` for HF Spaces; you just keep `doctor_tab.py` importable
- Vision support / image lab reports — post-hackathon
- WhatsApp (was B's, now also cut from hackathon)
