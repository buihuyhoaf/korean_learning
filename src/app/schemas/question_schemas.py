"""
Pydantic Schemas for Questions

Provides request and response schemas for all question types.
Supports flexible JSONB data structures for media and metadata.
"""
from datetime import datetime
from typing import Any, Optional, List, Union
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator
import json


# ============================================================================
# Question Type Schemas
# ============================================================================

class QuestionTypeBase(BaseModel):
    """Base schema for question type."""
    code: str = Field(..., min_length=1, max_length=50, description="Unique code for question type")
    name: str = Field(..., min_length=1, max_length=100, description="Human-readable name")
    description: Optional[str] = Field(None, description="Detailed description")


class QuestionTypeCreate(QuestionTypeBase):
    """Schema for creating a question type."""
    model_config = ConfigDict(extra="forbid")


class QuestionTypeUpdate(BaseModel):
    """Schema for updating a question type."""
    code: Optional[str] = Field(None, min_length=1, max_length=50, description="Unique code for question type")
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="Human-readable name")
    description: Optional[str] = Field(None, description="Detailed description")
    model_config = ConfigDict(extra="forbid")


class QuestionTypeResponse(QuestionTypeBase):
    """Schema for question type response."""
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Question Option Schemas
# ============================================================================

class QuestionOptionBase(BaseModel):
    """Base schema for question option."""
    option_text: Optional[str] = Field(None, description="Text content of the option")
    option_media: Optional[dict[str, Any]] = Field(None, description="Media files (image, audio)")
    is_correct: bool = Field(False, description="Whether this option is correct")
    sort_order: int = Field(0, description="Display order")


class QuestionOptionCreate(QuestionOptionBase):
    """Schema for creating a question option."""
    model_config = ConfigDict(extra="forbid")


class QuestionOptionUpdate(BaseModel):
    """Schema for updating a question option."""
    option_text: Optional[str] = None
    option_media: Optional[dict[str, Any]] = None
    is_correct: Optional[bool] = None
    sort_order: Optional[int] = None
    model_config = ConfigDict(extra="forbid")


class QuestionOptionResponse(QuestionOptionBase):
    """Schema for question option response."""
    id: int
    question_id: int
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Question Subtype Schemas
# ============================================================================

class MatchingPairBase(BaseModel):
    """Base schema for matching pair."""
    left_text: Optional[str] = None
    left_media: Optional[dict[str, Any]] = None
    right_text: Optional[str] = None
    right_media: Optional[dict[str, Any]] = None
    sort_order: int = 0


class MatchingPairCreate(MatchingPairBase):
    """Schema for creating a matching pair."""
    model_config = ConfigDict(extra="forbid")


class MatchingPairUpdate(BaseModel):
    """Schema for updating a matching pair."""
    left_text: Optional[str] = None
    left_media: Optional[dict[str, Any]] = None
    right_text: Optional[str] = None
    right_media: Optional[dict[str, Any]] = None
    sort_order: Optional[int] = None
    model_config = ConfigDict(extra="forbid")


class MatchingPairResponse(MatchingPairBase):
    """Schema for matching pair response."""
    id: int
    question_id: int
    model_config = ConfigDict(from_attributes=True)


class SentenceOrderBase(BaseModel):
    """Base schema for sentence order."""
    correct_sequence: List[str] = Field(..., min_items=1, description="Correct order as list of strings")


class SentenceOrderCreate(SentenceOrderBase):
    """Schema for creating sentence order."""
    model_config = ConfigDict(extra="forbid")


class SentenceOrderUpdate(BaseModel):
    """Schema for updating sentence order."""
    correct_sequence: Optional[List[str]] = Field(None, min_items=1, description="Correct order as list of strings")
    model_config = ConfigDict(extra="forbid")


class SentenceOrderResponse(SentenceOrderBase):
    """Schema for sentence order response."""
    id: int
    question_id: int
    model_config = ConfigDict(from_attributes=True)


class AudioComprehensionBase(BaseModel):
    """Base schema for audio comprehension."""
    transcript: Optional[str] = None
    tts_config: Optional[dict[str, Any]] = None


class AudioComprehensionCreate(AudioComprehensionBase):
    """Schema for creating audio comprehension."""
    model_config = ConfigDict(extra="forbid")


class AudioComprehensionUpdate(BaseModel):
    """Schema for updating audio comprehension."""
    transcript: Optional[str] = None
    tts_config: Optional[dict[str, Any]] = None
    model_config = ConfigDict(extra="forbid")


class AudioComprehensionResponse(AudioComprehensionBase):
    """Schema for audio comprehension response."""
    id: int
    question_id: int
    model_config = ConfigDict(from_attributes=True)


class PronunciationBase(BaseModel):
    """Base schema for pronunciation."""
    target_phrase: str = Field(..., min_length=1)
    reference_audio_url: Optional[str] = None
    tts_config: Optional[dict[str, Any]] = None


class PronunciationCreate(PronunciationBase):
    """Schema for creating pronunciation."""
    model_config = ConfigDict(extra="forbid")


class PronunciationUpdate(BaseModel):
    """Schema for updating pronunciation."""
    target_phrase: Optional[str] = Field(None, min_length=1)
    reference_audio_url: Optional[str] = None
    tts_config: Optional[dict[str, Any]] = None
    model_config = ConfigDict(extra="forbid")


class PronunciationResponse(PronunciationBase):
    """Schema for pronunciation response."""
    id: int
    question_id: int
    model_config = ConfigDict(from_attributes=True)


