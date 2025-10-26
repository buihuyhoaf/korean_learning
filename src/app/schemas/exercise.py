from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
from enum import Enum


class ExerciseType(str, Enum):
    """Exercise types enum"""
    LISTENING = "listening"
    SPEAKING = "speaking"
    WRITING = "writing"
    PRONUNCIATION = "pronunciation"


class ExerciseBase(BaseModel):
    """Base schema for Exercise"""
    type: ExerciseType = Field(..., description="Type of exercise")
    title: Optional[str] = Field(None, max_length=200, description="Exercise title")
    content: Optional[str] = Field(None, description="Exercise content")
    audio_url: Optional[str] = Field(None, max_length=500, description="Audio file URL")
    transcript: Optional[str] = Field(None, description="Audio transcript")
    prompt: Optional[str] = Field(None, description="Exercise prompt")
    sample_answer: Optional[str] = Field(None, description="Sample answer")
    order_index: int = Field(0, ge=0, description="Order index within lesson")


class ExerciseCreate(ExerciseBase):
    """Schema for creating a new exercise"""
    lesson_id: int = Field(..., gt=0, description="ID of the lesson this exercise belongs to")
    
    model_config = ConfigDict(extra="forbid")


class ExerciseUpdate(BaseModel):
    """Schema for updating an exercise"""
    type: Optional[ExerciseType] = Field(None, description="Type of exercise")
    title: Optional[str] = Field(None, max_length=200, description="Exercise title")
    content: Optional[str] = Field(None, description="Exercise content")
    audio_url: Optional[str] = Field(None, max_length=500, description="Audio file URL")
    transcript: Optional[str] = Field(None, description="Audio transcript")
    prompt: Optional[str] = Field(None, description="Exercise prompt")
    sample_answer: Optional[str] = Field(None, description="Sample answer")
    order_index: Optional[int] = Field(None, ge=0, description="Order index within lesson")
    
    model_config = ConfigDict(extra="forbid")


class ExerciseRead(ExerciseBase):
    """Schema for reading exercise data"""
    id: int = Field(..., description="Exercise ID")
    lesson_id: int = Field(..., description="Lesson ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class ExerciseListResponse(BaseModel):
    """Response schema for listing exercises"""
    exercises: List[ExerciseRead] = Field(..., description="List of exercises")
    total: int = Field(..., description="Total number of exercises")
    lesson_id: int = Field(..., description="Lesson ID")
    exercise_type: Optional[ExerciseType] = Field(None, description="Filtered exercise type")


class ExerciseStatsResponse(BaseModel):
    """Response schema for exercise statistics"""
    lesson_id: int = Field(..., description="Lesson ID")
    total_exercises: int = Field(..., description="Total number of exercises")
    listening_count: int = Field(..., description="Number of listening exercises")
    speaking_count: int = Field(..., description="Number of speaking exercises")
    writing_count: int = Field(..., description="Number of writing exercises")
    pronunciation_count: int = Field(..., description="Number of pronunciation exercises")
