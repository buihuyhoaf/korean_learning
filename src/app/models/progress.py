from datetime import UTC, datetime
import uuid

from sqlalchemy import DateTime, Integer, Boolean, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class UserCourseProgress(Base):
    __tablename__ = "user_course_progress"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="course_progress")
    course = relationship("Course", back_populates="user_progress")


class UserUnitProgress(Base):
    __tablename__ = "user_unit_progress"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    unit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("units.id"), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    user = relationship("User", back_populates="unit_progress")
    unit = relationship("Unit", back_populates="user_progress")


class UserLessonProgress(Base):
    __tablename__ = "user_lesson_progress"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    lesson_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("lessons.id"), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    completed_questions_count: Mapped[int] = mapped_column(Integer, default=0)
    completed_exercises_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="lesson_progress")
    lesson = relationship("Lesson", back_populates="user_progress")


class UserQuestionError(Base):
    __tablename__ = "user_question_errors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("questions.id"), nullable=False)
    last_wrong_answer: Mapped[str] = mapped_column(String(1000), nullable=True)
    last_wrong_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="question_errors")
    question = relationship("Question", back_populates="user_errors")
