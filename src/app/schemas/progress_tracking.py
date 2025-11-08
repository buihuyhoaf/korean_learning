from datetime import date
from typing import List
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DateRange(BaseModel):
    start: date
    end: date


class ExpPoint(BaseModel):
    date: date
    exp_delta: int
    cumulative_exp: int


class UserExpSeries(BaseModel):
    user_id: UUID
    username: str
    starting_exp: int
    total_exp: int
    series: List[ExpPoint]


class ExpSeriesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    date_range: DateRange
    series: List[UserExpSeries]


