from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Integer, Text, ForeignKey, Boolean, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class EntryTest(Base):
    __tablename__ = "entry_tests"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    related_course_id: Mapped[int] = mapped_column(Integer, ForeignKey("courses.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    related_course = relationship("Course", back_populates="entry_tests")
    questions = relationship("EntryTestQuestion", back_populates="entry_test")
    user_results = relationship("UserEntryTestResult", back_populates="entry_test")


class EntryTestQuestion(Base):
    __tablename__ = "entry_test_questions"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    entry_test_id: Mapped[int] = mapped_column(Integer, ForeignKey("entry_tests.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text)
    audio_url: Mapped[str] = mapped_column(String(500), nullable=True)
    image_url: Mapped[str] = mapped_column(String(500), nullable=True)
    correct_answer: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    entry_test = relationship("EntryTest", back_populates="questions")
    options = relationship("EntryTestQuestionOption", back_populates="question")


class EntryTestQuestionOption(Base):
    __tablename__ = "entry_test_question_options"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("entry_test_questions.id"), nullable=False)
    option_text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    question = relationship("EntryTestQuestion", back_populates="options")


class UserEntryTestResult(Base):
    __tablename__ = "user_entry_test_results"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    entry_test_id: Mapped[int] = mapped_column(Integer, ForeignKey("entry_tests.id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    recommended_course_id: Mapped[int] = mapped_column(Integer, ForeignKey("courses.id"), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    user = relationship("User", back_populates="entry_test_results")
    entry_test = relationship("EntryTest", back_populates="user_results")
    recommended_course = relationship("Course", foreign_keys=[recommended_course_id])
