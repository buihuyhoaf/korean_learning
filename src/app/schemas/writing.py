"""
Pydantic schemas for the writing submission workflow.

Phase 1 only introduces learner submission payloads and simple response objects.
Extend these schemas when teacher grading and analytics are implemented.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
import uuid

from pydantic import BaseModel, Field, field_validator, ConfigDict

from ..models.writing_submission import WritingSubmissionStatus


class WritingSubmissionMode(str, Enum):
    """Supported submission targets."""

    AI = "AI"
    TEACHER = "Teacher"

    @classmethod
    def from_str(cls, value: str) -> "WritingSubmissionMode":
        """Normalize common string variants from clients."""
        normalized = value.strip().lower()
        if normalized == "ai":
            return cls.AI
        if normalized == "teacher":
            return cls.TEACHER
        raise ValueError(f"Unsupported submission mode: {value}")


class WritingSubmissionCreate(BaseModel):
    """Payload accepted from learners when submitting a writing exercise."""

    text: str = Field(..., min_length=1, description="Learner's writing content.")
    mode: WritingSubmissionMode = Field(..., description="Evaluation mode: AI or Teacher.")

    @field_validator("mode", mode="before")
    @classmethod
    def _normalize_mode(cls, value: str | WritingSubmissionMode) -> WritingSubmissionMode:
        """Allow case-insensitive inputs such as ``ai`` / ``teacher``."""
        if isinstance(value, WritingSubmissionMode):
            return value
        return WritingSubmissionMode.from_str(value)


class WritingSubmissionResponse(BaseModel):
    """Serialized representation of a writing submission."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    exercise_id: uuid.UUID
    text: str
    status: WritingSubmissionStatus
    ai_score: float | None = None
    ai_feedback: str | None = None
    teacher_spelling_score: float | None = None
    teacher_grammar_score: float | None = None
    teacher_structure_score: float | None = None
    teacher_vocabulary_score: float | None = None
    teacher_feedback: str | None = None
    final_score: float | None = None
    created_at: datetime
    updated_at: datetime


class TeacherGradeSchema(BaseModel):
    """Payload submitted by teachers when grading a writing submission."""

    spelling_score: float = Field(..., ge=0.0, le=10.0, description="Spelling rubric score (0-10).")
    grammar_score: float = Field(..., ge=0.0, le=10.0, description="Grammar rubric score (0-10).")
    structure_score: float = Field(..., ge=0.0, le=10.0, description="Sentence structure rubric score (0-10).")
    vocabulary_score: float = Field(..., ge=0.0, le=10.0, description="Vocabulary rubric score (0-10).")
    feedback: str = Field(..., min_length=1, description="Teacher feedback for the learner.")


class TeacherGradeResponseSchema(BaseModel):
    """Response returned to admin clients after grading."""

    final_score: float
    feedback: str
    status: WritingSubmissionStatus


class WritingLessonResultItem(BaseModel):
    """Single submission entry in lesson-level results."""

    submission_id: uuid.UUID
    exercise_id: uuid.UUID
    mode: WritingSubmissionMode
    status: WritingSubmissionStatus
    ai_score: float | None = None
    ai_feedback: str | None = None
    teacher_spelling_score: float | None = None
    teacher_grammar_score: float | None = None
    teacher_structure_score: float | None = None
    teacher_vocabulary_score: float | None = None
    teacher_feedback: str | None = None
    final_score: float | None = None
    submitted_at: datetime
    updated_at: datetime


class WritingLessonResultsResponse(BaseModel):
    """Aggregated writing submissions for a lesson."""

    lesson_id: uuid.UUID
    submissions: list[WritingLessonResultItem] = Field(default_factory=list)


