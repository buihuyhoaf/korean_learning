from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class FinalQuiz(Base):
    """Final quiz for units - renamed from Quiz after manual schema changes"""
    __tablename__ = "final_quizzes"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    unit_id: Mapped[int] = mapped_column(Integer, ForeignKey("units.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(50))  # vocabulary, listening, speaking, writing
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    unit = relationship("Unit", back_populates="final_quiz")
    questions = relationship("Question", back_populates="quiz")
    final_quiz_attempts = relationship("UserFinalQuizAttempt", back_populates="final_quiz")  # New relationship
