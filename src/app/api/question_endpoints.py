"""
API Endpoints for Questions

Provides REST API endpoints for managing questions with support for all 9 question types.
"""
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.dependencies import get_current_user, get_current_superuser
from ..core.db.database import async_get_db
from ..core.exceptions.http_exceptions import NotFoundException
from ..schemas.question_schemas import (
    QuestionCreate,
    QuestionUpdate,
    QuestionResponse,
    QuestionsListResponse,
    QuestionTypeResponse
)
from ..schemas.answer_schemas import AnswerSubmitRequest, AnswerSubmitResponse
from ..crud.question_crud import QuestionCRUD
from ..crud.answer_crud import AnswerCRUD

router = APIRouter(tags=["questions"], prefix="/questions")

# Also create a router for lesson-specific endpoints
lesson_questions_router = APIRouter(tags=["lessons"])


@lesson_questions_router.get("/lessons/{lesson_id}/questions", response_model=QuestionsListResponse)
async def get_lesson_questions(
    lesson_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> QuestionsListResponse:
    """
    Get all questions for a specific lesson.
    
    Returns questions with all subtype data loaded based on their question types.
    Questions are ordered by order_index.
    """
    return await QuestionCRUD.get_by_lesson(db, lesson_id, skip, limit)


@router.get("/types", response_model=list[QuestionTypeResponse])
async def get_question_types(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> list[QuestionTypeResponse]:
    """
    Get all available question types.
    
    Returns a list of question types with their codes and descriptions.
    """
    types = await QuestionCRUD.list_question_types(db)
    return [QuestionTypeResponse.model_validate(qt) for qt in types]


@router.get("/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> QuestionResponse:
    """
    Get a single question by ID with all subtype data loaded.
    
    The response includes nested data based on the question type:
    - MULTIPLE_CHOICE: includes options
    - MATCHING: includes matching_pairs
    - SENTENCE_ORDER: includes sentence_order
    - AUDIO_COMPREHENSION: includes audio_comprehension
    - PRONUNCIATION: includes pronunciation
    - BLANK: includes blank
    """
    question = await QuestionCRUD.get_by_id(db, question_id, include_subtypes=True)
    if not question:
        raise NotFoundException("Question not found")
    return QuestionResponse.model_validate(question)


@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
async def create_question(
    question_data: QuestionCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_superuser)]
) -> QuestionResponse:
    """
    Create a new question (Admin only).
    
    Supports all 9 question types through nested subtype data in the request body.
    See documentation for example payloads for each question type.
    """
    try:
        return await QuestionCRUD.create(db, question_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{question_id}", response_model=QuestionResponse)
async def update_question(
    question_id: int,
    question_data: QuestionUpdate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_superuser)]
) -> QuestionResponse:
    """
    Update a question (Admin only).
    
    Updates question fields. Note: subtype data should be updated separately
    or the question should be deleted and recreated.
    """
    updated = await QuestionCRUD.update(db, question_id, question_data)
    if not updated:
        raise NotFoundException("Question not found")
    return updated


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_question(
    question_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_superuser)]
):
    """
    Delete a question (Admin only).
    
    Cascade deletes all associated subtype data and user answers.
    """
    deleted = await QuestionCRUD.delete(db, question_id)
    if not deleted:
        raise NotFoundException("Question not found")


@router.post("/{question_id}/answers", response_model=AnswerSubmitResponse)
async def submit_answer(
    question_id: int,
    answer_data: AnswerSubmitRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> AnswerSubmitResponse:
    """
    Submit an answer for a question.
    
    The answer format depends on the question type:
    - MULTIPLE_CHOICE: [1, 2, 3] (list of option IDs)
    - BLANK: "answer text" (string)
    - SENTENCE_ORDER: ["word1", "word2", "word3"] (list in user's order)
    - MATCHING: {"pair1": {"left_id": 1, "right_id": 2}} (dict)
    - AUDIO_COMPREHENSION: {"answer": "text", "audio_url": "..."}
    - PRONUNCIATION: {"audio_url": "...", "transcript": "..."}
    
    Automatically evaluates correctness for MCQ, BLANK, SENTENCE_ORDER, and MATCHING types.
    """
    user_id = current_user["id"]
    try:
        return await AnswerCRUD.submit_answer(db, user_id, question_id, answer_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

