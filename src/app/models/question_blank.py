"""
Question Blank Model

Stores fill-in-the-blank question data including correct answer and case sensitivity setting.
"""
import uuid
from sqlalchemy import Integer, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class QuestionBlank(Base):
    """
    Fill-in-the-blank question data.
    
    Attributes:
        id: Primary key
        question_id: Foreign key to questions table (one-to-one relationship)
        correct_answer: The correct answer for the blank
        case_sensitive: Whether the answer comparison should be case-sensitive
    """
    __tablename__ = "question_blanks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    correct_answer: Mapped[str] = mapped_column(Text, nullable=False)
    case_sensitive: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    question = relationship("Question", back_populates="blanks", uselist=False)

