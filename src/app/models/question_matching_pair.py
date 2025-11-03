"""
Question Matching Pair Model

Stores left-right pairs for matching questions (e.g., match Korean word to English translation).
"""
from typing import Any
import uuid

from sqlalchemy import Integer, Text, ForeignKey, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class QuestionMatchingPair(Base):
    """
    Left-right pairs for matching questions.
    
    Attributes:
        id: Primary key
        question_id: Foreign key to questions table
        left_text: Text for the left side of the pair
        left_media: JSONB object storing media for left side (image, audio URLs)
        right_text: Text for the right side of the pair
        right_media: JSONB object storing media for right side (image, audio URLs)
        sort_order: Ordering of pairs within the question
    """
    __tablename__ = "question_matching_pairs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    question_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("questions.id", ondelete="CASCADE"), nullable=False, index=True)
    left_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    left_media: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)  # {"image": "...", "audio": "..."}
    right_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    right_media: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)  # {"image": "...", "audio": "..."}
    sort_order: Mapped[int] = mapped_column(SmallInteger, default=0)

    # Relationships
    question = relationship("Question", back_populates="matching_pairs")

