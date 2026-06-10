"""Context retrieval for the Documentation Agent. OWNER: Person A — Day 3.

Gathers the three grounding inputs the SOAP prompt needs:

- the patient's wiki page (prior history),
- the most relevant condition guideline page(s), and
- ICD-10 code candidates from the hybrid index.

Guideline retrieval reads the markdown condition pages directly and scores them
by keyword overlap with the transcript. This needs no built index, so the agent
still grounds its guideline citations when ``data/indices`` is empty (the ICD-10
candidates do come from the index and degrade gracefully to an empty list).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import structlog

from app.agents.wiki import api as wiki_api
from app.contracts import Hit
from app.retrieval import index_api

log = structlog.get_logger(__name__)

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONDITIONS_DIR = _REPO_ROOT / "wiki" / "conditions"
_TOKEN_RE = re.compile(r"[a-z0-9]+")
# Sections worth feeding the model as the guideline excerpt.
_EXCERPT_SECTIONS = ("Summary", "Current Guideline", "Drug Interactions")


@dataclass(frozen=True)
class GuidelineExcerpt:
    page_id: str  # wiki id, e.g. "conditions/hypertension"
    title: str
    excerpt: str


@dataclass
class RetrievalContext:
    patient_wiki: str | None = None
    guidelines: list[GuidelineExcerpt] = field(default_factory=list)
    icd_candidates: list[Hit] = field(default_factory=list)


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall(text.lower()) if len(t) > 3}


def _parse_frontmatter(raw: str) -> tuple[dict[str, str], str]:
    """Return (frontmatter dict, body). Tolerates pages without frontmatter."""
    if not raw.startswith("---"):
        return {}, raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return {}, raw
    meta: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()
    return meta, parts[2]


def _sections(body: str) -> dict[str, str]:
    """Split a markdown body into {section-title: text} on ``## `` headers."""
    out: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current is not None:
                out[current] = "\n".join(buf).strip()
            current = line[3:].strip()
            buf = []
        elif current is not None:
            buf.append(line)
    if current is not None:
        out[current] = "\n".join(buf).strip()
    return out


def retrieve_guidelines(transcript: str, top_k: int = 2) -> list[GuidelineExcerpt]:
    """Rank condition pages by keyword overlap with the transcript."""
    if not _CONDITIONS_DIR.exists():
        return []

    query = _tokens(transcript)
    scored: list[tuple[int, GuidelineExcerpt]] = []
    for path in sorted(_CONDITIONS_DIR.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = _parse_frontmatter(raw)
        page_id = f"conditions/{meta.get('id', path.stem)}"
        title = meta.get("title", path.stem)

        score = len(query & _tokens(raw))
        if score == 0:
            continue

        sections = _sections(body)
        excerpt = "\n\n".join(
            f"{name}: {sections[name]}" for name in _EXCERPT_SECTIONS if sections.get(name)
        )
        scored.append((score, GuidelineExcerpt(page_id=page_id, title=title, excerpt=excerpt)))

    scored.sort(key=lambda s: s[0], reverse=True)
    return [g for _, g in scored[:top_k]]


def retrieve_context(
    transcript: str,
    patient_id: str,
    *,
    top_guidelines: int = 2,
    top_icd: int = 8,
) -> RetrievalContext:
    """Assemble patient history + guidelines + ICD-10 candidates for the prompt."""
    ctx = RetrievalContext()

    try:
        ctx.patient_wiki = wiki_api.get_patient_page(patient_id)
    except Exception:  # noqa: BLE001 — a missing patient page must not block drafting
        log.warning("documentation.patient_page_read_failed", patient_id=patient_id)

    ctx.guidelines = retrieve_guidelines(transcript, top_k=top_guidelines)

    try:
        ctx.icd_candidates = index_api.search(transcript, top_k=top_icd, mode="bm25")
    except Exception:  # noqa: BLE001 — drafting works without the ICD index built
        log.warning("documentation.icd_search_failed", exc_info=True)

    log.info(
        "documentation.context_retrieved",
        patient_id=patient_id,
        has_patient_wiki=ctx.patient_wiki is not None,
        n_guidelines=len(ctx.guidelines),
        n_icd=len(ctx.icd_candidates),
    )
    return ctx
