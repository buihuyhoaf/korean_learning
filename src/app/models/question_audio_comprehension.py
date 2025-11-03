"""
Question Audio Comprehension Model

Stores audio-related data for audio comprehension questions.
Includes transcript and TTS configuration.
"""
from typing import Any

from sqlalchemy import Integer, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class QuestionAudioComprehension(Base):
    """
    Audio-related data for audio comprehension questions.
    
    Attributes:
        id: Primary key
        question_id: Foreign key to questions table (one-to-one relationship)
        transcript: Text transcript of the audio
        tts_config: JSONB object storing TTS configuration
                   Example: {"voice": "ko-KR-Standard-A", "speed": 1.0, "pitch": 0.0, "volume_db": 0.0}
    """
    __tablename__ = "question_audio_comprehension"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True, init=False)
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    tts_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Relationships
    question = relationship("Question", back_populates="audio_comprehension", uselist=False)

