"""Whisper transcription via Groq. OWNER: Person A.

Audio is transcribed with Groq's hosted Whisper (``whisper-large-v3-turbo`` by
default) through LiteLLM, reusing the same ``GROQ_API_KEY`` already used for LLM
calls throughout the project. No local GPU and no model download — there is no
on-device fallback.

Override the model with ``WHISPER_MODEL``. A bare Groq id
(``whisper-large-v3-turbo``) is expected, but an ``openai/`` or ``groq/`` prefix
is tolerated and normalized.

litellm is imported lazily so this module imports cleanly before ``uv sync``
has installed it (mirrors the guard in ``app/llm/router.py``).

CLI::

    python -m app.integrations.whisper sample.wav
    python -m app.integrations.whisper sample.wav --language hi
"""

from __future__ import annotations

import os
from pathlib import Path

import structlog

log = structlog.get_logger(__name__)

# WHISPER_MODEL may be set bare ("whisper-large-v3-turbo") or with an
# org/provider prefix; _groq_model() normalizes it to LiteLLM's "groq/<id>".
_WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo")


def _groq_model() -> str:
    """Normalize WHISPER_MODEL to LiteLLM's ``groq/<model>`` string."""
    name = _WHISPER_MODEL.split("/")[-1]  # drop any "openai/" or "groq/" prefix
    return f"groq/{name}"


def transcribe(audio_path: Path | str, language: str = "en") -> str:
    """Transcribe an audio file to text via Groq Whisper.

    Args:
        audio_path: path to a wav/mp3/m4a/flac file.
        language: ISO-639-1 hint (e.g. "en", "hi"). Whisper auto-detects, but
            the hint improves accuracy on code-mixed Indian-English consults.

    Returns:
        The transcript text (stripped).

    Raises:
        FileNotFoundError: if the audio file is missing.
        RuntimeError: if GROQ_API_KEY is unset, litellm is missing, or the
            Groq API call fails.
    """
    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"audio file not found: {path}")

    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError(
            "GROQ_API_KEY is not set — required for Groq Whisper transcription"
        )

    try:
        from litellm import transcription as _litellm_transcription
    except ImportError as exc:
        raise RuntimeError("litellm is not installed — run `make install`") from exc

    model = _groq_model()
    with path.open("rb") as audio_file:
        response = _litellm_transcription(
            model=model,
            file=audio_file,
            **({"language": language} if language else {}),
        )

    text = (response.text or "").strip()
    log.info("whisper.groq_ok", model=model, chars=len(text))
    return text


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Transcribe an audio file with Groq Whisper"
    )
    parser.add_argument("audio", type=Path, help="path to a wav/mp3/m4a/flac file")
    parser.add_argument("--language", default="en", help="ISO-639-1 hint, e.g. en / hi")
    args = parser.parse_args()

    print(transcribe(args.audio, language=args.language))


if __name__ == "__main__":
    _main()
