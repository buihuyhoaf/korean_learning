from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class UserFinalQuizAttemptBase(BaseModel):
    """Base schema for UserFinalQuizAttempt"""
    user_id: int = Field(..., gt=0, description="ID of the user")
    final_quiz_id: int = Field(..., gt=0, description="ID of the final quiz")
    score: float = Field(0.0, ge=0.0, le=100.0, description="Score achieved (0-100)")
    exp_earned: int = Field(0, ge=0, description="Experience points earned")


class UserFinalQuizAttemptCreate(BaseModel):
    """Schema for creating a new final quiz attempt"""
    final_quiz_id: int = Field(..., gt=0, description="ID of the final quiz to attempt")
    
    model_config = ConfigDict(extra="forbid")


class UserFinalQuizAttemptUpdate(BaseModel):
    """Schema for updating a final quiz attempt"""
    score: Optional[float] = Field(None, ge=0.0, le=100.0, description="Score achieved (0-100)")
    exp_earned: Optional[int] = Field(None, ge=0, description="Experience points earned")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    model_config = ConfigDict(extra="forbid")


class UserFinalQuizAttemptComplete(BaseModel):
    """Schema for completing a final quiz attempt"""
    score: float = Field(..., ge=0.0, le=100.0, description="Final score achieved (0-100)")
    exp_earned: int = Field(..., ge=0, description="Experience points earned")
    
    model_config = ConfigDict(extra="forbid")


class UserFinalQuizAttemptRead(UserFinalQuizAttemptBase):
    """Schema for reading final quiz attempt data"""
    id: int = Field(..., description="Attempt ID")
    started_at: datetime = Field(..., description="Start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class UserFinalQuizAttemptWithDetails(UserFinalQuizAttemptRead):
    """Schema for reading final quiz attempt with additional details"""
    final_quiz_title: Optional[str] = Field(None, description="Title of the final quiz")
    final_quiz_description: Optional[str] = Field(None, description="Description of the final quiz")
    unit_title: Optional[str] = Field(None, description="Title of the unit")
    course_title: Optional[str] = Field(None, description="Title of the course")


class UserFinalQuizAttemptListResponse(BaseModel):
    """Response schema for listing final quiz attempts"""
    attempts: list[UserFinalQuizAttemptWithDetails] = Field(..., description="List of attempts")
    total: int = Field(..., description="Total number of attempts")
    user_id: int = Field(..., description="User ID")


class UserFinalQuizAttemptStatsResponse(BaseModel):
    """Response schema for final quiz attempt statistics"""
    user_id: int = Field(..., description="User ID")
    total_attempts: int = Field(..., description="Total number of attempts")
    completed_attempts: int = Field(..., description="Number of completed attempts")
    average_score: Optional[float] = Field(None, description="Average score across all attempts")
    total_exp_earned: int = Field(..., description="Total experience points earned")
    best_score: Optional[float] = Field(None, description="Best score achieved")
    latest_attempt: Optional[datetime] = Field(None, description="Latest attempt timestamp")