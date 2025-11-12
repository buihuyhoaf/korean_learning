from types import SimpleNamespace

import language_tool_python
import pytest

from src.app.services import writing_ai


class _DummyMatch:
    """Lightweight stand-in for language_tool_python.Match used in tests."""

    def __init__(self, category_id: str):
        category = SimpleNamespace(id=category_id)
        rule = SimpleNamespace(category=category)
        self.rule = rule


@pytest.mark.asyncio
async def test_evaluate_writing_with_ai_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Service should return scores and feedback when LanguageTool succeeds."""

    matches = [_DummyMatch("typos"), _DummyMatch("grammar")]

    async def fake_check(text: str):
        assert text == "Xin chào thế giới"
        return matches, text

    monkeypatch.setattr(writing_ai, "_run_languagetool_check", fake_check)

    result = await writing_ai.evaluate_writing_with_ai("Xin chào thế giới")

    assert result.is_fallback is False
    assert result.score is not None
    assert result.spelling_errors == 1
    assert result.grammar_errors == 1
    assert "Chính tả" in result.feedback
    assert "Spelling" in result.feedback


@pytest.mark.asyncio
async def test_evaluate_writing_with_ai_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Service should return fallback feedback when LanguageTool fails."""

    async def fake_check(_text: str):
        raise language_tool_python.LanguageToolError("Service unavailable")  # type: ignore[attr-defined]

    monkeypatch.setattr(writing_ai, "_run_languagetool_check", fake_check)
    monkeypatch.setattr(writing_ai, "asyncio", SimpleNamespace(sleep=lambda *_args, **_kwargs: None))

    result = await writing_ai.evaluate_writing_with_ai("Bài viết lỗi service")

    assert result.is_fallback is True
    assert result.score is None
    assert "Không thể kết nối dịch vụ" in result.feedback

