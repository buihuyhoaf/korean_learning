from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class CourseBase(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=200, examples=["Korean Basics"])]
    description: Annotated[str, Field(min_length=1, examples=["Learn basic Korean vocabulary and grammar"])]


class Course(CourseBase):
    id: int
    order_index: int
    created_at: datetime


class CourseRead(CourseBase):
    id: int
    order_index: int
    created_at: datetime


class CourseCreate(CourseBase):
    model_config = ConfigDict(extra="forbid")
    order_index: Annotated[int, Field(default=0, ge=0)]


class CourseUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    title: Annotated[str | None, Field(min_length=1, max_length=200, default=None)]
    description: Annotated[str | None, Field(min_length=1, default=None)]
    order_index: Annotated[int | None, Field(ge=0, default=None)]


class CourseUpdateInternal(CourseUpdate):
    updated_at: datetime


