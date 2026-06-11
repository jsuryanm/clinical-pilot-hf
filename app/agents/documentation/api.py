"""Documentation Agent — public API. OWNER: Person A.

Pipeline (Day 3):

    audio | transcript
        -> retrieve patient wiki + guideline pages + ICD-10 candidates
        -> render soap_v1 prompt
        -> router.complete(task="soap_note", json_mode=True)   # Qwen3-32B on Groq
        -> parse + validate into SOAPNoteDraft

Every guideline page and patient page we retrieve is attached to the draft's
``sources`` — that citation guarantee is the clinical-safety contract, so it is
enforced here rather than trusted to the model. ``approve_draft`` (Day 4) then
persists an (optionally edited) draft to the patient's wiki page.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import structlog

from app.agents.documentation.retrieval import RetrievalContext, retrieve_context
from app.agents.wiki import api as wiki_api
from app.contracts import (
    Citation,
    ICD10Suggestion,
    PatientWikiPageRef,
    SOAPNoteDraft,
    SOAPSection,
)
from app.integrations import whisper
from app.llm.router import complete

log = structlog.get_logger(__name__)

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "soap_v1.md"
_TASK = "soap_note"
_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(\{.*\})\s*```", re.DOTALL)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def draft_soap(
    *,
    patient_id: str,
    audio_path: Path | None = None,
    transcript: str | None = None,
) -> SOAPNoteDraft:
    """Build a SOAP note draft from audio or a transcript.

    Exactly one of ``audio_path`` / ``transcript`` is required; if both are
    given the transcript wins (audio is not re-transcribed).
    """
    if transcript is None:
        if audio_path is None:
            raise ValueError("draft_soap needs either audio_path or transcript")
        transcript = whisper.transcribe(audio_path)
    transcript = transcript.strip()
    if not transcript:
        raise ValueError("transcript is empty")

    ctx = retrieve_context(transcript, patient_id)
    messages = _build_messages(transcript, ctx)

    result = complete(task=_TASK, messages=messages, json_mode=True, max_tokens=2048)
    payload = _parse_json(result.text)

    draft = _assemble_draft(
        patient_id=patient_id,
        transcript=transcript,
        ctx=ctx,
        payload=payload,
        model=result.model,
    )
    log.info(
        "documentation.draft_ready",
        patient_id=patient_id,
        draft_id=draft.draft_id,
        n_sources=len(draft.sources),
        latency_ms=round(result.latency_ms, 1),
    )
    return draft


def approve_draft(draft: SOAPNoteDraft, edits: dict | None = None) -> PatientWikiPageRef:
    """Persist a SOAP draft (with optional doctor edits) to the patient wiki page.

    ``edits`` may carry doctor-edited SOAP fields, e.g.
    ``{"plan": "...", "assessment": "..."}`` — they overwrite the matching
    fields before the draft is written to the patient's Encounter History.
    """
    if edits:
        soap = draft.soap.model_copy(
            update={k: v for k, v in edits.items() if k in SOAPSection.model_fields}
        )
        draft = draft.model_copy(update={"soap": soap})

    return wiki_api.update_patient_page(draft.patient_id, draft)


# ---------------------------------------------------------------------------
# Prompt rendering
# ---------------------------------------------------------------------------


def _build_messages(transcript: str, ctx: RetrievalContext) -> list[dict[str, str]]:
    """Render soap_v1.md into a system + user message pair."""
    template = _PROMPT_PATH.read_text(encoding="utf-8")
    system, user = _split_prompt(template)

    filled = (
        user.replace("{{transcript}}", transcript)
        .replace("{{patient_wiki_excerpt}}", ctx.patient_wiki or "No prior wiki page on file.")
        .replace("{{retrieved_guideline_excerpts}}", _format_guidelines(ctx))
        .replace("{{icd10_candidates}}", _format_icd(ctx))
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": filled},
    ]


def _split_prompt(template: str) -> tuple[str, str]:
    """Split soap_v1.md into the System block and the Inputs+Output block."""
    sys_marker, inputs_marker = "## System", "## Inputs"
    if sys_marker in template and inputs_marker in template:
        system = template.split(sys_marker, 1)[1].split(inputs_marker, 1)[0].strip()
        user = inputs_marker + template.split(inputs_marker, 1)[1]
        return system, user.strip()
    # Fallback: whole template as the user message.
    return "You are CliniqAI's Documentation Agent.", template.strip()


def _format_guidelines(ctx: RetrievalContext) -> str:
    if not ctx.guidelines:
        return "No matching guideline pages found."
    return "\n\n".join(
        f"[{g.page_id}] {g.title}\n{g.excerpt}" for g in ctx.guidelines
    )


def _format_icd(ctx: RetrievalContext) -> str:
    if not ctx.icd_candidates:
        return "No ICD-10 candidates retrieved."
    return "\n".join(f"- {h.doc_id}: {h.text}" for h in ctx.icd_candidates)


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


def _parse_json(text: str) -> dict:
    """Parse the model's JSON, tolerating ```json fences and leading prose."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = _JSON_FENCE_RE.search(text)
    if not m:
        # Last resort: grab the outermost {...} span.
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            raise ValueError(f"model did not return JSON: {text[:200]!r}")
        m_text = text[start : end + 1]
    else:
        m_text = m.group(1)
    return json.loads(m_text)


