# src/app/models/course.py
from sqlalchemy import Column, Integer, String
from src.app import Base

class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, nullable=False)
    description = Column(String)
    lessons = relationship("Lesson", back_populates="course")