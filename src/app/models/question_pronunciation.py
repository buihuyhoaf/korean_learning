"""
Question Pronunciation Model

Stores pronunciation practice data including target phrase, reference audio, and TTS config.
"""
from typing import Any

from sqlalchemy import Integer, Text, String, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class QuestionPronunciation(Base):
    """
    Pronunciation practice question data.
    
    Attributes:
        id: Primary key
        question_id: Foreign key to questions table (one-to-one relationship)
        target_phrase: The phrase the user should pronounce
        reference_audio_url: URL to reference audio file (optional)
        tts_config: JSONB object storing TTS configuration for generating reference audio
    """
    __tablename__ = "question_pronunciation"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True, init=False)
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    target_phrase: Mapped[str] = mapped_column(Text, nullable=False)
    reference_audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    tts_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    question = relationship("Question", back_populates="pronunciation", uselist=False)

