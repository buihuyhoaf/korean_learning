from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException, ForbiddenException
from ...models.user_final_quiz_attempt import UserFinalQuizAttempt
from ...models.final_quiz import FinalQuiz
from ...models.user import User
from ...schemas.user_final_quiz_attempt import (
    UserFinalQuizAttemptCreate,
    UserFinalQuizAttemptComplete,
    UserFinalQuizAttemptRead,
    UserFinalQuizAttemptListResponse,
    FinalQuizAttemptStartResponse,
    FinalQuizAttemptCompleteResponse
)
from ...crud.user_final_quiz_attempt import UserFinalQuizAttemptCRUD

router = APIRouter(prefix="/final-quiz", tags=["final-quiz-attempts"])


@router.post("/attempts/start", response_model=FinalQuizAttemptStartResponse, status_code=status.HTTP_201_CREATED)
async def start_final_quiz_attempt(
    attempt_data: UserFinalQuizAttemptCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> FinalQuizAttemptStartResponse:
    """Start a new final quiz attempt"""
    
    user_id = current_user["id"]
    
    # Check if final quiz exists
    quiz_query = select(FinalQuiz).where(FinalQuiz.id == attempt_data.final_quiz_id)
    quiz_result = await db.execute(quiz_query)
    quiz = quiz_result.scalar_one_or_none()
    
    if not quiz:
        raise NotFoundException("Final quiz not found")
    
    # Create attempt
    attempt = await UserFinalQuizAttemptCRUD.create_attempt(
        db, user_id, attempt_data.final_quiz_id
    )
    
    return FinalQuizAttemptStartResponse(
        attempt_id=attempt.id,
        final_quiz_id=attempt.final_quiz_id,
        started_at=attempt.started_at,
        message="Final quiz attempt started successfully"
    )


@router.put("/attempts/{attempt_id}/complete", response_model=FinalQuizAttemptCompleteResponse)
async def complete_final_quiz_attempt(
    attempt_id: int,
    completion_data: UserFinalQuizAttemptComplete,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> FinalQuizAttemptCompleteResponse:
    """Complete a final quiz attempt with score"""
    
    user_id = current_user["id"]
    
    # Get the attempt
    attempt = await UserFinalQuizAttemptCRUD.get_attempt_by_id(db, attempt_id)
    if not attempt:
        raise NotFoundException("Final quiz attempt not found")
    
    # Check if user owns this attempt
    if attempt.user_id != user_id:
        raise ForbiddenException("You can only complete your own attempts")
    
    # Check if already completed
    if attempt.completed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This attempt has already been completed"
        )
    
    # Update attempt with score
    updated_attempt = await UserFinalQuizAttemptCRUD.update_attempt_score(
        db, attempt_id, completion_data.score, completion_data.exp_earned
    )
    
    if not updated_attempt:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete the attempt"
        )
    
    return FinalQuizAttemptCompleteResponse(
        attempt_id=updated_attempt.id,
        score=updated_attempt.score,
        exp_earned=updated_attempt.exp_earned,
        completed_at=updated_attempt.completed_at,
        message="Final quiz attempt completed successfully"
    )


@router.get("/users/{user_id}/final-quiz-attempts", response_model=UserFinalQuizAttemptListResponse)
async def get_user_final_quiz_attempts(
    user_id: int,
    skip: int = Query(0, ge=0, description="Number of attempts to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of attempts to return"),
    completed_only: bool = Query(False, description="Show only completed attempts"),
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> UserFinalQuizAttemptListResponse:
    """Get all final quiz attempts for a user"""
    
    # Check if user exists
    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise NotFoundException("User not found")
    
    # Check if user can view these attempts (own attempts or admin)
    if user_id != current_user["id"] and current_user.get("role") != "admin":
        raise ForbiddenException("You can only view your own attempts")
    
    # Get attempts with details
    attempts_response = await UserFinalQuizAttemptCRUD.get_attempts_with_details(
        db, user_id, skip, limit
    )
    
    # Filter completed attempts if requested
    if completed_only:
        attempts_response.attempts = [
            attempt for attempt in attempts_response.attempts 
            if attempt.is_completed
        ]
        attempts_response.completed_count = len(attempts_response.attempts)
    
    return attempts_response


@router.get("/attempts/{attempt_id}", response_model=UserFinalQuizAttemptRead)
async def get_final_quiz_attempt(
    attempt_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> UserFinalQuizAttemptRead:
    """Get a specific final quiz attempt by ID"""
    
    attempt = await UserFinalQuizAttemptCRUD.get_attempt_by_id(db, attempt_id)
    if not attempt:
        raise NotFoundException("Final quiz attempt not found")
    
    # Check if user can view this attempt
    if attempt.user_id != current_user["id"] and current_user.get("role") != "admin":
        raise ForbiddenException("You can only view your own attempts")
    
    return UserFinalQuizAttemptRead(
        id=attempt.id,
        user_id=attempt.user_id,
        final_quiz_id=attempt.final_quiz_id,
        score=attempt.score,
        exp_earned=attempt.exp_earned,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        is_completed=attempt.completed_at is not None
    )


@router.get("/users/{user_id}/final-quiz-attempts/stats")
async def get_user_final_quiz_stats(
    user_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get final quiz attempt statistics for a user"""
    
    # Check if user exists
    user_query = select(User).where(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise NotFoundException("User not found")
    
    # Check if user can view these stats
    if user_id != current_user["id"] and current_user.get("role") != "admin":
        raise ForbiddenException("You can only view your own statistics")
    
    stats = await UserFinalQuizAttemptCRUD.get_attempt_stats_by_user(db, user_id)
    return stats


@router.get("/quizzes/{final_quiz_id}/attempts/{user_id}")
async def get_user_attempt_for_quiz(
    final_quiz_id: int,
    user_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> UserFinalQuizAttemptRead:
    """Get user's attempt for a specific final quiz"""
    
    # Check if user can view this attempt
    if user_id != current_user["id"] and current_user.get("role") != "admin":
        raise ForbiddenException("You can only view your own attempts")
    
    attempt = await UserFinalQuizAttemptCRUD.get_attempt_by_quiz(
        db, user_id, final_quiz_id
    )
    
    if not attempt:
        raise NotFoundException("No attempt found for this user and final quiz")
    
    return UserFinalQuizAttemptRead(
        id=attempt.id,
        user_id=attempt.user_id,
        final_quiz_id=attempt.final_quiz_id,
        score=attempt.score,
        exp_earned=attempt.exp_earned,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        is_completed=attempt.completed_at is not None
    )


@router.delete("/attempts/{attempt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_final_quiz_attempt(
    attempt_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_superuser)] = None
) -> None:
    """Delete a final quiz attempt (Admin only)"""
    
    success = await UserFinalQuizAttemptCRUD.delete_attempt(db, attempt_id)
    if not success:
        raise NotFoundException("Final quiz attempt not found")
