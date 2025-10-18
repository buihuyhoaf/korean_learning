from typing import Annotated, List, Optional
from datetime import datetime, UTC
import random

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException, BadRequestException
from ...models.entry_test import EntryTest, EntryTestQuestion, EntryTestQuestionOption, UserEntryTestResult
from ...models.user import User
from ...models.course import Course
from ...schemas.entry_test import (
    EntryTestRead,
    EntryTestQuestionRead,
    EntryTestQuestionOptionRead,
    EntryTestSubmitResponse, 
    EntryTestSubmission,
    EntryTestResult
)
from ...schemas.course import CourseRead

router = APIRouter(tags=["entry_test"])


def _convert_entry_test_to_read(entry_test: EntryTest, limit_questions: int = 10) -> EntryTestRead:
    """
    Convert EntryTest ORM object to EntryTestRead using proper Pydantic v2 approach.
    Uses model_validate on individual components to avoid nested validation issues.
    Randomly selects up to limit_questions questions if available.
    """
    # Step 1: Randomly select questions and convert with their nested options
    all_questions = list(entry_test.questions)
    
    # Randomly select up to limit_questions questions, or all if fewer exist
    selected_questions = random.sample(
        all_questions, 
        min(limit_questions, len(all_questions))
    ) if all_questions else []
    
    questions_data = []
    for question in selected_questions:
        # Convert question options first using model_validate
        options_data = [
            EntryTestQuestionOptionRead.model_validate(option)
            for option in question.options
        ]
        
        # Create question read model manually to avoid nested validation conflicts
        question_read = EntryTestQuestionRead(
            id=question.id,
            entry_test_id=question.entry_test_id,
            content=question.content,
            audio_url=question.audio_url,
            image_url=question.image_url,
            correct_answer=question.correct_answer,
            explanation=question.explanation,
            order_index=question.order_index,
            created_at=question.created_at,
            options=options_data
        )
        questions_data.append(question_read)
    
    # Step 2: Convert related course to proper Read model
    related_course_read = None
    if entry_test.related_course:
        related_course_read = CourseRead.model_validate(entry_test.related_course)
    
    # Step 3: Create EntryTestRead with all properly converted nested objects
    return EntryTestRead(
        id=entry_test.id,
        name=entry_test.name,
        description=entry_test.description,
        related_course_id=entry_test.related_course_id,
        created_at=entry_test.created_at,
        questions=questions_data,
        related_course=related_course_read
    )


def determine_recommended_course(score: float) -> int:
    """
    Determine recommended course based on entry test score.
    Score ranges:
    - 0-30: Seoul 1A (beginner)
    - 30-60: Seoul 1B (elementary)
    - 60-80: Seoul 2A (intermediate)
    - 80-100: Seoul 2B (upper intermediate)
    """
    if score < 30:
        return 1  # Seoul 1A
    elif score < 60:
        return 2  # Seoul 1B  
    elif score < 80:
        return 3  # Seoul 2A
    else:
        return 4  # Seoul 2B


@router.get("/entry-test/", response_model=EntryTestRead)
async def get_entry_test(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    limit: int = 10,
    entry_test_id: Optional[int] = None
) -> EntryTestRead:
    """Fetch entry test questions for the placement test. Returns random 10 questions by default.
    If entry_test_id is provided, it will get questions from that specific entry test.
    Otherwise, it will get questions from all available entry tests."""
    
    # Get entry test(s) - either specific one or first available
    if entry_test_id:
        entry_test_stmt = select(EntryTest).where(EntryTest.id == entry_test_id).options(selectinload(EntryTest.related_course))
    else:
        # Get first available entry test for backward compatibility
        entry_test_stmt = select(EntryTest).options(selectinload(EntryTest.related_course)).limit(1)
    
    entry_test_result = await db.execute(entry_test_stmt)
    entry_test = entry_test_result.scalar_one_or_none()
    
    if not entry_test:
        raise NotFoundException("No entry test found. Please contact administrator.")
    
    # Get random questions from all entry tests (if no specific entry_test_id) or just the specified one
    if entry_test_id:
        # Get questions from specific entry test
        question_ids_stmt = select(EntryTestQuestion.id).where(EntryTestQuestion.entry_test_id == entry_test_id)
    else:
        # Get questions from all entry tests (ID 1-5 based on user's requirement)
        question_ids_stmt = select(EntryTestQuestion.id).where(EntryTestQuestion.entry_test_id.in_([1, 2, 3, 4, 5]))
    
    question_ids_result = await db.execute(question_ids_stmt)
    all_question_ids = [row[0] for row in question_ids_result.fetchall()]
    
    if not all_question_ids:
        raise NotFoundException("No questions found for entry test(s).")
    
    # Select random question IDs (limit to 10 or fewer if not enough questions exist)
    random_question_ids = random.sample(all_question_ids, min(limit, len(all_question_ids)))
    
    # Fetch the selected questions with their options
    questions_stmt = (
        select(EntryTestQuestion)
        .options(selectinload(EntryTestQuestion.options))
        .where(EntryTestQuestion.id.in_(random_question_ids))
    )
    questions_result = await db.execute(questions_stmt)
    selected_questions = questions_result.scalars().all()
    
    # Manually create EntryTestRead with selected questions
    questions_data = []
    for question in selected_questions:
        options_data = [
            EntryTestQuestionOptionRead.model_validate(option)
            for option in question.options
        ]
        
        question_read = EntryTestQuestionRead(
            id=question.id,
            entry_test_id=question.entry_test_id,
            content=question.content,
            audio_url=question.audio_url,
            image_url=question.image_url,
            correct_answer=question.correct_answer,
            explanation=question.explanation,
            order_index=question.order_index,
            created_at=question.created_at,
            options=options_data
        )
        questions_data.append(question_read)
    
    # Convert related course to proper Read model
    related_course_read = None
    if entry_test.related_course:
        related_course_read = CourseRead.model_validate(entry_test.related_course)
    
    return EntryTestRead(
        id=entry_test.id,
        name=entry_test.name,
        description=entry_test.description,
        related_course_id=entry_test.related_course_id,
        created_at=entry_test.created_at,
        questions=questions_data,
        related_course=related_course_read
    )


