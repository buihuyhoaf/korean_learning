from datetime import UTC, datetime
import uuid

from sqlalchemy import DateTime, String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class Friend(Base):
    __tablename__ = "friends"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    friend_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending, accepted, blocked
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    user = relationship("User", back_populates="friends", foreign_keys=[user_id])
    friend = relationship("User", back_populates="friend_of", foreign_keys=[friend_user_id])

    # Unique constraint
    __table_args__ = (UniqueConstraint('user_id', 'friend_user_id'),)


class Leaderboard(Base):
    __tablename__ = "leaderboard"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    season: Mapped[str] = mapped_column(String(50))
    rank: Mapped[int] = mapped_column(Integer)
    exp: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC))

    # Relationships
    user = relationship("User", back_populates="leaderboard")
