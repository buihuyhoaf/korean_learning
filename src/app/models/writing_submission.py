"""
SQLAlchemy model definitions for writing submissions.
"""

from __future__ import annotations

from datetime import UTC, datetime
import uuid
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db.database import Base


class WritingSubmissionStatus(str, Enum):
    """
    Lifecycle states for a learner's writing submission.

    - ``submitted``: Learner just sent the writing; awaiting evaluation.
    - ``ai_graded``: Automatic AI evaluation completed.
    - ``teacher_graded``: Human teacher has provided the final scores.
    """

    SUBMITTED = "submitted"
    AI_GRADED = "ai_graded"
    TEACHER_GRADED = "teacher_graded"


class WritingSubmission(Base):
    """
    Persisted writing submission record.

    Parameters
    ----------
    user_id:
        References the author of the submission (`users.id`).
    exercise_id:
        References the writing exercise (`exercises.id`).
    text:
        Raw text submitted by the learner.
    status:
        Workflow status (see :class:`WritingSubmissionStatus`).
    ai_score / ai_feedback:
        Optional AI-provided evaluation artifacts.
    """

    __tablename__ = "writing_submissions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        init=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    exercise_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exercises.id", ondelete="CASCADE"),
        nullable=False,
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    ai_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    ai_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[WritingSubmissionStatus] = mapped_column(
        SqlEnum(WritingSubmissionStatus, name="writing_submission_status"),
        nullable=False,
        default=WritingSubmissionStatus.SUBMITTED,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Relationships to User / Exercise can be added later when needed for queries.


