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
    audio_url: Optional[str] = Field(None, max_length=500, description="Audio file URL (preferred if available)")
    text_to_speak: Optional[str] = Field(None, description="Text for Text-to-Speech (used when audio_url is not available)")
    transcript: Optional[str] = Field(None, description="Audio transcript")
    prompt: Optional[str] = Field(None, description="Exercise prompt")
    sample_answer: Optional[str] = Field(None, description="Sample answer")
    order_index: int = Field(0, ge=0, description="Order index within lesson")


# Schemas for ExerciseQuestion and ExerciseQuestionOption (must be defined before ExerciseCreate)

class ExerciseQuestionOptionBase(BaseModel):
    """Base schema for ExerciseQuestionOption"""
    option_text: str = Field(..., description="Option text")
    is_correct: bool = Field(False, description="Is this option correct?")
    order_index: int = Field(0, ge=0, description="Order index")


class ExerciseQuestionOptionCreate(ExerciseQuestionOptionBase):
    """Schema for creating an exercise question option"""
    pass


class ExerciseQuestionOptionResponse(ExerciseQuestionOptionBase):
    """Schema for reading exercise question option data"""
    id: int = Field(..., description="Option ID")
    question_id: int = Field(..., description="Question ID")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class ExerciseQuestionBase(BaseModel):
    """Base schema for ExerciseQuestion"""
    question_text: str = Field(..., description="Question text")
    explanation: Optional[str] = Field(None, description="Explanation for the answer")
    order_index: int = Field(0, ge=0, description="Order index")


class ExerciseQuestionCreate(ExerciseQuestionBase):
    """Schema for creating an exercise question"""
    options: List[ExerciseQuestionOptionCreate] = Field(default_factory=list, description="Multiple choice options")


class ExerciseQuestionResponse(ExerciseQuestionBase):
    """Schema for reading exercise question data"""
    id: int = Field(..., description="Question ID")
    exercise_id: int = Field(..., description="Exercise ID")
    options: List[ExerciseQuestionOptionResponse] = Field(default_factory=list, description="Multiple choice options")
    created_at: datetime = Field(..., description="Creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class ExerciseCreate(ExerciseBase):
    """Schema for creating a new exercise"""
    lesson_id: int = Field(..., gt=0, description="ID of the lesson this exercise belongs to")
    questions: List[ExerciseQuestionCreate] = Field(default_factory=list, description="Questions for this exercise")
    
    model_config = ConfigDict(extra="forbid")


class ExerciseUpdate(BaseModel):
    """Schema for updating an exercise"""
    type: Optional[ExerciseType] = Field(None, description="Type of exercise")
    title: Optional[str] = Field(None, max_length=200, description="Exercise title")
    content: Optional[str] = Field(None, description="Exercise content")
    audio_url: Optional[str] = Field(None, max_length=500, description="Audio file URL (preferred if available)")
    text_to_speak: Optional[str] = Field(None, description="Text for Text-to-Speech (used when audio_url is not available)")
    transcript: Optional[str] = Field(None, description="Audio transcript")
    prompt: Optional[str] = Field(None, description="Exercise prompt")
    sample_answer: Optional[str] = Field(None, description="Sample answer")
    order_index: Optional[int] = Field(None, ge=0, description="Order index within lesson")
    questions: Optional[List[ExerciseQuestionCreate]] = Field(None, description="Questions for this exercise (full replace)")
    
    model_config = ConfigDict(extra="forbid")


class ExerciseRead(ExerciseBase):
    """Schema for reading exercise data"""
    id: int = Field(..., description="Exercise ID")
    lesson_id: int = Field(..., description="Lesson ID")
    questions: List[ExerciseQuestionResponse] = Field(default_factory=list, description="Questions for this exercise")
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
