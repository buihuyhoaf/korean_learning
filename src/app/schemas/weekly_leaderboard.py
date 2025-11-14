from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from uuid import UUID


class LeaderboardEntry(BaseModel):
    id: UUID
    rank: int
    name: str
    avatar: Optional[str] = None
    country: Optional[str] = None
    xp: int
    is_dummy: bool
    is_current_user: bool = False
    rank_change: Optional[int] = None  # Only for current user
    streak_days: Optional[int] = None  # User's streak days


class WeeklyLeaderboardResponse(BaseModel):
    week_start: date
    entries: list[LeaderboardEntry]
    current_user_rank: Optional[int] = None
    current_user_xp: Optional[int] = None
    rank_change: Optional[int] = None  # Positive = up, Negative = down, None = no change


class WeeklyLeaderboardUpdateRequest(BaseModel):
    exp: int = Field(..., description="New EXP earned")


class WeeklyLeaderboardUpdateResponse(BaseModel):
    message: str
    current_xp: int
    current_rank: int
    rank_change: Optional[int] = None

