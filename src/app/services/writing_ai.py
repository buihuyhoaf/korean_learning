"""
Support functions for AI-backed writing evaluation.

Phase 1 ships with a placeholder implementation so the API surface is ready.
Replace ``evaluate_writing_with_ai`` with real integration (LanguageTool, LLM,
etc.) during Phase 2.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class WritingAiEvaluationResult:
    """Simple DTO describing AI grading output."""

    score: float | None
    feedback: str | None


async def evaluate_writing_with_ai(text: str) -> WritingAiEvaluationResult:
    """
    Evaluate a learner's writing using AI.

    Notes
    -----
    - Current implementation is a stub. Replace with ``language_tool_python``
      or other services to calculate spelling/grammar scores.
    - Keep the interface async to allow network calls without blocking.
    """

    # TODO(Phase 2): Integrate language-tool-python and return real metrics.
    return WritingAiEvaluationResult(
        score=None,
        feedback="AI evaluation pending implementation.",
    )


