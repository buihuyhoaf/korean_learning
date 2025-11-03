"""
Question Option Model

Stores options/choices for multiple choice questions.
Supports text and media (image, audio) for each option.
"""
from typing import Any

from sqlalchemy import Integer, Text, ForeignKey, Boolean, SmallInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class QuestionOption(Base):
    """
    Options/choices for multiple choice questions.
    
    Attributes:
        id: Primary key
        question_id: Foreign key to questions table
        option_text: Text content of the option
        option_media: JSONB object storing media (image, audio URLs)
        is_correct: Whether this option is the correct answer
        sort_order: Ordering of options within the question
    """
    __tablename__ = "question_options"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True, init=False)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    option_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    option_media: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)  # {"image": "...", "audio": "..."}
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)

    # Relationships
    question = relationship("Question", back_populates="options")

