"""
Question Type Model

Defines the different types of questions supported in the Korean learning app.
Each question type has a unique code, name, and description.
"""
from datetime import UTC, datetime
import uuid

from sqlalchemy import DateTime, String, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class QuestionType(Base):
    """
    Question Type model defining the types of questions available.
    
    Attributes:
        id: Primary key
        code: Unique code for the question type (e.g., 'MULTIPLE_CHOICE', 'AUDIO_COMPREHENSION')
        name: Human-readable name
        description: Detailed description of the question type
        created_at: Timestamp when the question type was created
    """
    __tablename__ = "question_types"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        default_factory=lambda: datetime.now(UTC), 
        init=False
    )

    # Relationships
    questions = relationship(
        "Question", 
        back_populates="question_type_relation",
        cascade="all, delete-orphan"
    )

