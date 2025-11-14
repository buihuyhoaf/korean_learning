from datetime import UTC, datetime, date
import uuid

from sqlalchemy import DateTime, String, Integer, ForeignKey, UniqueConstraint, Boolean, Date
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


class WeeklyLeaderboard(Base):
    __tablename__ = "weekly_leaderboard"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, default=None)
    is_dummy: Mapped[bool] = mapped_column(Boolean, nullable=False)
    dummy_id: Mapped[str | None] = mapped_column(String(20), nullable=True, default=None)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True, default=None)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank_previous: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    xp_week_start: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), init=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    user = relationship("User", back_populates="weekly_leaderboard")

    __table_args__ = (
        UniqueConstraint('week_start', 'user_id', 'is_dummy', 'dummy_id', name='unique_weekly_entry'),
    )


