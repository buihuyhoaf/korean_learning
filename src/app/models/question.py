"""
Question Model

Core question model that supports multiple question types through polymorphic relationships.
Uses JSONB for flexible media and metadata storage.
"""
from datetime import UTC, datetime
import uuid
from typing import Any

from sqlalchemy import DateTime, String, Integer, Text, ForeignKey, SmallInteger, func, select, event
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship, Session

from ..core.db.database import Base


class Question(Base):
    """
    Core question model that supports 9 different question types.
    
    Attributes:
        id: Primary key
        question_type_id: Foreign key to question_types table
        lesson_id: Foreign key to lessons table (nullable)
        content: Main question content/text
        media: JSONB object storing media files (image, audio, video URLs)
        question_metadata: JSONB object storing type-specific settings (difficulty, hints, etc.)
        explanation: Explanation shown after answering
        order_index: Ordering within the lesson
        created_at: Timestamp when question was created
    """
    __tablename__ = "questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    question_type_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("question_types.id"), nullable=False, index=True)
    lesson_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=False, index=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    media: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)  # {"image": "...", "audio": "...", "video": "..."}
    question_metadata: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)  # Type-specific settings, difficulty, hints
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        init=False
    )

    # Relationships
    question_type_relation = relationship(
        "QuestionType",
        back_populates="questions",
        lazy="selectin"
    )
    lesson = relationship(
        "Lesson",
        back_populates="questions"
    )
    options = relationship(
        "QuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    matching_pairs = relationship(
        "QuestionMatchingPair",
        back_populates="question",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    sentence_order = relationship(
        "QuestionSentenceOrder",
        back_populates="question",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin"
    )
    audio_comprehension = relationship(
        "QuestionAudioComprehension",
        back_populates="question",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin"
    )
    pronunciation = relationship(
        "QuestionPronunciation",
        back_populates="question",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin"
    )
    blanks = relationship(
        "QuestionBlank",
        back_populates="question",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin"
    )
    user_answers = relationship(
        "UserAnswer",
        back_populates="question",
        cascade="all, delete-orphan"
    )
    user_errors = relationship(
        "UserQuestionError",
        back_populates="question",
        cascade="all, delete-orphan"
    )


# Event listener to auto-increment order_index before insert
@event.listens_for(Question, 'before_insert')
def receive_before_insert(mapper, connection, target):
    """Auto-increment order_index if not provided and validate lesson exists."""
    if target.order_index == 0 and target.lesson_id is not None:
        # First, verify that the lesson exists
        from ..models.course import Lesson
        lesson_check = select(Lesson.id).where(Lesson.id == target.lesson_id)
        lesson_result = connection.execute(lesson_check)
        lesson_exists = lesson_result.scalar_one_or_none()
        
        if lesson_exists is None:
            raise ValueError(f"Lesson with id {target.lesson_id} does not exist")
        
        # Get max order_index for this lesson
        stmt = select(func.max(Question.order_index)).where(
            Question.lesson_id == target.lesson_id
        )
        result = connection.execute(stmt)
        max_order = result.scalar()
        target.order_index = (max_order or 0) + 1

