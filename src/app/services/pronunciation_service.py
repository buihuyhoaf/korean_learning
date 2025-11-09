from __future__ import annotations

import logging
import os
from difflib import SequenceMatcher
from typing import Any

from functools import lru_cache

from dotenv import load_dotenv
from openai import OpenAI

from ..core.config import settings

LOGGER = logging.getLogger(__name__)

load_dotenv()


class PronunciationServiceError(RuntimeError):
    """Raised when pronunciation evaluation fails."""


@lru_cache(maxsize=1)
def _get_openai_client() -> OpenAI:
    api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
    if not api_key:
        visible_keys = [key for key in os.environ.keys() if "OPENAI" in key.upper()]
        hint = (
            "OPENAI_API_KEY is not set. Ensure the environment variable is defined "
            "exactly as OPENAI_API_KEY (current detected keys: "
            f"{visible_keys or 'none'})."
        )
        raise PronunciationServiceError(hint)
    return OpenAI(api_key=api_key)


def transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    client = _get_openai_client()
    try:
        response = client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=(filename, audio_bytes, "audio/wav"),
        )
    except Exception as exc:  # pragma: no cover - log unexpected errors
        LOGGER.error("OpenAI transcription failed: %s", exc)
        raise PronunciationServiceError(f"Transcription failed: {exc}") from exc

    transcript = (response.text or "").strip()
    if not transcript:
        raise PronunciationServiceError("No transcript returned from OpenAI")
    return transcript


def compare_pronunciation(transcript: str, target: str) -> float:
    normalized_transcript = transcript.strip().lower()
    normalized_target = target.strip().lower()
    if not normalized_transcript or not normalized_target:
        return 0.0
    return SequenceMatcher(a=normalized_transcript, b=normalized_target).ratio()


def evaluate_pronunciation(audio_bytes: bytes, filename: str, sentence: str) -> dict[str, Any]:
    transcript = transcribe_audio(audio_bytes, filename)
    score = compare_pronunciation(transcript, sentence)
    return {
        "transcript": transcript,
        "score": score,
        "passed": score >= settings.PRONUNCIATION_SCORE_THRESHOLD,
    }

