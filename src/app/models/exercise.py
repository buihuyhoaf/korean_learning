from datetime import UTC, datetime
import uuid
from enum import Enum

from sqlalchemy import DateTime, String, Integer, Text, ForeignKey, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class ExerciseType(str, Enum):
    """Enum for exercise types"""
    LISTENING = "listening"
    SPEAKING = "speaking"
    WRITING = "writing"
    PRONUNCIATION = "pronunciation"


class Exercise(Base):
    """Unified exercises table for listening, speaking, writing"""
    __tablename__ = "exercises"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    lesson_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=False)
    type: Mapped[ExerciseType] = mapped_column(String(50), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    text_to_speak: Mapped[str | None] = mapped_column(Text, nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    sample_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    lesson = relationship("Lesson", back_populates="exercises")
    questions = relationship("ExerciseQuestion", back_populates="exercise", cascade="all, delete-orphan", lazy="selectin")

    # Indexes for better performance
    __table_args__ = (
        Index('ix_exercises_lesson_id', 'lesson_id'),
        Index('ix_exercises_type', 'type'),
        Index('ix_exercises_lesson_type', 'lesson_id', 'type'),
        Index('ix_exercises_order', 'lesson_id', 'order_index'),
    )


# Legacy exercise models for backward compatibility
# These models reference tables that may have been dropped, so they're commented out
# Uncomment if you need to maintain backward compatibility with old tables

# class ListeningExercise(Base):
#     __tablename__ = "listening_exercises"
# 
#     id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
#     lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("lessons.id"), nullable=False)
#     audio_url: Mapped[str] = mapped_column(String(500))
#     transcript: Mapped[str] = mapped_column(Text)
#     description: Mapped[str] = mapped_column(Text)
#     created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
# 
#     # Relationships
#     lesson = relationship("Lesson", back_populates="listening_exercises")
# 
# 
# class SpeakingExercise(Base):
#     __tablename__ = "speaking_exercises"
# 
#     id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
#     lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("lessons.id"), nullable=False)
#     prompt: Mapped[str] = mapped_column(Text)
#     sample_answer: Mapped[str] = mapped_column(Text)
#     created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
# 
#     # Relationships
#     lesson = relationship("Lesson", back_populates="speaking_exercises")
# 
# 
# class WritingExercise(Base):
#     __tablename__ = "writing_exercises"
# 
#     id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
#     lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("lessons.id"), nullable=False)
#     prompt: Mapped[str] = mapped_column(Text)
#     sample_answer: Mapped[str] = mapped_column(Text)
#     created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
# 
#     # Relationships
#     lesson = relationship("Lesson", back_populates="writing_exercises")


class ExerciseQuestion(Base):
    """Questions belonging to an exercise"""
    __tablename__ = "exercise_questions"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    exercise_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exercises.id"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    
    # Relationships
    exercise = relationship("Exercise", back_populates="questions")
    options = relationship("ExerciseQuestionOption", back_populates="question", cascade="all, delete-orphan", lazy="selectin")
    
    # Indexes
    __table_args__ = (
        Index('ix_exercise_questions_exercise_id', 'exercise_id'),
        Index('ix_exercise_questions_order', 'exercise_id', 'order_index'),
    )


class ExerciseQuestionOption(Base):
    """Options for exercise questions"""
    __tablename__ = "exercise_question_options"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("exercise_questions.id"), nullable=False)
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    
    # Relationships
    question = relationship("ExerciseQuestion", back_populates="options")
    
    # Indexes
    __table_args__ = (
        Index('ix_exercise_question_options_question_id', 'question_id'),
        Index('ix_exercise_question_options_order', 'question_id', 'order_index'),
    )