def _find_soap(payload: dict) -> dict:
    """Locate the SOAP object regardless of how the model wrapped it.

    Models inconsistently nest the note under "soap", "soap_note", etc., or
    emit the fields flat at the top level — tolerate all of them.
    """
    for key in ("soap", "soap_note", "SOAP", "soapNote", "note"):
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return payload  # flat shape


def _coerce_field(value: object) -> str:
    """Render a SOAP field as clean text, whatever shape the model returned.

    Strings pass through; dicts become "key: value" joined by " · "; lists
    become one bullet per item — so a nested object/array never leaks into the
    UI as an ugly Python ``repr``.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "\n".join(f"- {item}" for item in map(_coerce_field, value) if item)
    if isinstance(value, dict):
        parts = [
            f"{str(k).replace('_', ' ')}: {text}"
            for k, text in ((k, _coerce_field(v)) for k, v in value.items())
            if text
        ]
        return " · ".join(parts)
    return str(value).strip()


def _pick(soap_in: dict, payload: dict, key: str, default: object) -> object:
    """Read a top-level field from the SOAP object or the payload root.

    Models sometimes nest referral_needed / confidence_overall / suggestions
    inside the SOAP wrapper instead of at the top level — check both.
    """
    if isinstance(soap_in, dict) and key in soap_in:
        return soap_in[key]
    return payload.get(key, default)


def _assemble_draft(
    *,
    patient_id: str,
    transcript: str,
    ctx: RetrievalContext,
    payload: dict,
    model: str,
) -> SOAPNoteDraft:
    """Build a validated SOAPNoteDraft from the model payload + retrieved context.

    Deterministic fields (ids, timestamps, model) and the citation list are set
    here so the audit trail never depends on the model getting them right.
    """
    soap_in = _find_soap(payload)
    soap = SOAPSection(
        subjective=_coerce_field(soap_in.get("subjective")),
        objective=_coerce_field(soap_in.get("objective")),
        assessment=_coerce_field(soap_in.get("assessment")),
        plan=_coerce_field(soap_in.get("plan")),
    )

    icd = _coerce_icd(_pick(soap_in, payload, "icd10_suggestions", None), ctx)
    sources = _build_sources(ctx)

    return SOAPNoteDraft(
        draft_id=f"soap-{uuid4().hex[:8]}",
        patient_id=patient_id,
        encounter_ts=datetime.now(timezone.utc),
        soap=soap,
        icd10_suggestions=icd,
        guideline_suggestions=[
            str(g)
            for g in (_pick(soap_in, payload, "guideline_suggestions", []) or [])
            if str(g).strip()
        ],
        sources=sources,
        referral_needed=bool(_pick(soap_in, payload, "referral_needed", False)),
        confidence_overall=_clamp(_pick(soap_in, payload, "confidence_overall", 0.0)),
        transcript_excerpt=transcript[:280],
        model=model,
    )


def _coerce_icd(raw: object, ctx: RetrievalContext) -> list[ICD10Suggestion]:
    """Prefer the model's ICD picks; fall back to top index candidates."""
    out: list[ICD10Suggestion] = []
    if isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict) or not item.get("code"):
                continue
            out.append(
                ICD10Suggestion(
                    code=str(item["code"]),
                    label=str(item.get("label", "")),
                    confidence=_clamp(item.get("confidence", 0.5)),
                )
            )
    if out:
        return out
    # Fallback: surface the top index hits so the doctor still sees candidates.
    for hit in ctx.icd_candidates[:3]:
        label = hit.text.split(maxsplit=1)[1] if " " in hit.text else hit.text
        out.append(ICD10Suggestion(code=hit.doc_id, label=label, confidence=0.4))
    return out


def _build_sources(ctx: RetrievalContext) -> list[Citation]:
    """Citation for every retrieved guideline + the patient page (audit contract)."""
    sources: list[Citation] = []
    for g in ctx.guidelines:
        sources.append(
            Citation(
                source_type="wiki",
                source_id=g.page_id,
                title=g.title,
                snippet=g.excerpt[:200] if g.excerpt else None,
            )
        )
    if ctx.patient_wiki is not None:
        sources.append(
            Citation(source_type="wiki", source_id="patients", title="Patient history")
        )
    return sources


def _clamp(value: object, lo: float = 0.0, hi: float = 1.0) -> float:
    try:
        return max(lo, min(hi, float(value)))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return lo
