"""Whisper transcription. OWNER: Person A — Day 2.

Two backends, tried in order:

1. **HF Inference API** (hackathon default) — POST the audio bytes to the
   hosted ``openai/whisper-large-v3`` endpoint. Needs ``HF_TOKEN``. Fast, no
   local GPU, but rate-limited on the free tier.
2. **Local transformers** (documented fallback) — run a ``transformers`` ASR
   pipeline on-device. Heavier first call (model download) but offline and
   unmetered. Used automatically when ``HF_TOKEN`` is unset or
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

import httpx
import structlog

log = structlog.get_logger(__name__)

_HF_TOKEN = os.getenv("HF_TOKEN", "")
_HF_MODEL = os.getenv("WHISPER_MODEL", "openai/whisper-large-v3")
_HF_INFERENCE_URL = os.getenv(
    "WHISPER_HF_URL", "https://api-inference.huggingface.co/models"
)
# "auto" (default) prefers HF when a token is present, else local.
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

    use_hf = _BACKEND == "hf" or (_BACKEND == "auto" and bool(_HF_TOKEN))

    if use_hf:
        try:
            return _transcribe_hf(path, language)
        except Exception as exc:  # noqa: BLE001 — fall back to local on any HF failure
            if _BACKEND == "hf":
                raise
            log.warning("whisper.hf_failed_falling_back_local", exc=str(exc))

    return _transcribe_local(path, language)


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------


def _transcribe_hf(path: Path, language: str) -> str:
    """Hosted HF Inference API. Posts raw audio bytes, returns {"text": ...}."""
    if not _HF_TOKEN:
        raise RuntimeError("HF_TOKEN is not set — cannot use the HF backend")

    url = f"{_HF_INFERENCE_URL}/{_HF_MODEL}"
    headers = {"Authorization": f"Bearer {_HF_TOKEN}"}
    audio_bytes = path.read_bytes()

    with httpx.Client(timeout=120) as client:
        resp = client.post(url, headers=headers, content=audio_bytes)
        resp.raise_for_status()
        data = resp.json()

    # HF returns {"text": "..."} for ASR; some endpoints nest under a list.
    if isinstance(data, list) and data:
        data = data[0]
    text = (data or {}).get("text", "").strip()
    log.info("whisper.hf_ok", model=_HF_MODEL, chars=len(text))
    return text


def _transcribe_local(path: Path, language: str) -> str:
    """On-device transformers ASR pipeline. Lazy-imports torch/transformers."""
    try:
        from transformers import pipeline
    except ImportError as exc:  # pragma: no cover — depends on uv sync
        raise RuntimeError(
            "transformers is not installed and no HF_TOKEN is set — "
            "run `make install` or set HF_TOKEN to use the hosted endpoint"
        ) from exc

    asr = pipeline(
        "automatic-speech-recognition",
        model=_HF_MODEL,
        chunk_length_s=30,  # chunk long consults so memory stays bounded
    )
    result = asr(
        str(path),
        generate_kwargs={"language": language} if language else None,
        return_timestamps=False,
    )
    text = (result.get("text", "") if isinstance(result, dict) else str(result)).strip()
    log.info("whisper.local_ok", model=_HF_MODEL, chars=len(text))
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
