# CliniqAI — Legal Source Catalog for RAG and the LLM Wiki

> What you can upload, what you must license first, and what you must never upload. Verified May 2026.

This document is the **legal gate** on every document that enters CliniqAI's knowledge layers. Read it before ingesting anything.

> ⚠️ **One-line summary:** Use **ICD-10/ICD-11 from WHO**, **SNOMED CT via NRCeS India** (free for India members), **ICMR guidelines**, **WHO guidelines**, **National Formulary of India** and **CDSCO** for everything Indian-context. **Do NOT** ingest **DSM-5**, **British National Formulary (BNF)**, **NICE guidelines** (outside UK), or any **proprietary drug database** without a paid commercial license. **Do NOT** put any real patient data into the repo or send it to a third-party LLM without DPDPA-compliant consent.

---

## 1. Architecture recap — what each layer needs

From the README:

| Layer | What it stores | What you actually upload |
|---|---|---|
| **LLM Wiki** | Patient histories, drug profiles, clinical protocols, SOPs | Markdown pages you (or the Wiki Maintenance Agent) author and update — synthesised from licensed sources |
| **Vector + BM25 RAG** | ICD-10 (95,000+), drug formulary, DSM-5 *(see §6 — replace this)* | The raw classification CSVs / TXT files indexed once at ingestion |
| **PostgreSQL** | Appointments, lab results, roster history | Operational data only; not a clinical knowledge source |
| **LangGraph State** | Current session | In-memory only |

So there are **three classes of documents** to track:

1. **Reference data** (ICD, drug formulary, ATC codes) → flat-file ingestion into BM25 + Chroma
2. **Clinical guidelines** (ICMR, WHO, professional society documents) → synthesised by you into condition/drug wiki pages with citations
3. **Patient data** → DPDPA-governed, never in repo, encrypted at rest, consent-tracked

---

## 2. Reference data — what's safe to ingest into BM25 + Chroma

