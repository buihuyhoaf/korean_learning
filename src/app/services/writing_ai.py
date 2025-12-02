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
from langdetect import detect, LangDetectException

from ..core.config import settings

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

# Mã ngôn ngữ tiếng Hàn được chấp nhận
KOREAN_LANGUAGE_CODES = {"ko", "kor"}


def _detect_language(text: str) -> tuple[str | None, bool]:
    """
    Phát hiện ngôn ngữ của văn bản.
    
    Args:
        text: Văn bản cần phát hiện ngôn ngữ
        
    Returns:
        Tuple (detected_lang, is_korean):
        - detected_lang: Mã ngôn ngữ được phát hiện (ví dụ: 'ko', 'vi', 'en') hoặc None nếu không thể phát hiện
        - is_korean: True nếu là tiếng Hàn, False nếu không
    """
    if not text or len(text.strip()) < 3:
        # Văn bản quá ngắn, không thể phát hiện chính xác
        return None, False
    
    try:
        detected_lang = detect(text)
        is_korean = detected_lang.lower() in KOREAN_LANGUAGE_CODES
        logger.info(f"Detected language: {detected_lang}, is_korean: {is_korean}")
        return detected_lang, is_korean
    except LangDetectException as e:
        logger.warning(f"Language detection failed: {e}")
        return None, False
    except Exception as e:
        logger.error(f"Unexpected error during language detection: {e}")
        return None, False


# Không cache để có thể thử các language code khác nhau
def _get_language_tool() -> language_tool_python.LanguageTool | language_tool_python.LanguageToolPublicAPI:
    """
    Reuse a single LanguageTool client for Korean to avoid cold starts.
    
    Returns:
        LanguageTool instance (local server) or LanguageToolPublicAPI (public API)
    
    Note:
        LanguageTool may not fully support Korean ('ko'). If 'ko' fails, 
        we try 'en-US' as fallback or use auto-detect.
    """
    lang_code = settings.LANGUAGETOOL_LANG
    
    if settings.LANGUAGETOOL_USE_LOCAL:
        # Sử dụng local server (chạy trong cùng container)
        local_url = f"http://localhost:{settings.LANGUAGETOOL_PORT}"
        logger.info(f"Using LanguageTool local server: {local_url} with language: {lang_code}")
        
        # Thử các mã ngôn ngữ khác nhau cho tiếng Hàn
        korean_codes = [lang_code, "ko-KR", "ko_KR", "auto"]
        
        for code in korean_codes:
            try:
                tool = language_tool_python.LanguageTool(
                    language=code,
                    remote_server=local_url
                )
                if code != lang_code:
                    logger.info(f"LanguageTool initialized with language code: {code} (fallback from {lang_code})")
                return tool
            except (ValueError, KeyError) as e:
                logger.debug(f"LanguageTool failed with code '{code}': {e}")
                if code == korean_codes[-1]:  # Last attempt
                    raise
        # Should not reach here, but just in case
        return language_tool_python.LanguageTool(
            language="auto",
            remote_server=local_url
        )
    else:
        # Sử dụng public API (fallback)
        logger.info(f"Using LanguageTool public API with language: {lang_code}")
        # Public API cũng có thể không hỗ trợ 'ko', thử 'auto' nếu fail
        try:
            return language_tool_python.LanguageToolPublicAPI(lang_code)
        except (ValueError, KeyError):
            logger.warning(f"Language code '{lang_code}' not supported, using 'auto' instead")
            return language_tool_python.LanguageToolPublicAPI("auto")


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
    - Uses LanguageTool local server (if configured) or public API as fallback.
    - Wraps LanguageTool failures and returns safe fallback feedback.
    - Validates that the input text is in Korean before evaluation.
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

    # Phát hiện ngôn ngữ trước khi chấm
    detected_lang, is_korean = _detect_language(text)
    
    if not is_korean:
        # Xác định tên ngôn ngữ để hiển thị thông báo
        lang_names = {
            "vi": "tiếng Việt",
            "en": "tiếng Anh",
            "zh": "tiếng Trung",
            "ja": "tiếng Nhật",
            "th": "tiếng Thái",
            "es": "tiếng Tây Ban Nha",
            "fr": "tiếng Pháp",
            "de": "tiếng Đức",
        }
        lang_name = lang_names.get(detected_lang.lower() if detected_lang else "", "ngôn ngữ khác")
        
        if detected_lang:
            feedback_msg = (
                f"Phát hiện bài viết của bạn là {lang_name} (mã: {detected_lang}), "
                "không phải tiếng Hàn. Vui lòng viết lại bằng tiếng Hàn để được chấm điểm chính xác."
            )
        else:
            feedback_msg = (
                "Không thể xác định ngôn ngữ của bài viết. "
                "Vui lòng đảm bảo bạn đang viết bằng tiếng Hàn để được chấm điểm chính xác."
            )
        
        logger.warning(f"Non-Korean text detected: lang={detected_lang}, text_preview={text[:50]}...")
        return WritingAiEvaluationResult(
            score=None,
            feedback=feedback_msg,
            spelling_score=None,
            grammar_score=None,
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
    except (LanguageToolError, ConnectionError, TimeoutError) as exc:
        logger.warning("LanguageTool evaluation failed: %s", exc)
        
        # Fallback: thử public API nếu local server fail
        if settings.LANGUAGETOOL_USE_LOCAL:
            logger.info("Falling back to public API due to local server error")
            try:
                public_tool = language_tool_python.LanguageToolPublicAPI(settings.LANGUAGETOOL_LANG)
                matches = public_tool.check(text)
                corrected_text = public_tool.correct(text)
                
                spelling_errors, grammar_errors = _categorize_matches(matches)
                total_tokens = max(len(text.split()), 1)
                spelling_score = _score_from_counts(spelling_errors, total_tokens)
                grammar_score = _score_from_counts(grammar_errors, total_tokens)
                overall_score = round((spelling_score + grammar_score) / 2.0, 2)
                feedback = _build_feedback(spelling_errors, grammar_errors, corrected_text)
                
                return WritingAiEvaluationResult(
                    score=overall_score,
                    feedback=feedback + " (Sử dụng public API do local server không khả dụng)",
                    spelling_score=spelling_score,
                    grammar_score=grammar_score,
                    corrected_text=corrected_text if corrected_text != text else None,
                )
            except Exception as fallback_exc:
                logger.error("Public API fallback also failed: %s", fallback_exc)
        
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


