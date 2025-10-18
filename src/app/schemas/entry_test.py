from datetime import datetime
from typing import Annotated, List, Optional, TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from .course import CourseRead


class EntryTestQuestionOptionBase(BaseModel):
    option_text: Annotated[str, Field(min_length=1, examples=["Hello"])]
    is_correct: Annotated[bool, Field(default=False)]


class EntryTestQuestionOption(EntryTestQuestionOptionBase):
    id: int
    created_at: datetime


class EntryTestQuestionOptionRead(EntryTestQuestionOptionBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class EntryTestQuestionBase(BaseModel):
    content: Annotated[str, Field(min_length=1, examples=["What does 안녕하세요 mean?"])]
    audio_url: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    correct_answer: Annotated[str, Field(min_length=1, examples=["Hello"])]
    explanation: Optional[str] = None
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
    model_config = ConfigDict(from_attributes=True)
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
    model_config = ConfigDict(from_attributes=True)
    questions: List[EntryTestQuestionRead]
    related_course: Optional["CourseRead"] = None


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
    recommended_course_title: str
    message: Annotated[str, Field(examples=["Entry test completed successfully! You have been placed in course Seoul 1A."])]


# Additional schemas for admin CRUD operations

class EntryTestScoreRangeBase(BaseModel):
    """Base schema for EntryTestResult (score range mapping)"""
    entry_test_id: Annotated[int, Field(gt=0)]
    min_score: Annotated[float, Field(ge=0, le=100)]
    max_score: Annotated[float, Field(ge=0, le=100)]
    course_id: Annotated[int, Field(gt=0)]


class EntryTestScoreRangeCreate(EntryTestScoreRangeBase):
    model_config = ConfigDict(extra="forbid")


class EntryTestScoreRangeUpdate(BaseModel):
    min_score: Annotated[float | None, Field(ge=0, le=100, default=None)]
    max_score: Annotated[float | None, Field(ge=0, le=100, default=None)]
    course_id: Annotated[int | None, Field(gt=0, default=None)]
    
    model_config = ConfigDict(extra="forbid")


class EntryTestScoreRangeRead(EntryTestScoreRangeBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserEntryTestHistoryRead(BaseModel):
    id: int
    user_id: int
    entry_test_id: int
    score: float
    recommended_course_id: int
    taken_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserEntryTestHistoryCreate(BaseModel):
    """Create schema for UserEntryTestHistory (read-only, should not be used)"""
    user_id: int
    entry_test_id: int
    score: float
    recommended_course_id: int

    model_config = ConfigDict(extra="forbid")


class UserEntryTestHistoryUpdate(BaseModel):
    """Update schema for UserEntryTestHistory (read-only, should not be used)"""
    user_id: Annotated[int | None, Field(gt=0, default=None)]
    entry_test_id: Annotated[int | None, Field(gt=0, default=None)]
    score: Annotated[float | None, Field(ge=0, le=100, default=None)]
    recommended_course_id: Annotated[int | None, Field(gt=0, default=None)]

    model_config = ConfigDict(extra="forbid")


# Update existing schemas for admin use

class EntryTestQuestionOptionCreate(BaseModel):
    option_text: Annotated[str, Field(min_length=1)]
    is_correct: Annotated[bool, Field(default=False)]
    question_id: Annotated[int, Field(gt=0)]
    
    model_config = ConfigDict(extra="forbid")


class EntryTestQuestionOptionUpdate(BaseModel):
    option_text: Annotated[str | None, Field(min_length=1, default=None)]
    is_correct: Annotated[bool | None, Field(default=None)]
    
    model_config = ConfigDict(extra="forbid")


class EntryTestQuestionCreateAdmin(BaseModel):
    content: Annotated[str, Field(min_length=1)]
    audio_url: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    correct_answer: Annotated[str, Field(min_length=1)]
    explanation: Optional[str] = None
    order_index: Annotated[int, Field(ge=0, default=0)]
    entry_test_id: Annotated[int, Field(gt=0)]
    
    model_config = ConfigDict(extra="forbid")


class EntryTestQuestionUpdate(BaseModel):
    content: Annotated[str | None, Field(min_length=1, default=None)]
    audio_url: Optional[str] = Field(None, max_length=500)
    image_url: Optional[str] = Field(None, max_length=500)
    correct_answer: Annotated[str | None, Field(min_length=1, default=None)]
    explanation: Optional[str] = None
    order_index: Annotated[int | None, Field(ge=0, default=None)]
    
    model_config = ConfigDict(extra="forbid")


class EntryTestUpdate(BaseModel):
    name: Annotated[str | None, Field(min_length=1, max_length=200, default=None)]
    description: Annotated[str | None, Field(min_length=1, default=None)]
    related_course_id: Annotated[int | None, Field(gt=0, default=None)]
    
    model_config = ConfigDict(extra="forbid")


# Update forward references after all models are defined
def _update_forward_refs():
    from .course import CourseRead
    EntryTestRead.model_rebuild()

_update_forward_refs()
