from datetime import UTC, datetime
from enum import Enum

from sqlalchemy import DateTime, String, Integer, Text, ForeignKey, Index
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

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("lessons.id"), nullable=False)
    type: Mapped[ExerciseType] = mapped_column(String(50), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    sample_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    lesson = relationship("Lesson", back_populates="exercises")

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