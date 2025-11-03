"""
Gamification Schemas

Pydantic schemas for gamification models: badges, user badges, daily goals, and exp logs.
"""
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Badge Schemas
# ============================================================================

class BadgeBase(BaseModel):
    """Base schema for Badge"""
    name: str = Field(..., max_length=100, description="Badge name")
    description: str = Field(..., description="Badge description")
    icon_url: Optional[str] = Field(None, max_length=500, description="Badge icon URL")


class BadgeCreate(BadgeBase):
    """Schema for creating a badge"""
    model_config = ConfigDict(extra="forbid")


class BadgeUpdate(BaseModel):
    """Schema for updating a badge"""
    name: Optional[str] = Field(None, max_length=100, description="Badge name")
    description: Optional[str] = Field(None, description="Badge description")
    icon_url: Optional[str] = Field(None, max_length=500, description="Badge icon URL")
    model_config = ConfigDict(extra="forbid")


class BadgeResponse(BadgeBase):
    """Schema for reading badge data"""
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# User Badge Schemas
# ============================================================================

class UserBadgeBase(BaseModel):
    """Base schema for UserBadge"""
    user_id: int = Field(..., description="User ID")
    badge_id: int = Field(..., description="Badge ID")


class UserBadgeCreate(UserBadgeBase):
    """Schema for creating a user badge"""
    model_config = ConfigDict(extra="forbid")


class UserBadgeUpdate(BaseModel):
    """Schema for updating a user badge (usually not needed, read-only)"""
    model_config = ConfigDict(extra="forbid")


class UserBadgeResponse(UserBadgeBase):
    """Schema for reading user badge data"""
    id: int
    earned_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Daily Goal Schemas
# ============================================================================

class DailyGoalBase(BaseModel):
    """Base schema for DailyGoal"""
    user_id: int = Field(..., description="User ID")
    target_exp: int = Field(default=100, description="Target EXP for the day")
    target_lessons: int = Field(default=1, description="Target lessons for the day")
    is_completed: bool = Field(default=False, description="Whether the goal is completed")


class DailyGoalCreate(DailyGoalBase):
    """Schema for creating a daily goal"""
    model_config = ConfigDict(extra="forbid")


class DailyGoalUpdate(BaseModel):
    """Schema for updating a daily goal"""
    target_exp: Optional[int] = Field(None, description="Target EXP for the day")
    target_lessons: Optional[int] = Field(None, description="Target lessons for the day")
    is_completed: Optional[bool] = Field(None, description="Whether the goal is completed")
    model_config = ConfigDict(extra="forbid")


class DailyGoalResponse(DailyGoalBase):
    """Schema for reading daily goal data"""
    id: int
    created_at: date
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# User Exp Log Schemas
# ============================================================================

class UserExpLogBase(BaseModel):
    """Base schema for UserExpLog"""
    user_id: int = Field(..., description="User ID")
    source: str = Field(..., max_length=100, description="Source of EXP (quiz, daily_goal, etc.)")
    amount: int = Field(..., description="Amount of EXP earned")


class UserExpLogCreate(UserExpLogBase):
    """Schema for creating a user exp log entry"""
    model_config = ConfigDict(extra="forbid")


class UserExpLogUpdate(BaseModel):
    """Schema for updating a user exp log entry (usually not needed, read-only)"""
    source: Optional[str] = Field(None, max_length=100, description="Source of EXP")
    amount: Optional[int] = Field(None, description="Amount of EXP earned")
    model_config = ConfigDict(extra="forbid")


class UserExpLogResponse(UserExpLogBase):
    """Schema for reading user exp log data"""
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

