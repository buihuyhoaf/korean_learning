"""
Question Sentence Order Model

Stores the correct sequence of sentences/words for sentence ordering questions.
"""
from typing import Any

from sqlalchemy import Integer, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class QuestionSentenceOrder(Base):
    """
    Correct sequence for sentence ordering questions.
    
    Attributes:
        id: Primary key
        question_id: Foreign key to questions table (one-to-one relationship)
        correct_sequence: JSONB array of strings in the correct order
                        Example: ["안녕하세요", "저는", "한국어를", "배우고", "있습니다"]
    """
    __tablename__ = "question_sentence_order"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True, init=False)
    question_id: Mapped[int] = mapped_column(
        Integer, 
        ForeignKey("questions.id", ondelete="CASCADE"), 
        nullable=False, 
        unique=True,
        index=True
    )
    correct_sequence: Mapped[list[str]] = mapped_column(JSONB, nullable=False)  # JSON array of strings

    # Relationships
    question = relationship("Question", back_populates="sentence_order", uselist=False)

