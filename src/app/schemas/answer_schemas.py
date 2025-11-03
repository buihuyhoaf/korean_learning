"""
Pydantic Schemas for User Answers

Provides request and response schemas for submitting and retrieving user answers.
Supports flexible JSONB storage for different answer types.
"""
from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field, ConfigDict


class AnswerSubmitRequest(BaseModel):
    """
    Request schema for submitting an answer.
    
    The 'answer' field uses JSONB to support different question types:
    - MULTIPLE_CHOICE: [1, 2, 3] (list of selected option IDs)
    - BLANK: "answer text" (string)
    - SENTENCE_ORDER: ["word1", "word2", "word3"] (list of strings in user's order)
    - MATCHING: {"pair1": {"left_id": 1, "right_id": 2}, ...} (dict mapping pairs)
    - AUDIO_COMPREHENSION: {"answer": "transcribed text", "audio_url": "..."}
    - PRONUNCIATION: {"audio_url": "...", "transcript": "..."}
    """
    answer: Any = Field(..., description="Answer data (flexible JSON structure)")
    time_spent: Optional[int] = Field(None, description="Time spent in seconds")
    model_config = ConfigDict(extra="forbid")


class AnswerResponse(BaseModel):
    """Response schema for a submitted answer."""
    id: int
    user_id: int
    question_id: int
    answer: Any = Field(..., description="Stored answer data")
    is_correct: Optional[bool] = Field(None, description="Whether answer is correct")
    score: Optional[float] = Field(None, ge=0.0, le=1.0, description="Score (0.0-1.0)")
    answered_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class AnswerSubmitResponse(BaseModel):
    """
    Response schema after submitting an answer.
    
    Includes correctness evaluation and feedback.
    """
    answer_id: int
    is_correct: bool
    score: float = Field(..., ge=0.0, le=1.0)
    feedback: Optional[str] = Field(None, description="Feedback message")
    correct_answer: Optional[Any] = Field(None, description="Correct answer (if applicable)")
    explanation: Optional[str] = Field(None, description="Question explanation")


class UserAnswerHistoryResponse(BaseModel):
    """Response schema for user's answer history."""
    id: int
    question_id: int
    answer: Any
    is_correct: Optional[bool]
    score: Optional[float]
    answered_at: datetime
    question: Optional[dict] = Field(None, description="Question details if included")
    
    model_config = ConfigDict(from_attributes=True)

