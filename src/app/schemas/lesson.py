from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class LessonBase(BaseModel):
    course_id: Annotated[int, Field(gt=0, examples=[1])]
    title: Annotated[str, Field(min_length=1, max_length=200, examples=["Greetings"])]
    description: Annotated[str, Field(min_length=1, examples=["Learn how to greet people in Korean"])]


class Lesson(LessonBase):
    id: int
    created_at: datetime


class LessonRead(LessonBase):
    id: int
    created_at: datetime


class LessonCreate(LessonBase):
    model_config = ConfigDict(extra="forbid")


class LessonUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    course_id: Annotated[int | None, Field(gt=0, default=None)]
    title: Annotated[str | None, Field(min_length=1, max_length=200, default=None)]
    description: Annotated[str | None, Field(min_length=1, default=None)]


class LessonUpdateInternal(LessonUpdate):
    updated_at: datetime


