from datetime import UTC, datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, Float, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class UserFinalQuizAttempt(Base):
    """User attempts for final quizzes"""
    __tablename__ = "user_final_quiz_attempts"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    final_quiz_id: Mapped[int] = mapped_column(Integer, ForeignKey("final_quizzes.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, default=None)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    exp_earned: Mapped[int] = mapped_column(Integer, default=0)

    # Relationships
    user = relationship("User", back_populates="final_quiz_attempts")
    final_quiz = relationship("FinalQuiz", back_populates="user_attempts")

    # Indexes for better performance
    __table_args__ = (
        Index('ix_user_final_quiz_attempts_user_id', 'user_id'),
        Index('ix_user_final_quiz_attempts_final_quiz_id', 'final_quiz_id'),
        Index('ix_user_final_quiz_attempts_user_quiz', 'user_id', 'final_quiz_id'),
        Index('ix_user_final_quiz_attempts_started_at', 'started_at'),
        Index('ix_user_final_quiz_attempts_completed_at', 'completed_at'),
    )
