"""
User Answer Model

Stores user answers to questions with flexible JSONB storage for different answer types.
"""
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, Integer, ForeignKey, Boolean, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class UserAnswer(Base):
    """
    User answers to questions.
    
    Uses JSONB to store flexible answer data:
    - Multiple choice: [1, 2, 3] (option IDs)
    - Text: "answer text"
    - Sentence order: ["word1", "word2", "word3"]
    - Matching: {"pair1": {"left": 1, "right": 2}}
    - Audio/pronunciation: {"audio_url": "...", "transcript": "..."}
    
    Attributes:
        id: Primary key
        user_id: Foreign key to users table
        question_id: Foreign key to questions table
        answer: JSONB object/array storing the user's answer
        is_correct: Whether the answer is correct (can be NULL if not yet evaluated)
        score: Score achieved (float, 0.0-1.0)
        answered_at: Timestamp when the answer was submitted
    """
    __tablename__ = "user_answers"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True, init=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    answer: Mapped[Any] = mapped_column(JSONB, nullable=False)  # Flexible JSON data
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    answered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default_factory=lambda: datetime.now(UTC),
        init=False
    )

    # Relationships
    user = relationship("User", back_populates="answers")
    question = relationship("Question", back_populates="user_answers")

