from datetime import UTC, datetime
import uuid
from sqlalchemy import DateTime, String, Integer, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class UserRefreshToken(Base):
    __tablename__ = "user_refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token: Mapped[str] = mapped_column(String(500), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), init=False)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    # Indexes for performance
    __table_args__ = (
        Index('idx_user_refresh_tokens_user_id', 'user_id'),
        Index('idx_user_refresh_tokens_expires_at', 'expires_at'),
    )











