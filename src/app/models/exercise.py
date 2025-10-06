from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class ListeningExercise(Base):
    __tablename__ = "listening_exercises"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("lessons.id"), nullable=False)
    audio_url: Mapped[str] = mapped_column(String(500))
    transcript: Mapped[str] = mapped_column(Text)
    description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    lesson = relationship("Lesson", back_populates="listening_exercises")


class SpeakingExercise(Base):
    __tablename__ = "speaking_exercises"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("lessons.id"), nullable=False)
    prompt: Mapped[str] = mapped_column(Text)
    sample_answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    lesson = relationship("Lesson", back_populates="speaking_exercises")


class WritingExercise(Base):
    __tablename__ = "writing_exercises"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("lessons.id"), nullable=False)
    prompt: Mapped[str] = mapped_column(Text)
    sample_answer: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    lesson = relationship("Lesson", back_populates="writing_exercises")
