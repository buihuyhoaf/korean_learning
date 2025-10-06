from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class UnitBase(BaseModel):
    course_id: Annotated[int, Field(ge=1, examples=[1])]
    title: Annotated[str, Field(min_length=1, max_length=200, examples=["Unit 1: Greetings"])]
    description: Annotated[str, Field(min_length=1, examples=["Basic Korean greetings and introductions"])]
    order_index: Annotated[int, Field(default=0, ge=0)]


class Unit(UnitBase):
    id: int
    created_at: datetime


class UnitRead(UnitBase):
    id: int
    created_at: datetime


class UnitCreate(UnitBase):
    model_config = ConfigDict(extra="forbid")


class UnitUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    course_id: Annotated[int | None, Field(ge=1, default=None)]
    title: Annotated[str | None, Field(min_length=1, max_length=200, default=None)]
    description: Annotated[str | None, Field(min_length=1, default=None)]
    order_index: Annotated[int | None, Field(ge=0, default=None)]


class UnitUpdateInternal(UnitUpdate):
    updated_at: datetime


