"""Endpoints for grading Korean writing exercises."""

from functools import lru_cache

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import language_tool_python

LanguageToolError = getattr(
    language_tool_python,
    "LanguageToolErrorException",
    getattr(language_tool_python, "LanguageToolError", None),
)
if LanguageToolError is None:
    class LanguageToolError(Exception):  # type: ignore[redefine-in-inner-scope]
        """Fallback when language_tool_python does not expose an error type."""
        pass

# Khởi tạo router riêng cho chức năng chấm điểm
router = APIRouter(prefix="/grade", tags=["grading"])


class KoreanTextPayload(BaseModel):
    """Incoming payload holding the learner's Korean text."""

    text: str = Field(..., min_length=1, description="Đoạn văn bản tiếng Hàn cần chấm điểm.")


class KoreanGradingResponse(BaseModel):
    """Normalized response describing the grading outcome."""

    original_text: str
    corrected_text: str
    spelling_score: float
    grammar_score: float
    feedback: str


# Xác định các nhóm lỗi được xem là chính tả
SPELLING_CATEGORY_HINTS = {"TYPOS", "TYPOGRAPHY", "MISSPELLING", "CASING"}


@lru_cache(maxsize=1)
def get_tool() -> language_tool_python.LanguageToolPublicAPI:
    """Reuse a single LanguageTool public API client for Korean."""

    return language_tool_python.LanguageToolPublicAPI("ko")


def _categorize_matches(matches: list[language_tool_python.Match]) -> tuple[int, int]:
    """Split LanguageTool matches into spelling vs grammar counts."""

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
    """Convert raw error counts into a 0-10 score."""

    if total_tokens <= 0:
        return 10.0

    penalty = min(error_count, total_tokens)
    score = 10.0 * (1.0 - penalty / total_tokens)
    return round(max(0.0, min(10.0, score)), 2)


def _build_feedback(spelling_errors: int, grammar_errors: int) -> str:
    """Compose short Vietnamese feedback based on detected issues."""

    if spelling_errors == 0 and grammar_errors == 0:
        return "Bài viết rất tốt, không phát hiện lỗi chính tả hay ngữ pháp đáng kể."

    parts: list[str] = []
    if spelling_errors:
        parts.append(f"Có {spelling_errors} lỗi chính tả cần xem lại.")
    if grammar_errors:
        parts.append(f"Có {grammar_errors} lỗi ngữ pháp cần điều chỉnh.")

    parts.append("Hãy rà soát lại và luyện tập thêm để bài viết tự nhiên hơn.")
    return " ".join(parts)


# Endpoint POST để chấm điểm bài viết tiếng Hàn
@router.post(
    "/korean",
    response_model=KoreanGradingResponse,
    summary="Chấm bài viết tiếng Hàn bằng LanguageTool",
)
async def grade_korean_text(payload: KoreanTextPayload) -> KoreanGradingResponse:
    """Grade Korean text for spelling and grammar issues."""

    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Vui lòng cung cấp nội dung tiếng Hàn hợp lệ.")

    tool = get_tool()

    try:
        matches = tool.check(text)
        corrected_text = tool.correct(text)
    except LanguageToolError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Không thể kết nối tới dịch vụ kiểm tra ngôn ngữ: {exc}",
        ) from exc

    spelling_errors, grammar_errors = _categorize_matches(matches)
    total_tokens = max(len(text.split()), 1)

    spelling_score = _score_from_counts(spelling_errors, total_tokens)
    grammar_score = _score_from_counts(grammar_errors, total_tokens)

    feedback = _build_feedback(spelling_errors, grammar_errors)

    return KoreanGradingResponse(
        original_text=text,
        corrected_text=corrected_text,
        spelling_score=spelling_score,
        grammar_score=grammar_score,
        feedback=feedback,
    )

