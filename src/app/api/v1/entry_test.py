from typing import Annotated, List, Optional
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException, BadRequestException
from ...models.entry_test import EntryTest, EntryTestQuestion, EntryTestQuestionOption, UserEntryTestResult
from ...models.user import User
from ...models.course import Course
from ...schemas.entry_test import (
    EntryTestRead, 
    EntryTestSubmitResponse, 
    EntryTestSubmission,
    EntryTestResult
)

router = APIRouter(tags=["entry_test"])


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
    current_user: Annotated[dict, Depends(get_current_user)]
) -> EntryTestRead:
    """Fetch entry test questions for the placement test."""
    
    # Get the first available entry test (you might want to make this more flexible)
    stmt = (
        select(EntryTest)
        .options(
            selectinload(EntryTest.questions).selectinload(EntryTestQuestion.options),
            selectinload(EntryTest.related_course)
        )
        .limit(1)
    )
    
    result = await db.execute(stmt)
    entry_test = result.scalar_one_or_none()
    
    if not entry_test:
        # Create a default entry test if none exists
        # This is a fallback - in production you'd want to ensure tests exist
        raise NotFoundException("No entry test found. Please contact administrator.")
    
    return EntryTestRead.model_validate(entry_test)


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
    
    # Get entry test questions and options
    entry_test_stmt = (
        select(EntryTest)
        .options(
            selectinload(EntryTest.questions).selectinload(EntryTestQuestion.options)
        )
        .limit(1)
    )
    
    entry_test_result = await db.execute(entry_test_stmt)
    entry_test = entry_test_result.scalar_one_or_none()
    
    if not entry_test:
        raise NotFoundException("Entry test not found")
    
    # Calculate score
    correct_answers = 0
    total_questions = len(entry_test.questions)
    
    if total_questions == 0:
        raise BadRequestException("Entry test has no questions")
    
    # Create a mapping of question_id to correct option_id
    correct_options = {}
    for question in entry_test.questions:
        for option in question.options:
            if option.is_correct:
                correct_options[question.id] = option.id
    
    # Check submitted answers
    for answer in submission.answers:
        if answer.question_id in correct_options:
            if answer.selected_option_id == correct_options[answer.question_id]:
                correct_answers += 1
    
    # Calculate percentage score
    score_percentage = (correct_answers / total_questions) * 100
    
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
