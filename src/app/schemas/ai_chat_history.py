from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field


class AIChatHistoryBase(BaseModel):
    user_id: Annotated[int, Field(ge=1, examples=[1])]
    message: Annotated[str, Field(min_length=1, examples=["How do you say hello in Korean?"])]
    response: Annotated[str, Field(min_length=1, examples=["안녕하세요 (annyeonghaseyo) means hello in Korean."])]


class AIChatHistory(AIChatHistoryBase):
    id: int
    created_at: datetime


class AIChatHistoryRead(AIChatHistoryBase):
    id: int
    created_at: datetime


class AIChatHistoryCreate(AIChatHistoryBase):
    model_config = ConfigDict(extra="forbid")


class AIChatHistoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: Annotated[int | None, Field(ge=1, default=None)]
    message: Annotated[str | None, Field(min_length=1, default=None)]
    response: Annotated[str | None, Field(min_length=1, default=None)]


class AIChatHistoryUpdateInternal(AIChatHistoryUpdate):
    updated_at: datetime


