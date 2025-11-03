from datetime import UTC, datetime
import uuid

from sqlalchemy import DateTime, String, Integer, Text, ForeignKey, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class EntryTest(Base):
    __tablename__ = "entry_tests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    related_course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), init=False)


    # Relationships
    related_course = relationship("Course", back_populates="entry_tests")
    questions = relationship("EntryTestQuestion", back_populates="entry_test")
    user_results = relationship("UserEntryTestResult", back_populates="entry_test")
    score_ranges = relationship("EntryTestResult")


class EntryTestQuestion(Base):
    __tablename__ = "entry_test_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    entry_test_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("entry_tests.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text)
    audio_url: Mapped[str] = mapped_column(String(500), nullable=True)
    image_url: Mapped[str] = mapped_column(String(500), nullable=True)
    correct_answer: Mapped[str] = mapped_column(Text)
    explanation: Mapped[str] = mapped_column(Text, nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), init=False)

    # Relationships
    entry_test = relationship("EntryTest", back_populates="questions")
    options = relationship("EntryTestQuestionOption", back_populates="question")


class EntryTestQuestionOption(Base):
    __tablename__ = "entry_test_question_options"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("entry_test_questions.id"), nullable=False)
    option_text: Mapped[str] = mapped_column(Text)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), init=False)

    # Relationships
    question = relationship("EntryTestQuestion", back_populates="options")


class UserEntryTestResult(Base):
    __tablename__ = "user_entry_test_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    entry_test_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("entry_tests.id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    recommended_course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), init=False)

    # Relationships
    user = relationship("User", back_populates="entry_test_results")
    entry_test = relationship("EntryTest", back_populates="user_results")
    recommended_course = relationship("Course", foreign_keys=[recommended_course_id])


class EntryTestResult(Base):
    """Maps score ranges to recommended courses"""
    __tablename__ = "entry_test_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    entry_test_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("entry_tests.id"), nullable=False)
    min_score: Mapped[float] = mapped_column(Float, nullable=False)
    max_score: Mapped[float] = mapped_column(Float, nullable=False)
    course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), init=False)

    # Relationships
    entry_test = relationship("EntryTest")
    course = relationship("Course", foreign_keys=[course_id])


class UserEntryTestHistory(Base):
    """Read-only history of user entry test attempts"""
    __tablename__ = "user_entry_test_history"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    entry_test_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("entry_tests.id"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    recommended_course_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("courses.id"), nullable=False)
    taken_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), init=False)

    # Relationships
    user = relationship("User")
    entry_test = relationship("EntryTest")
    recommended_course = relationship("Course", foreign_keys=[recommended_course_id])
