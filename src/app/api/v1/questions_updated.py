# Updated API Endpoints for Questions and FinalQuiz
# This shows how to update the existing quiz_management.py

from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException
from ...models.question import Question, QuestionOption
from ...models.final_quiz import FinalQuiz
from ...models.user import User
from ...schemas.question import (
    QuestionResponse, QuestionsListResponse, 
    QuestionCreate, QuestionSubmitRequest, QuestionSubmitResponse
)
from ...schemas.final_quiz import FinalQuizResponse, FinalQuizWithQuestionsResponse
from ...crud.question_crud import QuestionCRUD, FinalQuizCRUD

router = APIRouter(tags=["questions_and_quizzes"])


# Updated endpoints for questions
@router.get("/lessons/{lesson_id}/questions", response_model=QuestionsListResponse)
async def get_lesson_questions(
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> QuestionsListResponse:
    """Get all questions for a specific lesson (new approach)"""
    return await QuestionCRUD.get_questions_by_lesson(db, lesson_id)


@router.get("/quizzes/{quiz_id}/questions", response_model=QuestionsListResponse)
async def get_quiz_questions(
    quiz_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> QuestionsListResponse:
    """Get all questions for a specific quiz (backward compatibility)"""
    return await QuestionCRUD.get_questions_by_quiz(db, quiz_id)


@router.get("/questions/{question_id}", response_model=QuestionResponse)
async def get_question(
    question_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> QuestionResponse:
    """Get a single question by ID"""
    question = await QuestionCRUD.get_question_by_id(db, question_id)
    if not question:
        raise NotFoundException("Question not found")
    return question


@router.post("/questions", response_model=QuestionResponse, status_code=201)
async def create_question(
    question_data: QuestionCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_superuser)]
) -> QuestionResponse:
    """Create a new question (Admin only)"""
    return await QuestionCRUD.create_question(db, question_data)


@router.post("/questions/{question_id}/submit", response_model=QuestionSubmitResponse)
async def submit_question_answer(
    question_id: int,
    request: QuestionSubmitRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> QuestionSubmitResponse:
    """Submit answer for a specific question"""
    
    # Get question
    question = await QuestionCRUD.get_question_by_id(db, question_id)
    if not question:
        raise NotFoundException("Question not found")
    
    # Evaluate answer based on question type
    is_correct = False
    score = None
    feedback = None
    
    if question.question_type in ["vocabulary", "grammar", "reading"]:
        # Multiple choice questions
        if request.selected_option_ids:
            correct_options = [opt.id for opt in question.options if opt.is_correct]
            is_correct = set(request.selected_option_ids) == set(correct_options)
            score = 1.0 if is_correct else 0.0
            
    elif question.question_type in ["listening"]:
        # Audio-based questions - compare with correct answer
        if request.answer and question.correct_answer:
            is_correct = request.answer.lower().strip() == question.correct_answer.lower().strip()
            score = 1.0 if is_correct else 0.0
            
    elif question.question_type in ["speaking", "writing"]:
        # Subjective questions - always mark as correct for now
        is_correct = bool(request.answer or request.audio_response)
        score = 1.0 if is_correct else 0.0
        feedback = "Good job!" if is_correct else "Please try again."
    
    return QuestionSubmitResponse(
        is_correct=is_correct,
        score=score,
        explanation=question.explanation,
        correct_answer=question.correct_answer,
        feedback=feedback
    )


# Updated endpoints for final quizzes
@router.get("/units/{unit_id}/final-quiz", response_model=dict)
async def get_unit_final_quiz(
    unit_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Get final quiz for a specific unit"""
    
    quiz_data = await FinalQuizCRUD.get_final_quiz_by_unit(db, unit_id)
    if not quiz_data:
        raise NotFoundException("Final quiz not found for this unit")
    
    return quiz_data


# Backward compatibility endpoint
@router.get("/quizzes/{quiz_id}", response_model=dict)
async def get_quiz_legacy(
    quiz_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Get quiz details with questions (legacy endpoint for backward compatibility)"""
    
    # Get final quiz
    quiz_query = select(FinalQuiz).filter(FinalQuiz.id == quiz_id)
    quiz_result = await db.execute(quiz_query)
    quiz = quiz_result.scalar_one_or_none()
    
    if not quiz:
        raise NotFoundException("Quiz not found")
    
    # Get questions
    questions_query = (
        select(Question)
        .options(
            selectinload(Question.options),
            selectinload(Question.question_type)
        )
        .filter(Question.quiz_id == quiz_id)
        .order_by(Question.order_index)
    )
    
    questions_result = await db.execute(questions_query)
    questions = questions_result.scalars().all()
    
    # Format response to match old API structure
    quiz_data = {
        "id": quiz.id,
        "unit_id": quiz.unit_id,  # New field
        "title": quiz.title,
        "description": quiz.description,
        "type": quiz.type,
        "order_index": quiz.order_index,
        "created_at": quiz.created_at,
        "questions": [
            {
                "id": q.id,
                "content": q.content,
                "audio_url": q.audio_url,
                "image_url": q.image_url,
                "explanation": q.explanation,
                "order_index": q.order_index,
                "question_type": {
                    "id": q.question_type.id,
                    "name": q.question_type.name,
                    "description": q.question_type.description
                },
                "options": [
                    {
                        "id": option.id,
                        "option_text": option.option_text,
                        "is_correct": option.is_correct
                    }
                    for option in q.options
                ]
            }
            for q in questions
        ]
    }
    
    return quiz_data
