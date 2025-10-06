from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class QuizBase(BaseModel):
    lesson_id: Annotated[int, Field(gt=0, examples=[1])]
    title: Annotated[str, Field(min_length=1, max_length=200, examples=["Basic Greetings Quiz"])]
    question: Annotated[str, Field(min_length=1, examples=["What does '안녕하세요' mean?"])]
    answer: Annotated[str, Field(min_length=1, examples=["Hello"])]


class Quiz(QuizBase):
    id: int
    created_at: datetime


class QuizRead(QuizBase):
    id: int
    created_at: datetime


class QuizCreate(QuizBase):
    model_config = ConfigDict(extra="forbid")


class QuizUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    lesson_id: Annotated[int | None, Field(gt=0, default=None)]
    title: Annotated[str | None, Field(min_length=1, max_length=200, default=None)]
    question: Annotated[str | None, Field(min_length=1, default=None)]
    answer: Annotated[str | None, Field(min_length=1, default=None)]


class QuizUpdateInternal(QuizUpdate):
    updated_at: datetime