| Source | License | Cost | Commercial use | What to upload | Attribution |
|---|---|---|---|---|---|
| **ICD-10** (WHO) | WHO classification, freely available for use; treat as **WHO IP, free attribution-required** | Free | ✅ Yes | The full ICD-10 tabular list (chapters I–XXII). Source: `icd.who.int/browse10`. **For India use the ICD-10 base** — the US-specific `ICD-10-CM` is a US clinical modification published by CDC/NCHS (also free). | Cite WHO in the wiki page header and on every UI surface that surfaces a code. |
| **ICD-11** (WHO) | **CC BY-ND 3.0 IGO** — explicitly permits commercial use, clinical decision support, AI training | Free | ✅ Yes — explicitly permitted | Foundation Component + Mortality and Morbidity Statistics linearization. Source: `icd.who.int/browse11`. | **Mandatory citation:** "International Classification of Diseases, Eleventh Revision (ICD-11), World Health Organization (WHO) 2019/2021. Licensed under CC BY-ND 3.0 IGO." May **not** state or imply WHO endorses CliniqAI, and may **not** make "adaptations" (you can copy and search, you can't create a derivative classification). |
| **SNOMED CT — India Edition** | India is a SNOMED CT Member (since 2014); affiliate license is **free for use within India** via NRCeS | Free in India | ✅ Yes (within India) | Apply for an **Affiliate License** at `mlds.ihtsdotools.org/#/landing/IN` (or via `nrces.in`). Download the SNOMED CT International Edition + the India Edition + the India Drug Extension. | Display the SNOMED CT affiliate notice in your About page. Re-license terms apply when going outside India — handle at internationalisation time. |
| **WHO ATC/DDD Index** (drug classification) | Owned by WHO Collaborating Centre for Drug Statistics Methodology; free for personal/research use; **fee for commercial use** | Free non-commercial / fee commercial | Mixed — **request a license** before production | Use the classification *codes* (which are free as factual data) but do **not** redistribute the full WHOCC database commercially without a license. | Request at `whocc.no/atc_ddd_index/license/`. |
| **WHO Model List of Essential Medicines** | CC BY-NC-SA 3.0 IGO (verify on current PDF) | Free | ⚠️ Non-commercial — fine for an MVP / open-source; **revisit when monetising** | Latest list as PDF/JSON. Source: `who.int/publications`. | Cite WHO; if you go commercial, get permission. |
| **National Formulary of India (NFI)** | Published by Indian Pharmacopoeia Commission (IPC), Ministry of Health & Family Welfare, GoI | Free (PDF) | ✅ Generally yes (government work) — cite source | NFI 5th Edition 2016 — 521 drug monographs. Source: NHP `nhp.gov.in/national-formulary-of-india_mtl`. | Cite "National Formulary of India (NFI), 5th edn, 2016, Indian Pharmacopoeia Commission". |
| **CDSCO approved-drugs database** | Government of India open data | Free | ✅ Yes | Approved new drugs CSV from `cdsco.gov.in/opencms/opencms/en/Data-Bank/`. | Cite CDSCO; note the date of snapshot. |
| **RxNorm** (US National Library of Medicine) | Public-domain US government data | Free | ✅ Yes | Useful for cross-mapping Indian generics to international names. Source: `nlm.nih.gov/research/umls/rxnorm`. | Cite NLM. |
| **openFDA drug labelling** | Public domain US government data | Free | ✅ Yes | Drug interactions / contraindications from US FDA labels. Source: `open.fda.gov`. | Cite openFDA. |
| **Loinc** (lab codes) | Loinc license — free for any use including commercial, with attribution | Free | ✅ Yes | Useful if you parse lab reports. Source: `loinc.org`. | Cite Regenstrief Institute. |

### Practical first-week ingestion bundle (Person A — Day 1)

Download and check into a `data/` folder (gitignored — see `.gitignore`):

```
data/icd10/      icdClaML.xml or tab-delim     # WHO ICD-10 base, English
data/icd11/      foundation.json + mms.json    # WHO ICD-11 API export
data/snomed/     SnomedCT_IndiaRelease_*.zip   # NRCeS affiliate distribution
data/nfi/        NFI_2016.pdf + extracted.json # parse once to JSON
data/atc/        atc_2025.csv                  # free for research; license for prod
data/rxnorm/     RxNorm_full_*.zip             # US NLM
data/loinc/      Loinc_*.zip                   # Regenstrief
```

`data/` is gitignored. The first-time ingestion CLI (`python -m app.retrieval.chroma_index ingest --root data/`) builds the Chroma + BM25 indices into `chroma_db/` (also gitignored). The team distributes the indices via a shared bucket, not git.

---

## 3. Clinical guidelines — what to read, synthesise, and cite

The wiki is *your* synthesis of these. You do not copy them verbatim — you summarise, paraphrase, and cite. This is normal fair-use clinical content authorship.

| Source | License | Cost | Use in wiki | Caveat |
|---|---|---|---|---|
| **ICMR guidelines** (Indian Council of Medical Research) | India government work; freely available on `icmr.gov.in/guidelines`. Treat as Government Open Data — paraphrase + cite. | Free | ✅ Primary source for India-specific clinical practice. | Cite ICMR + publication year + the specific document. |
| **WHO clinical guidelines** | Typically CC BY-NC-SA 3.0 IGO on individual PDFs (verify each cover page) | Free | ✅ With NC restriction — fine for MVP; relicense or paraphrase for commercial product | Always check the inside-front-cover license block of the specific PDF. |
| **AIIMS / PGIMER / Indian society guidelines** (Cardiological Society of India, API, ESI, etc.) | Usually free PDFs; copyright varies | Free (web) | ✅ Paraphrase + cite. **Do not redistribute the PDF verbatim.** | Get the specific journal's reuse terms when in doubt. |
| **Open-access PMC / PubMed Central articles** | CC BY, CC BY-NC, or CC BY-NC-SA per article (check each) | Free | ✅ Read freely, cite, paraphrase — never copy paragraphs into the wiki | The article-level license appears on the PMC page. |
| **NICE guidelines (UK)** | **NICE UK Open Content Licence — free in UK only.** International use (which includes India) requires a fee and a license agreement. Plus, BNF and Clinical Knowledge Summaries inside NICE are third-party content NOT covered by the license. | Fee for India | ⚠️ Do not ingest NICE PDFs into the wiki. You may reference NICE's recommendations by name and link, but do not synthesise NICE content into wiki pages without a NICE international licence. | Use ICMR / WHO equivalents instead. |
| **British National Formulary (BNF)** | Proprietary (Pharmaceutical Press / RPS); not covered by NICE's open licence even on the NICE site | Paid | ❌ Do not ingest. | Use **National Formulary of India** instead. |
| **DSM-5 / DSM-5-TR** (American Psychiatric Association) | **All rights reserved.** APA explicitly states: "APA content may **not** be input into generative artificial intelligence or any other machine learning tool without written permission from APA." Electronic-product licenses are available but capped at ≤50% of total criteria, with a per-product fee + value-added requirement. | Paid + restrictive | ❌ **Do not ingest.** This is a legal problem for the README's stated scope. | **Replacement:** Use **ICD-10 Chapter V (F00–F99)** "Mental and behavioural disorders" or **ICD-11 Chapter 06** "Mental, behavioural or neurodevelopmental disorders". Both are WHO and legally usable. See §6. |
| **Harrison's, Davidson's, Bates, KDT, etc. — medical textbooks** | All rights reserved (Elsevier, McGraw-Hill, etc.) | Paid | ❌ Do not ingest. Do not paste chapters into wiki pages. | Use the underlying guideline (ICMR / WHO) that the textbook cites. |
| **UpToDate / DynaMed / BMJ Best Practice** | Subscription-only proprietary | Paid | ❌ Do not ingest. | Cite as a clinician's external reference, do not store. |
| **MIMS India / CIMS / Indian Drug Review** | Proprietary commercial | Paid | ❌ Do not ingest. | Use National Formulary of India + CDSCO. |
| **DrugBank — academic** | Free for academic, paid for commercial | Mixed | ⚠️ Academic version only for non-commercial MVP. Get the commercial license before launch. | Or use RxNorm + openFDA, both free for commercial use. |
| **Wikipedia clinical articles** | CC BY-SA | Free | ⚠️ Permitted but **not appropriate** as a primary clinical source. Use as a tertiary cross-check only. | If you do quote Wikipedia, the SA clause may force your wiki page to also be CC BY-SA — keep wiki-internal authorship as your own writing. |

### Wiki page authorship rules (legal-safe)

1. **Write the page yourself** — your wording, your structure. Paraphrase the guideline; do not copy paragraphs.
2. **Cite every clinical claim** in the page's frontmatter `source:` field with author + year + URL.
3. **Quote sparingly** — short direct quotes (≤ 2 sentences) of a guideline are normal fair use; longer passages need a licence.
4. **Mark the date** the page was synthesised; the Wiki Maintenance Agent's lint catches stale pages (> 180 days).
5. **Never** paste copyrighted text into the wiki and then "ask the LLM to rewrite it." That's a derivative work and inherits the source's license restrictions.

---

## 4. Patient data — DPDPA 2023 + DPDP Rules 2025

India's Digital Personal Data Protection Act was notified on **13 Nov 2025**. The substantive compliance provisions become enforceable on **13 May 2027** — but you should design for them today because the architectural cost of retrofitting later is enormous.

### What DPDPA means concretely for CliniqAI

| Obligation | How CliniqAI complies |
|---|---|
| **Informed, specific, unambiguous consent** before processing personal health data | Patient onboarding step (Person B) records consent in `messages` / a `consents` table with timestamp, purpose, and version of the notice shown |
| **Time-stamped consent history** — every change (withdrawal, modification, re-consent) is logged | Use an append-only `consent_events` table (add to Person C's Day-10 work) |
| **Right to access / correction / erasure** | Doctor + admin tab needs a "Patient data export" and "Patient data delete" action; deletes must cascade to ChromaDB and the wiki patient page |
| **Data localisation for sensitive health data** | Run Postgres + Chroma + wiki files inside an Indian AWS region (ap-south-1 Mumbai or ap-south-2 Hyderabad). Do **not** store patient data in HF Spaces |
| **Emergency exemption** — consent not required for processing during medical emergencies or epidemics | The system may proceed without consent in a flagged emergency, but the event must still be logged for audit |
| **Children's data** — verifiable parental consent (with healthcare exemption for essential services) | If you serve paediatrics, capture guardian identity at booking |
| **Data Protection Officer** for significant data fiduciaries | Designate a DPO before commercial launch (post-hackathon) |

### Patient data + LLM calls

The risky path is sending a patient's identifiable transcript to a third-party LLM API (Groq, OpenRouter). To stay clean:

- **De-identify before the call.** Strip name, exact DOB, address, phone, ABHA ID, MRN. Use a stable pseudonymous ID (e.g. `p-001`) inside the prompt.
- **Track what went where.** Langfuse already traces every call; ensure no raw PHI is in the prompt body — only the pseudonymised version.
- **Offer a local-only mode.** The README's Ollama path (Qwen2.5 32B) is the legal escape hatch for hospitals that refuse third-party processing. Wire this on Day 6 in Person C's roadmap.
- **Consent for transcription.** Before Whisper runs on an audio file, the doctor confirms verbal consent was obtained from the patient ("This consult will be recorded for AI documentation"). The consent timestamp goes into the `soap_drafts.payload` JSON.

### Audio + transcript retention

- **Audio:** delete the file within 24h of the SOAP note being approved. There is no clinical reason to retain it longer; it's the highest-risk artefact.
- **Transcript:** retain only the `transcript_excerpt` field on the approved `SOAPNoteDraft`, not the full transcript.
- **Whisper inference:** run on HF inference for now; for production, run Whisper locally on the EC2 backend to keep the audio inside the Indian region.

---

## 5. ABDM / ABHA integration — what you must follow when wiring it up

Post-hackathon, when CliniqAI connects to ABDM:

- ABHA-linked records are subject to the **Health Data Management Policy (HDMP)** of the National Health Authority — read it before integrating.
- Patients must explicitly link their ABHA ID to your hospital via the NHA consent manager; you cannot store an ABHA ID without consent.
- ABDM-integrated solutions must pass NHA's sandbox certification — budget 2–4 weeks for this.
- You become a **Health Information User (HIU)** or **Health Information Provider (HIP)** depending on direction of flow — the certification differs.

---

## 6. README correction — DSM-5 cannot stay

The current README §"How the Knowledge System Works" lists **DSM-5** in the Vector + BM25 RAG layer. **This is not legally usable** without an APA license, and APA explicitly forbids feeding their content into generative AI. Acting on this:

**Replace with:** *ICD-10 Chapter V (F00–F99) "Mental and behavioural disorders"* (or ICD-11 Chapter 06). These are WHO classifications, free, and explicitly licensed for AI / clinical decision support use.

Suggested README edit (when you're ready to update):

```diff
- | **Vector + BM25 RAG** | ICD-10 codes (95,000+), drug formulary, DSM-5 | Too large for the wiki; needs keyword-precise lookup |
+ | **Vector + BM25 RAG** | ICD-10/11 codes (incl. Chapter V/06 mental health), National Formulary of India, SNOMED CT India Edition | Too large for the wiki; needs keyword-precise lookup |
```

---

## 7. The "Do NOT upload" list — pin this to the wall

- ❌ DSM-5 / DSM-5-TR (any portion, including diagnostic criteria)
- ❌ British National Formulary (BNF) and BNFC
- ❌ NICE guideline PDFs (use outside the UK requires a paid license)
- ❌ MIMS India / CIMS / Indian Drug Review proprietary content
- ❌ DrugBank commercial fields without a commercial license
- ❌ Harrison's, Davidson's, Bates, KDT, Robbins, any copyrighted textbook
- ❌ UpToDate / DynaMed / BMJ Best Practice
- ❌ Paywalled journal articles (Elsevier, Wolters Kluwer, etc.)
- ❌ Any scraped PDF whose copyright statement you have not personally read
- ❌ Real patient records — even "anonymised" ones — into the git repo
- ❌ Real audio recordings into the git repo

---

## 8. The "Safe to upload today" list

- ✅ WHO ICD-10 tabular list
- ✅ WHO ICD-11 foundation + MMS export (CC BY-ND 3.0 IGO)
- ✅ SNOMED CT India Edition (free for India via NRCeS affiliate)
- ✅ National Formulary of India (IPC, MoHFW)
- ✅ CDSCO approved drugs database
- ✅ RxNorm (US NLM)
- ✅ openFDA drug labelling
- ✅ Loinc lab codes
- ✅ ICMR guidelines (cite + paraphrase)
- ✅ WHO clinical guidelines (CC BY-NC-SA — fine for MVP, paraphrase + cite)
- ✅ Open-access PMC articles (check article-level CC license; paraphrase + cite)
- ✅ Synthetic patient data you generate yourself

---

## 9. Citation hygiene — what each wiki page must show

Every clinical wiki page's frontmatter `source:` field must contain at least:

```yaml
source:
  - title: "ICMR National Guidelines on Hypertension Management"
    org: "Indian Council of Medical Research"
    year: 2023
    url: "https://icmr.gov.in/guidelines/..."
    licence: "Government of India — open access"
  - title: "WHO ICD-10 Online — I10 Essential hypertension"
    org: "World Health Organization"
    year: 2024
    url: "https://icd.who.int/browse10/2019/en#/I10"
    licence: "WHO classification — free with attribution"
```

The Wiki Maintenance Agent's lint pass (Person A, Day 8) should fail any page whose `source:` is empty or whose URL returns 404.

---

## 10. Action items (do these before any ingestion)

1. **Apply for SNOMED CT affiliate licence** at `mlds.ihtsdotools.org/#/landing/IN` — free, takes ~2 days.
2. **Read the ICD-11 license PDF** (`icd.who.int/en/docs/icd11-license.pdf`) and save it to `data/legal/icd11-license.pdf`.
3. **Strip DSM-5 from the codebase + README**; replace with ICD-10 Chapter V / ICD-11 Chapter 06.
4. **Add `data/` and `chroma_db/` to `.gitignore`** (already done in this repo).
5. **Add a `consent_events` table** to the Postgres schema (Person C — fold into Day-10 auth/audit work).
6. **Write a `CONSENT.md`** describing the patient-facing consent language for transcription and data processing — this is what doctors will read aloud during the consult.
7. **Pick AWS region** before deploy: ap-south-1 (Mumbai) is the canonical India region for DPDPA-friendly storage.
8. **Schedule a DPO designation** for the first commercial customer — even if it's a co-founder for now.

---

## 11. Sources

- [WHO — ICD-11 License (PDF)](https://cdn.who.int/media/docs/default-source/classification/icd/icd11/icd11-license.pdf)
- [WHO — ICD-11 Terms of Use and License Agreement](https://www.who.int/publications/m/item/icd-11-terms-of-use-and-license-agreement)
- [WHO — International Classification of Diseases](https://www.who.int/standards/classifications/classification-of-diseases)
- [APA — Permissions, Licensing, and Reprints (DSM-5)](https://www.appi.org/Support/Customer-Information/Permissions)
- [Psychiatry Online — Copyright (DSM)](https://psychiatryonline.org/copyright)
- [ICMR — Guidelines](https://www.icmr.gov.in/guidelines)
- [NICE — Reusing our content](https://www.nice.org.uk/re-using-our-content)
- [NICE — Use of NICE content in the UK](https://www.nice.org.uk/reusing-our-content/use-of-nice-content-in-the-uk)
- [NHP India — National Formulary of India](https://www.nhp.gov.in/national-formulary-of-india_mtl)
- [CDSCO — Data Bank](https://cdsco.gov.in/opencms/opencms/en/Data-Bank/Data-Bank-Sub-cat/)
- [NRCeS — SNOMED CT in India](https://www.nrces.in/standards/snomed-ct)
- [SNOMED International — Get SNOMED](https://www.snomed.org/get-snomed)
- [MeitY — DPDP Rules 2025 (PDF, PIB)](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf)
- [Lexology — Navigating India's DPDPA 2025 Draft Rules](https://www.lexology.com/library/detail.aspx?g=afcc7e95-6fb7-4635-b0ee-b1e10104e3e1)
- [Archon Datastore — DPDPA Compliance Guide](https://www.archondatastore.com/blog/dpdpa-compliance-guide/)
- [PMC — Digital Data Protection in Indian Medical Research and Healthcare](https://pmc.ncbi.nlm.nih.gov/articles/PMC11754748/)
