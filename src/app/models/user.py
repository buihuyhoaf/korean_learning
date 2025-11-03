from datetime import UTC, datetime
from uuid6 import uuid7
import uuid as uuid_pkg

from sqlalchemy import DateTime, String, Integer, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True, init=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    password: Mapped[str] = mapped_column(String(255))
    picture: Mapped[str | None] = mapped_column(String(500), nullable=True)  # Google profile picture URL
    role: Mapped[str] = mapped_column(String(20), default="student")  # admin, student
    exp: Mapped[int] = mapped_column(Integer, default=0)  # Tổng điểm EXP của user
    streak_days: Mapped[int] = mapped_column(Integer, default=0)  # Số ngày học liên tiếp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), init=False)
    tier_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("tier.id"), nullable=True, default=None)
    current_course_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("courses.id"), nullable=True, default=None)
    entry_test_score: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    has_completed_entry_test: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    course_progress = relationship("UserCourseProgress", back_populates="user")
    current_course = relationship("Course", foreign_keys=[current_course_id])
    entry_test_results = relationship("UserEntryTestResult", back_populates="user")
    unit_progress = relationship("UserUnitProgress", back_populates="user")
    lesson_progress = relationship("UserLessonProgress", back_populates="user")
    question_errors = relationship("UserQuestionError", back_populates="user")
    exp_logs = relationship("UserExpLog", back_populates="user")
    badges = relationship("UserBadge", back_populates="user")
    daily_goals = relationship("DailyGoal", back_populates="user")
    friends = relationship("Friend", back_populates="user", foreign_keys="Friend.user_id")
    friend_of = relationship("Friend", back_populates="friend", foreign_keys="Friend.friend_user_id")
    leaderboard = relationship("Leaderboard", back_populates="user")
    ai_logs = relationship("AiLog", back_populates="user")
    notifications = relationship("Notification", back_populates="user")
    refresh_tokens = relationship("UserRefreshToken", back_populates="user", cascade="all, delete-orphan")
    answers = relationship("UserAnswer", back_populates="user", cascade="all, delete-orphan")