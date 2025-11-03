from datetime import UTC, datetime

from sqlalchemy import DateTime, String, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db.database import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True, init=False)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), init=False)

    # Relationships
    units = relationship("Unit", back_populates="course")
    user_progress = relationship("UserCourseProgress", back_populates="course")
    entry_tests = relationship("EntryTest", back_populates="related_course")


class Unit(Base):
    __tablename__ = "units"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True, init=False)
    course_id: Mapped[int] = mapped_column(Integer, ForeignKey("courses.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), init=False)

    # Relationships
    course = relationship("Course", back_populates="units")
    lessons = relationship("Lesson", back_populates="unit")
    user_progress = relationship("UserUnitProgress", back_populates="unit")


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[int] = mapped_column(Integer, autoincrement=True, primary_key=True, init=False)
    unit_id: Mapped[int] = mapped_column(Integer, ForeignKey("units.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), init=False)

    # Relationships
    unit = relationship("Unit", back_populates="lessons")
    user_progress = relationship("UserLessonProgress", back_populates="lesson")
    # New relationships
    questions = relationship("Question", back_populates="lesson")
    exercises = relationship("Exercise", back_populates="lesson")
