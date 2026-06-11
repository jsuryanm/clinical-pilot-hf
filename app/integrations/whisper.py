"""Whisper transcription. OWNER: Person A.

Two backends, tried in order:

1. **Groq API via LiteLLM** (default) — calls whisper-large-v3-turbo on Groq.
   Needs ``GROQ_API_KEY``. Fast, no local GPU, reuses the same key already
   used for LLM calls throughout the project.
2. **Local transformers** (fallback) — run a ``transformers`` ASR pipeline
   on-device. Heavier first call (model download) but offline and unmetered.
   Used automatically when ``GROQ_API_KEY`` is unset or
   ``WHISPER_BACKEND=local``.

Both backends are imported lazily so this module imports cleanly before
``uv sync`` has installed the heavy deps (mirrors the litellm guard in
``app/llm/router.py``).

CLI::

    python -m app.integrations.whisper sample.wav
    python -m app.integrations.whisper sample.wav --language hi
"""

from __future__ import annotations

import os
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)

_GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
_GROQ_WHISPER_MODEL = "groq/whisper-large-v3-turbo"   # LiteLLM model string
_LOCAL_WHISPER_MODEL = os.getenv("WHISPER_MODEL", "openai/whisper-large-v3-turbo")
# "auto" prefers groq when GROQ_API_KEY is present, else local.
_BACKEND = os.getenv("WHISPER_BACKEND", "auto").lower()


def transcribe(audio_path: Path | str, language: str = "en") -> str:
    """Transcribe an audio file to text.

    Args:
        audio_path: path to a wav/mp3/m4a/flac file.
        language: ISO-639-1 hint (e.g. "en", "hi"). Whisper auto-detects, but
            the hint improves accuracy on code-mixed Indian-English consults.

    Returns:
        The transcript text (stripped).

    Raises:
        FileNotFoundError: if the audio file is missing.
        RuntimeError: if every available backend fails.
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"audio file not found: {path}")

    use_groq = _BACKEND == "groq" or (_BACKEND == "auto" and bool(_GROQ_API_KEY))

    if use_groq:
        try:
            return _transcribe_groq(path, language)
        except Exception as exc:  # noqa: BLE001
            if _BACKEND == "groq":
                raise
            log.warning("whisper.groq_failed_falling_back_local", exc=str(exc))

    return _transcribe_local(path, language)


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------


def _transcribe_groq(path: Path, language: str) -> str:
    """Groq Whisper API via LiteLLM — uses GROQ_API_KEY, no GPU needed."""
    if not _GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not set — cannot use Groq Whisper backend")

    try:
        from litellm import transcription as _litellm_transcription
    except ImportError as exc:
        raise RuntimeError("litellm is not installed — run `make install`") from exc

    with path.open("rb") as audio_file:
        response = _litellm_transcription(
            model=_GROQ_WHISPER_MODEL,
            file=audio_file,
            **({"language": language} if language else {}),
        )

    text = (response.text or "").strip()
    log.info("whisper.groq_ok", model=_GROQ_WHISPER_MODEL, chars=len(text))
    return text


def _transcribe_local(path: Path, language: str) -> str:
    """On-device transformers ASR pipeline. Lazy-imports torch/transformers."""
    try:
        from transformers import pipeline
    except ImportError as exc:  # pragma: no cover — depends on uv sync
        raise RuntimeError(
            "transformers is not installed and GROQ_API_KEY is not set — "
            "run `make install` or set GROQ_API_KEY to use the Groq backend"
        ) from exc

    asr = pipeline(
        "automatic-speech-recognition",
        model=_LOCAL_WHISPER_MODEL,
        chunk_length_s=30,  # chunk long consults so memory stays bounded
    )
    result = asr(
        str(path),
        generate_kwargs={"language": language} if language else None,
        return_timestamps=False,
    )
    text = (result.get("text", "") if isinstance(result, dict) else str(result)).strip()
    log.info("whisper.local_ok", model=_LOCAL_WHISPER_MODEL, chars=len(text))
    return text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Transcribe an audio file with Whisper")
    parser.add_argument("audio", type=Path, help="path to a wav/mp3/m4a/flac file")
    parser.add_argument("--language", default="en", help="ISO-639-1 hint, e.g. en / hi")
    args = parser.parse_args()

    print(transcribe(args.audio, language=args.language))


if __name__ == "__main__":
    _main()