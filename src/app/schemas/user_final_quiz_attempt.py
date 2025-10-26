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
    started_at: datetime = Field(..., description="When the attempt was started")
    completed_at: Optional[datetime] = Field(None, description="When the attempt was completed")
    is_completed: bool = Field(..., description="Whether the attempt is completed")
    
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
    completed_count: int = Field(..., description="Number of completed attempts")
    average_score: Optional[float] = Field(None, description="Average score across completed attempts")


class FinalQuizAttemptStartResponse(BaseModel):
    """Response schema for starting a final quiz attempt"""
    attempt_id: int = Field(..., description="ID of the created attempt")
    final_quiz_id: int = Field(..., description="ID of the final quiz")
    started_at: datetime = Field(..., description="When the attempt was started")
    message: str = Field(..., description="Success message")


class FinalQuizAttemptCompleteResponse(BaseModel):
    """Response schema for completing a final quiz attempt"""
    attempt_id: int = Field(..., description="ID of the completed attempt")
    score: float = Field(..., description="Final score achieved")
    exp_earned: int = Field(..., description="Experience points earned")
    completed_at: datetime = Field(..., description="When the attempt was completed")
    message: str = Field(..., description="Success message")
