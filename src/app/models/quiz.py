from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Integer, Text, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


# OLD Quiz model - DEPRECATED after manual schema changes
# Use FinalQuiz model instead
# class Quiz(Base):
#     __tablename__ = "quizzes"
#     # ... old implementation removed


class QuestionType(Base):
    __tablename__ = "question_types"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text)

    # Relationships
    questions = relationship("Question", back_populates="question_type")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    # New fields added by manual schema changes
    lesson_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("lessons.id"), nullable=True)
    question_type: Mapped[str] = mapped_column(String(50), default="practice")
    # Keep quiz_id for backward compatibility
    quiz_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("final_quizzes.id"), nullable=True)
    question_type_id: Mapped[int] = mapped_column(Integer, ForeignKey("question_types.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text)
    audio_url: Mapped[str] = mapped_column(String(500), nullable=True)
    image_url: Mapped[str] = mapped_column(String(500), nullable=True)
    correct_answer: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    lesson = relationship("Lesson", back_populates="questions")
    quiz = relationship("FinalQuiz", back_populates="questions")  # Updated to FinalQuiz
    question_type = relationship("QuestionType", back_populates="questions")
    options = relationship("QuestionOption", back_populates="question")
    user_attempts = relationship("UserQuestionAttempt", back_populates="question")
    user_errors = relationship("UserQuestionError", back_populates="question")


class QuestionOption(Base):
    __tablename__ = "question_options"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id"), nullable=False)
    option_text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    question = relationship("Question", back_populates="options")