@router.post("/entry-test/submit", response_model=EntryTestSubmitResponse)
async def submit_entry_test(
    request: Request,
    submission: EntryTestSubmission,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> EntryTestSubmitResponse:
    """Submit entry test answers, calculate score, and return recommended course."""
    
    user_id = current_user["id"]
    
    # Check if user has already completed entry test
    user_stmt = select(User).where(User.id == user_id)
    user_result = await db.execute(user_stmt)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise NotFoundException("User not found")
    
    if user.has_completed_entry_test:
        raise BadRequestException("User has already completed the entry test")
    
    # Get entry test (we only need basic info)
    entry_test_stmt = select(EntryTest).limit(1)
    entry_test_result = await db.execute(entry_test_stmt)
    entry_test = entry_test_result.scalar_one_or_none()
    
    if not entry_test:
        raise NotFoundException("Entry test not found")
    
    if not submission.answers:
        raise BadRequestException("No answers provided")
    
    # Get the specific questions that were answered by the user
    answered_question_ids = [answer.question_id for answer in submission.answers]
    
    # Fetch questions and options for the specific questions user answered
    questions_stmt = (
        select(EntryTestQuestion)
        .options(selectinload(EntryTestQuestion.options))
        .where(EntryTestQuestion.id.in_(answered_question_ids))
        .where(EntryTestQuestion.entry_test_id == entry_test.id)
    )
    questions_result = await db.execute(questions_stmt)
    answered_questions = questions_result.scalars().all()
    
    if len(answered_questions) != len(submission.answers):
        raise BadRequestException("Some answered questions not found or invalid")
    
    # Create a mapping of question_id to correct option_id for answered questions only
    correct_options = {}
    for question in answered_questions:
        for option in question.options:
            if option.is_correct:
                correct_options[question.id] = option.id
    
    # Calculate score based on answered questions only
    correct_answers = 0
    total_answered_questions = len(submission.answers)
    
    # Check submitted answers
    for answer in submission.answers:
        if answer.question_id in correct_options:
            if answer.selected_option_id == correct_options[answer.question_id]:
                correct_answers += 1
    
    # Calculate percentage score based on answered questions
    score_percentage = (correct_answers / total_answered_questions) * 100
    
    # Determine recommended course
    recommended_course_id = determine_recommended_course(score_percentage)
    
    # Get recommended course details
    course_stmt = select(Course).where(Course.id == recommended_course_id)
    course_result = await db.execute(course_stmt)
    recommended_course = course_result.scalar_one_or_none()
    
    if not recommended_course:
        raise NotFoundException("Recommended course not found")
    
    # Save the result
    test_result = UserEntryTestResult(
        user_id=user_id,
        entry_test_id=entry_test.id,
        score=score_percentage,
        recommended_course_id=recommended_course_id,
        completed_at=datetime.now(UTC)
    )
    
    db.add(test_result)
    
    # Update user
    user.has_completed_entry_test = True
    user.current_course_id = recommended_course_id
    user.entry_test_score = int(score_percentage)
    
    await db.commit()
    
    return EntryTestSubmitResponse(
        score=score_percentage,
        recommended_course_id=recommended_course_id,
        recommended_course_title=recommended_course.title,
        message=f"Entry test completed successfully! You have been placed in course {recommended_course.title}."
    )


@router.get("/entry-test/result", response_model=EntryTestResult)
async def get_entry_test_result(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> EntryTestResult:
    """Fetch previous entry test result for the user."""
    
    user_id = current_user["id"]
    
    stmt = (
        select(UserEntryTestResult)
        .where(UserEntryTestResult.user_id == user_id)
        .order_by(UserEntryTestResult.completed_at.desc())
        .limit(1)
    )
    
    result = await db.execute(stmt)
    test_result = result.scalar_one_or_none()
    
    if not test_result:
        raise NotFoundException("No entry test result found for this user")
    
    return EntryTestResult.model_validate(test_result)
