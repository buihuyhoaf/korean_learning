from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict


class FinalQuizBase(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str
    type: str = Field(max_length=50)  # vocabulary, listening, speaking, writing
    order_index: int = 0


class FinalQuizCreate(FinalQuizBase):
    unit_id: int = Field(gt=0)
    
    model_config = ConfigDict(extra="forbid")


class FinalQuizUpdate(BaseModel):
    unit_id: Optional[int] = Field(gt=0, default=None)
    title: Optional[str] = Field(min_length=1, max_length=200, default=None)
    description: Optional[str] = None
    type: Optional[str] = Field(max_length=50, default=None)
    order_index: Optional[int] = None

    model_config = ConfigDict(extra="forbid")


class FinalQuizResponse(FinalQuizBase):
    id: int
    unit_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class FinalQuizWithQuestionsResponse(FinalQuizResponse):
    """Response schema for final quiz with questions"""
    questions: List[dict] = []  # Will be populated by the API logic


class FinalQuizListResponse(BaseModel):
    """Response schema for listing final quizzes"""
    quizzes: List[FinalQuizResponse]
    total: int
    unit_id: Optional[int] = None
