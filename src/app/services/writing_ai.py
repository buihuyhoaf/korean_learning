"""
Support functions for AI-backed writing evaluation.

Phase 1 ships with a placeholder implementation so the API surface is ready.
Replace ``evaluate_writing_with_ai`` with real integration (LanguageTool, LLM,
etc.) during Phase 2.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache

import language_tool_python

LanguageToolError = getattr(
    language_tool_python,
    "LanguageToolErrorException",
    getattr(language_tool_python, "LanguageToolError", None),
)
if LanguageToolError is None:
    class LanguageToolError(Exception):
        """Fallback when language_tool_python does not expose an error type."""
        pass

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WritingAiEvaluationResult:
    """Simple DTO describing AI grading output."""

    score: float | None
    feedback: str
    spelling_score: float | None = None
    grammar_score: float | None = None
    corrected_text: str | None = None


class WritingAiEvaluationError(Exception):
    """Raised when AI evaluation cannot be completed."""


SPELLING_CATEGORY_HINTS = {"TYPOS", "TYPOGRAPHY", "MISSPELLING", "CASING"}


@lru_cache(maxsize=1)
def _get_language_tool() -> language_tool_python.LanguageToolPublicAPI:
    """Reuse a single LanguageTool client for Korean to avoid cold starts."""

    return language_tool_python.LanguageToolPublicAPI("ko")


def _categorize_matches(matches: list[language_tool_python.Match]) -> tuple[int, int]:
    """Split matches into spelling vs grammar buckets."""

    spelling_errors = 0
    grammar_errors = 0
    for match in matches:
        category_id = (match.rule.category.id or "").upper()
        if any(hint in category_id for hint in SPELLING_CATEGORY_HINTS):
            spelling_errors += 1
        else:
            grammar_errors += 1
    return spelling_errors, grammar_errors


def _score_from_counts(error_count: int, total_tokens: int) -> float:
    """Convert error counts into a 0-10 scale."""

    if total_tokens <= 0:
        return 10.0
    penalty = min(error_count, total_tokens)
    score = 10.0 * (1.0 - penalty / total_tokens)
    return round(max(0.0, min(10.0, score)), 2)


def _build_feedback(
    spelling_errors: int,
    grammar_errors: int,
    corrected_text: str | None,
) -> str:
    """Compose short feedback using detected issues."""

    parts: list[str] = []
    if spelling_errors == 0 and grammar_errors == 0:
        parts.append("Bài viết rất tốt, không phát hiện lỗi chính tả hay ngữ pháp đáng kể.")
    else:
        if spelling_errors:
            parts.append(f"Có {spelling_errors} lỗi chính tả cần xem lại.")
        if grammar_errors:
            parts.append(f"Có {grammar_errors} lỗi ngữ pháp cần điều chỉnh.")
        parts.append("Hãy rà soát các câu được gợi ý để cải thiện bài viết.")

    if corrected_text:
        parts.append("Gợi ý chỉnh sửa: " + corrected_text)
    return " ".join(parts)


async def evaluate_writing_with_ai(text: str) -> WritingAiEvaluationResult:
    """
    Evaluate a learner's writing using AI.

    Notes
    -----
    - Uses LanguageTool public API for Korean to detect spelling/grammar issues.
    - Wraps LanguageTool failures and returns safe fallback feedback.
    """

    text = text.strip()
    if not text:
        return WritingAiEvaluationResult(
            score=10.0,
            feedback="Không có nội dung để chấm.",
            spelling_score=10.0,
            grammar_score=10.0,
            corrected_text=None,
        )

    try:
        tool = _get_language_tool()
        matches = tool.check(text)
        corrected_text = tool.correct(text)

        spelling_errors, grammar_errors = _categorize_matches(matches)
        total_tokens = max(len(text.split()), 1)
        spelling_score = _score_from_counts(spelling_errors, total_tokens)
        grammar_score = _score_from_counts(grammar_errors, total_tokens)
        overall_score = round((spelling_score + grammar_score) / 2.0, 2)
        feedback = _build_feedback(spelling_errors, grammar_errors, corrected_text)

        return WritingAiEvaluationResult(
            score=overall_score,
            feedback=feedback,
            spelling_score=spelling_score,
            grammar_score=grammar_score,
            corrected_text=corrected_text if corrected_text != text else None,
        )
    except LanguageToolError as exc:
        logger.warning("LanguageTool evaluation failed: %s", exc)
        return WritingAiEvaluationResult(
            score=None,
            feedback="Không thể kết nối tới dịch vụ kiểm tra ngôn ngữ. Vui lòng thử lại sau.",
        )
    except Exception as exc:  # pragma: no cover - defensive safeguard
        logger.exception("Unexpected error during AI evaluation: %s", exc)
        return WritingAiEvaluationResult(
            score=None,
            feedback="Đã xảy ra lỗi khi chấm bài viết. Vui lòng thử lại sau.",
        )


