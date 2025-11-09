from __future__ import annotations

import io
import json
import logging
import wave
from functools import lru_cache
from typing import Any

import numpy as np
from rapidfuzz.distance import Levenshtein
from rapidfuzz.distance import JaroWinkler
from vosk import KaldiRecognizer, Model

from ..core.config import settings

LOGGER = logging.getLogger(__name__)


class PronunciationModelNotConfigured(RuntimeError):
    """Raised when Vosk model is not configured."""


@lru_cache
def _load_vosk_model() -> Model:
    model_path = settings.PRONUNCIATION_VOSK_MODEL_PATH
    if not model_path:
        raise PronunciationModelNotConfigured("PRONUNCIATION_VOSK_MODEL_PATH is not set")
    try:
        return Model(model_path)
    except Exception as exc:  # pragma: no cover - defensive logging
        raise PronunciationModelNotConfigured(
            f"Failed to load Vosk model at {model_path}: {exc}"
        ) from exc


def _ensure_wav_buffer(audio_bytes: bytes, sample_rate: int = 16_000) -> bytes:
    """
    Ensure audio bytes are in a WAV container.

    Accepts either raw PCM16 mono data or WAV data.
    """
    with io.BytesIO(audio_bytes) as buf:
        try:
            with wave.open(buf, "rb") as wf:
                wf.getparams()  # Validate header
                return audio_bytes
        except wave.Error:
            pass

    audio_array = np.frombuffer(audio_bytes, dtype=np.int16)
    with io.BytesIO() as wav_buffer:
        with wave.open(wav_buffer, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(audio_array.tobytes())
        return wav_buffer.getvalue()


def transcribe_audio(audio_bytes: bytes) -> str:
    wav_bytes = _ensure_wav_buffer(audio_bytes)
    recognizer = KaldiRecognizer(_load_vosk_model(), 16_000)
    recognizer.SetWords(True)

    with wave.open(io.BytesIO(wav_bytes), "rb") as wf:
        transcript_parts: list[str] = []
        while True:
            data = wf.readframes(4000)
            if not data:
                break
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                transcript_parts.append(result.get("text", ""))

    final_result = json.loads(recognizer.FinalResult())
    transcript_parts.append(final_result.get("text", ""))
    transcript = " ".join(part for part in transcript_parts if part).strip()
    LOGGER.debug("Vosk transcript: %s", transcript)
    return transcript


def _normalize(text: str) -> str:
    normalized = text.strip()
    normalized = normalized.replace("  ", " ")
    return normalized


def compare_pronunciation(transcript: str, target: str) -> float:
    normalized_transcript = _normalize(transcript)
    normalized_target = _normalize(target)
    if not normalized_transcript or not normalized_target:
        return 0.0

    levenshtein_ratio = 1.0 - (Levenshtein.distance(normalized_transcript, normalized_target) /
                               max(len(normalized_transcript), len(normalized_target)))
    jw_score = JaroWinkler.normalized_similarity(normalized_transcript, normalized_target)
    combined_score = max(0.0, min(1.0, (levenshtein_ratio + jw_score) / 2))
    return combined_score


def evaluate_pronunciation(audio_bytes: bytes, sentence: str) -> dict[str, Any]:
    transcript = transcribe_audio(audio_bytes)
    score = compare_pronunciation(transcript, sentence)
    return {
        "transcript": transcript,
        "score": score,
        "passed": score >= settings.PRONUNCIATION_SCORE_THRESHOLD,
    }

