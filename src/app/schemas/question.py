from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class QuestionTypeBase(BaseModel):
    """Base schema for QuestionType"""
    code: str = Field(..., min_length=1, max_length=50, description="Unique code for question type")
    name: str = Field(..., min_length=1, max_length=100, description="Question type name")
    description: Optional[str] = Field(None, description="Question type description")


class QuestionTypeCreate(QuestionTypeBase):
    """Schema for creating a new question type"""
    model_config = ConfigDict(extra="forbid")


class QuestionTypeUpdate(BaseModel):
    """Schema for updating a question type"""
    code: Optional[str] = Field(None, min_length=1, max_length=50, description="Unique code for question type")
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Question type name")
    description: Optional[str] = Field(None, description="Question type description")
    model_config = ConfigDict(extra="forbid")


class QuestionTypeResponse(QuestionTypeBase):
    """Schema for reading question type data"""
    id: int = Field(..., description="Question type ID")
    model_config = ConfigDict(from_attributes=True)


class QuestionOptionBase(BaseModel):
    option_text: Optional[str] = None
    option_media: Optional[dict] = None
    is_correct: bool = False
    sort_order: int = 0


class QuestionOptionCreate(QuestionOptionBase):
    pass


class QuestionOptionResponse(QuestionOptionBase):
    id: int
    question_id: int
    
    model_config = ConfigDict(from_attributes=True)


class QuestionBase(BaseModel):
    content: str
    audio_url: Optional[str] = None
    image_url: Optional[str] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    order_index: int = 0


class QuestionCreate(QuestionBase):
    lesson_id: Optional[int] = None
    question_type: str = "practice"
    question_type_id: int
    options: List[QuestionOptionCreate] = []

    model_config = ConfigDict(extra="forbid")


class QuestionUpdate(BaseModel):
    lesson_id: Optional[int] = None
    question_type: Optional[str] = None
    content: Optional[str] = None
    audio_url: Optional[str] = None
    image_url: Optional[str] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    order_index: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


class QuestionResponse(QuestionBase):
    id: int
    lesson_id: Optional[int] = None
    question_type: str
    question_type_id: int
    created_at: datetime
    options: List[QuestionOptionResponse] = []

    model_config = ConfigDict(from_attributes=True)


class QuestionSubmitRequest(BaseModel):
    """Request schema for submitting question answers"""
    answer: Optional[str] = None  # For text-based answers
    selected_option_ids: List[int] = []  # For multiple choice questions
    audio_response: Optional[str] = None  # For speaking questions
    time_spent: Optional[int] = None  # Time in seconds


class QuestionSubmitResponse(BaseModel):
    """Response schema for question submission"""
    is_correct: bool
    score: Optional[float] = None
    explanation: Optional[str] = None
    correct_answer: Optional[str] = None
    feedback: Optional[str] = None


class QuestionsListResponse(BaseModel):
    """Response schema for listing questions"""
    questions: List[QuestionResponse]
    total: int
    lesson_id: Optional[int] = None
