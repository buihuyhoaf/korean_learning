from datetime import UTC, datetime
import uuid

from sqlalchemy import DateTime, String, Integer, Text, Float, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class AiLog(Base):
    __tablename__ = "ai_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    exercise_type: Mapped[str] = mapped_column(String(50))  # writing, speaking
    input_url: Mapped[str] = mapped_column(String(500))
    recognized_text: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float)
    result: Mapped[str] = mapped_column(String(20))  # correct, incorrect
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    user = relationship("User", back_populates="ai_logs")
