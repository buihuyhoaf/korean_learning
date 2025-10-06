from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class ProgressBase(BaseModel):
    user_id: Annotated[int, Field(ge=1, examples=[1])]
    lesson_id: Annotated[int, Field(ge=1, examples=[1])]
    score: Annotated[float, Field(ge=0.0, le=100.0, examples=[85.5])]
    completed: Annotated[bool, Field(default=False)]


class Progress(ProgressBase):
    id: int
    updated_at: datetime


class ProgressRead(ProgressBase):
    id: int
    updated_at: datetime


class ProgressCreate(ProgressBase):
    model_config = ConfigDict(extra="forbid")


class ProgressUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: Annotated[int | None, Field(ge=1, default=None)]
    lesson_id: Annotated[int | None, Field(ge=1, default=None)]
    score: Annotated[float | None, Field(ge=0.0, le=100.0, default=None)]
    completed: Annotated[bool | None, Field(default=None)]


class ProgressUpdateInternal(ProgressUpdate):
    updated_at: datetime


