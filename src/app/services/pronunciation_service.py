from __future__ import annotations

import io
import logging
from difflib import SequenceMatcher
from typing import Any

from dotenv import load_dotenv
import speech_recognition as sr

from ..core.config import settings

LOGGER = logging.getLogger(__name__)

load_dotenv()


class PronunciationServiceError(RuntimeError):
    """Raised when pronunciation evaluation fails."""


def transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    try:
        recognizer = sr.Recognizer()
        audio_stream = io.BytesIO(audio_bytes)
        audio_stream.name = filename  # type: ignore[attr-defined]
        audio_stream.seek(0)
        with sr.AudioFile(audio_stream) as source:
            audio = recognizer.record(source)
        try:
            transcript = recognizer.recognize_google(audio, language="ko-KR")
        except sr.UnknownValueError:
            transcript = ""
        except sr.RequestError as exc:  # pragma: no cover - external service failure
            LOGGER.error("Google Speech Recognition request error: %s", exc)
            raise PronunciationServiceError(f"Speech recognition request failed: {exc}") from exc
        return transcript.strip()
    except ValueError as exc:
        raise PronunciationServiceError(f"Unsupported audio format: {exc}") from exc
    except Exception as exc:  # pragma: no cover - log unexpected errors
        LOGGER.error("Speech recognition failed: %s", exc)
        raise PronunciationServiceError(f"Speech recognition failed: {exc}") from exc


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

