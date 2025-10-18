from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, Boolean, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class UserCourseProgress(Base):
    __tablename__ = "user_course_progress"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey("courses.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    user = relationship("User", back_populates="course_progress")
    course = relationship("Course", back_populates="user_progress")


class UserUnitProgress(Base):
    __tablename__ = "user_unit_progress"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    unit_id: Mapped[int] = mapped_column(Integer, ForeignKey("units.id"), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    user = relationship("User", back_populates="unit_progress")
    unit = relationship("Unit", back_populates="user_progress")


class UserLessonProgress(Base):
    __tablename__ = "user_lesson_progress"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    lesson_id: Mapped[int] = mapped_column(Integer, ForeignKey("lessons.id"), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    progress_percent: Mapped[float] = mapped_column(Float, default=0.0)

    # Relationships
    user = relationship("User", back_populates="lesson_progress")
    lesson = relationship("Lesson", back_populates="user_progress")


class UserQuizAttempt(Base):
    __tablename__ = "user_quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    quiz_id: Mapped[int] = mapped_column(Integer, ForeignKey("quizzes.id"), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    exp_earned: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    user = relationship("User", back_populates="quiz_attempts")
    quiz = relationship("Quiz", back_populates="user_attempts")
    question_attempts = relationship("UserQuestionAttempt", back_populates="quiz_attempt")


class UserQuestionAttempt(Base):
    __tablename__ = "user_question_attempts"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    user_quiz_attempt_id: Mapped[int] = mapped_column(Integer, ForeignKey("user_quiz_attempts.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    user_answer: Mapped[str] = mapped_column(String(1000))
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    quiz_attempt = relationship("UserQuizAttempt", back_populates="question_attempts")
    question = relationship("Question", back_populates="user_attempts")


class UserQuestionError(Base):
    __tablename__ = "user_question_errors"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    last_wrong_answer: Mapped[str] = mapped_column(String(1000), nullable=True)
    last_wrong_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="question_errors")
    question = relationship("Question", back_populates="user_errors")