class BlankBase(BaseModel):
    """Base schema for fill-in-the-blank."""
    correct_answer: str = Field(..., min_length=1)
    case_sensitive: bool = Field(False, description="Whether answer comparison is case-sensitive")


class BlankCreate(BlankBase):
    """Schema for creating fill-in-the-blank."""
    model_config = ConfigDict(extra="forbid")


class BlankUpdate(BaseModel):
    """Schema for updating fill-in-the-blank."""
    correct_answer: Optional[str] = Field(None, min_length=1)
    case_sensitive: Optional[bool] = Field(None, description="Whether answer comparison is case-sensitive")
    model_config = ConfigDict(extra="forbid")


class BlankResponse(BlankBase):
    """Schema for fill-in-the-blank response."""
    id: int
    question_id: int
    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Main Question Schemas
# ============================================================================

class QuestionBase(BaseModel):
    """Base schema for question."""
    content: Optional[str] = Field(None, description="Main question content/text")
    media: Optional[dict[str, Any]] = Field(None, description="Media files (image, audio, video)")
    question_metadata: Optional[dict[str, Any]] = Field(None, description="Type-specific settings, difficulty, hints")
    explanation: Optional[str] = Field(None, description="Explanation shown after answering")
    order_index: Optional[int] = Field(None, description="Ordering within lesson (auto-incremented if not provided)")
    
    @field_validator('media', mode='before')
    @classmethod
    def parse_media(cls, v):
        """Parse media from JSON string if needed (from admin forms)."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return v
        return v


class QuestionCreate(QuestionBase):
    """
    Schema for creating a question via API.
    
    Supports all 9 question types through nested subtype data:
    - MULTIPLE_CHOICE: requires options
    - MATCHING: requires matching_pairs
    - SENTENCE_ORDER: requires sentence_order
    - AUDIO_COMPREHENSION: requires audio_comprehension
    - PRONUNCIATION: requires pronunciation
    - BLANK: requires blank
    - etc.
    """
    question_type_id: int = Field(..., description="ID of question type")
    lesson_id: int = Field(..., description="ID of lesson this question belongs to")
    
    # Subtype data (optional, depends on question type)
    options: List[QuestionOptionCreate] = Field(default_factory=list, description="For MULTIPLE_CHOICE questions")
    matching_pairs: List[MatchingPairCreate] = Field(default_factory=list, description="For MATCHING questions")
    sentence_order: Optional[SentenceOrderCreate] = Field(None, description="For SENTENCE_ORDER questions")
    audio_comprehension: Optional[AudioComprehensionCreate] = Field(None, description="For AUDIO_COMPREHENSION questions")
    pronunciation: Optional[PronunciationCreate] = Field(None, description="For PRONUNCIATION questions")
    blank: Optional[BlankCreate] = Field(None, description="For BLANK questions")
    
    model_config = ConfigDict(extra="forbid")
    
    @model_validator(mode='after')
    def remove_empty_relationships(self):
        """Remove empty relationship fields to prevent passing them to SQLAlchemy model."""
        # List of relationship field names
        relationship_fields = ['options', 'matching_pairs', 'sentence_order', 
                             'audio_comprehension', 'pronunciation', 'blank']
        
        # Remove fields that are None or empty lists
        for field_name in relationship_fields:
            field_value = getattr(self, field_name, None)
            if field_value is None or (isinstance(field_value, list) and len(field_value) == 0):
                # Remove the attribute from the instance
                if hasattr(self, field_name):
                    delattr(self, field_name)
        
        return self


class QuestionCreateAdmin(QuestionBase):
    """Simplified schema for admin form creation (no relationships)."""
    question_type_id: int = Field(..., description="ID of question type")
    lesson_id: Optional[int] = Field(None, description="ID of lesson this question belongs to")
    
    model_config = ConfigDict(
        extra="forbid",
        # Allow JSONB fields to be sent as JSON strings from admin forms
        json_schema_extra={
            "properties": {
                "media": {"format": "jsonb"}
            }
        }
    )


class QuestionUpdate(BaseModel):
    """Schema for updating a question."""
    content: Optional[str] = None
    media: Optional[dict[str, Any]] = None
    question_metadata: Optional[dict[str, Any]] = None
    explanation: Optional[str] = None
    order_index: Optional[int] = None
    lesson_id: Optional[int] = None
    model_config = ConfigDict(extra="forbid")


class QuestionResponse(QuestionBase):
    """
    Schema for question response with nested subtype data.
    
    Includes all subtype relationships loaded based on question type.
    """
    id: int
    question_type_id: int
    lesson_id: Optional[int] = None
    created_at: datetime
    
    # Question type info
    question_type_relation: Optional[QuestionTypeResponse] = None
    
    # Subtype data (populated based on question type)
    options: List[QuestionOptionResponse] = Field(default_factory=list)
    matching_pairs: List[MatchingPairResponse] = Field(default_factory=list)
    sentence_order: Optional[SentenceOrderResponse] = None
    audio_comprehension: Optional[AudioComprehensionResponse] = None
    pronunciation: Optional[PronunciationResponse] = None
    blank: Optional[BlankResponse] = None
    
    model_config = ConfigDict(from_attributes=True)


class QuestionsListResponse(BaseModel):
    """Response schema for listing questions."""
    questions: List[QuestionResponse]
    total: int
    lesson_id: Optional[int] = None

