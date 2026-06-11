"""LiteLLM router — the ONLY place we call language models.

Routing table follows README §Recommended Routing Strategy:
  - heavy reasoning  → Qwen3-32B on Groq
  - light / fast     → Llama-3.1-8B on Groq
  - groq fallback    → Gemma-2-27B-IT on OpenRouter (free tier)
  - offline / demo   → Qwen2.5:32B on local Ollama

If a primary model fails (rate limit, network, 5xx), we try the next entry
in the fallback chain. All calls are wrapped in a Langfuse generation span.
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import structlog

from dotenv import load_dotenv

load_dotenv()

try:
    from litellm import completion as _litellm_completion
    from litellm.exceptions import APIError, BadRequestError,RateLimitError, ServiceUnavailableError
except ImportError:  # pragma: no cover — uv may not be sync'd yet on first clone
    _litellm_completion = None  # type: ignore[assignment]

    class APIError(Exception):
        ...

    class RateLimitError(Exception):
        ...

    class ServiceUnavailableError(Exception):
        ...


log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Routing table
# ---------------------------------------------------------------------------

# task name -> ordered fallback chain (LiteLLM model string)
# AFTER
# AFTER — Groq only, llama as internal fallback
ROUTES: dict[str, list[str]] = {
    "soap_note":         ["groq/qwen/qwen3-32b",       "groq/llama-3.1-8b-instant"],
    "handover":          ["groq/qwen/qwen3-32b",       "groq/llama-3.1-8b-instant"],
    "discharge_summary": ["groq/qwen/qwen3-32b",       "groq/llama-3.1-8b-instant"],
    "wiki_update":       ["groq/qwen/qwen3-32b",       "groq/llama-3.1-8b-instant"],
    "roster_reason":     ["groq/qwen/qwen3-32b",       "groq/llama-3.1-8b-instant"],
    "routing":           ["groq/llama-3.1-8b-instant", "groq/qwen-qwen3-32b"],
    "reminder":          ["groq/llama-3.1-8b-instant", "groq/qwen-qwen3-32b"],
    "faq":               ["groq/llama-3.1-8b-instant", "groq/qwen-qwen3-32b"],
    "classify_reply":    ["groq/llama-3.1-8b-instant", "groq/qwen-qwen3-32b"],
    "referral_letter":   ["groq/qwen-qwen3-32b",       "groq/llama-3.1-8b-instant"],
    "default":           ["groq/llama-3.1-8b-instant", "groq/qwen-qwen3-32b"],
}

_RETRY_EXC = (RateLimitError, ServiceUnavailableError, APIError, BadRequestError)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompletionResult:
    text: str
    model: str          # the model that actually answered
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    raw: Any | None = None


def complete(
    *,
    task: str,
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 1024,
    json_mode: bool = False,
    response_format: dict[str, Any] | None = None,
) -> CompletionResult:
    """Route a chat completion through the fallback chain for `task`."""

    chain = ROUTES.get(task, ROUTES["default"])
    last_exc: Exception | None = None

    for model in chain:
        # Filter to providers we actually have keys for.
        if not _provider_available(model):
            log.debug("router.skip", model=model, reason="missing_credentials")
            continue

        t0 = time.perf_counter()
        try:
            kwargs: dict[str, Any] = dict(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            if response_format is not None:
                kwargs["response_format"] = response_format
            elif json_mode:
                kwargs["response_format"] = {"type": "json_object"}

            if _litellm_completion is None:
                raise RuntimeError("litellm is not installed — run `make install`")

            resp = _litellm_completion(**kwargs)
            dt = (time.perf_counter() - t0) * 1000

            choice = resp["choices"][0]["message"]["content"]
            usage = resp.get("usage", {}) or {}
            result = CompletionResult(
                text=choice or "",
                model=model,
                latency_ms=dt,
                prompt_tokens=int(usage.get("prompt_tokens", 0)),
                completion_tokens=int(usage.get("completion_tokens", 0)),
                raw=resp,
            )
            _trace_langfuse(task=task, model=model, messages=messages, result=result)
            log.info("router.ok", task=task, model=model, ms=round(dt, 1))
            return result

        except _RETRY_EXC as exc:
            log.warning("router.fallback", task=task, model=model, exc=str(exc))
            last_exc = exc
            continue
        except Exception as exc:  # unknown error → still try the next model
            log.exception("router.unknown_exc", task=task, model=model)
            last_exc = exc
            continue

    raise RuntimeError(
        f"router: all models in chain for task={task} failed: {last_exc!r}"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _provider_available(model: str) -> bool:
    """Check whether we have the credentials to call this model."""
    if model.startswith("groq/"):
        return bool(os.getenv("GROQ_API_KEY"))
    if model.startswith("openrouter/"):
        return bool(os.getenv("OPENROUTER_API_KEY"))
    if model.startswith("ollama/"):
        return bool(os.getenv("OLLAMA_BASE_URL"))
    return False


def _trace_langfuse(
    *, task: str, model: str, messages: list[dict[str, str]], result: CompletionResult
) -> None:
    """Best-effort Langfuse trace. Never raises into the caller."""
    try:
        from langfuse import Langfuse  # type: ignore[import-not-found]
    except ImportError:
        return
    try:
        lf = Langfuse()
        lf.generation(
            name=f"llm.{task}",
            model=model,
            input=messages,
            output=result.text,
            metadata={"latency_ms": result.latency_ms},
            usage={
                "input": result.prompt_tokens,
                "output": result.completion_tokens,
                "unit": "TOKENS",
            },
        )
    except Exception:  # noqa: BLE001 — observability must never break the app
        logging.getLogger(__name__).debug("langfuse_trace_failed", exc_info=True)
