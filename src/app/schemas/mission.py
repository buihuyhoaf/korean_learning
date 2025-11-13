"""
Mission Schemas

Pydantic schemas for daily missions.
"""
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class MissionResponse(BaseModel):
    """Schema for mission response"""
    mission_id: str = Field(..., description="Mission ID (m1, m2, m3)")
    type: str = Field(..., description="Mission type (lesson, speaking, listening)")
    target: int = Field(..., description="Target count to complete mission")
    progress: int = Field(..., description="Current progress")
    is_completed: bool = Field(..., description="Whether mission is completed")
    model_config = ConfigDict(from_attributes=True)


class TodayMissionsResponse(BaseModel):
    """Schema for today's missions response"""
    missions: list[MissionResponse] = Field(..., description="List of today's missions")


class ActivityRequest(BaseModel):
    """Schema for activity tracking request"""
    type: str = Field(..., description="Activity type (lesson, speaking, listening)")
    model_config = ConfigDict(extra="forbid")


class ActivityResponse(BaseModel):
    """Schema for activity tracking response"""
    mission_completed: bool = Field(..., description="Whether a mission was completed")
    mission_id: Optional[str] = Field(None, description="Mission ID if completed")
    expires_at: Optional[int] = Field(None, description="Expires timestamp in milliseconds if mission completed")
    model_config = ConfigDict(extra="forbid")


class ExpRequest(BaseModel):
    """Schema for adding EXP request"""
    exp: int = Field(..., description="EXP amount (already multiplied by client)")
    model_config = ConfigDict(extra="forbid")


class ExpResponse(BaseModel):
    """Schema for adding EXP response"""
    message: str = Field(..., description="Response message")
    total_exp: int = Field(..., description="Total EXP after adding")
    model_config = ConfigDict(extra="forbid")

