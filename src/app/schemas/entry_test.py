from datetime import datetime
from typing import Annotated, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EntryTestQuestionOptionBase(BaseModel):
    option_text: Annotated[str, Field(min_length=1, examples=["Hello"])]
    is_correct: Annotated[bool, Field(default=False)]


class EntryTestQuestionOption(EntryTestQuestionOptionBase):
    id: int
    created_at: datetime


class EntryTestQuestionOptionRead(EntryTestQuestionOptionBase):
    id: int


class EntryTestQuestionBase(BaseModel):
    content: Annotated[str, Field(min_length=1, examples=["What does 안녕하세요 mean?"])]
    audio_url: Optional[Annotated[str, Field(max_length=500)]] = None
    image_url: Optional[Annotated[str, Field(max_length=500)]] = None
    correct_answer: Annotated[str, Field(min_length=1, examples=["Hello"])]
    explanation: Optional[Annotated[str]] = None
    order_index: Annotated[int, Field(ge=0, default=0)]


class EntryTestQuestionCreate(EntryTestQuestionBase):
    entry_test_id: Annotated[int, Field(gt=0)]
    options: Annotated[List[EntryTestQuestionOptionBase], Field(min_items=2, max_items=6)]
    
    model_config = ConfigDict(extra="forbid")


class EntryTestQuestion(EntryTestQuestionBase):
    id: int
    entry_test_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EntryTestQuestionRead(EntryTestQuestion):
    options: List[EntryTestQuestionOptionRead]


class EntryTestBase(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=200, examples=["Korean Language Placement Test"])]
    description: Annotated[str, Field(min_length=1, examples=["Test to determine your Korean language level"])]
    related_course_id: Annotated[int, Field(gt=0, examples=[1])]


class EntryTestCreate(EntryTestBase):
    model_config = ConfigDict(extra="forbid")


class EntryTest(EntryTestBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class EntryTestRead(EntryTest):
    questions: List[EntryTestQuestionRead]
    related_course: Optional[dict] = None


class EntryTestSubmissionAnswer(BaseModel):
    question_id: Annotated[int, Field(gt=0)]
    selected_option_id: Annotated[int, Field(gt=0)]


class EntryTestSubmission(BaseModel):
    answers: Annotated[List[EntryTestSubmissionAnswer], Field(min_items=1)]

    model_config = ConfigDict(extra="forbid")


class EntryTestResultBase(BaseModel):
    user_id: int
    entry_test_id: int
    score: Annotated[float, Field(ge=0, le=100)]
    recommended_course_id: Annotated[int, Field(gt=0)]
    completed_at: datetime


class EntryTestResult(EntryTestResultBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class EntryTestSubmitResponse(BaseModel):
    score: Annotated[float, Field(ge=0, le=100)]
    recommended_course_id: Annotated[int, Field(gt=0)]
    recommended_course_title: Annotated[str]
    message: Annotated[str, examples=["Entry test completed successfully! You have been placed in course Seoul 1A."]]
