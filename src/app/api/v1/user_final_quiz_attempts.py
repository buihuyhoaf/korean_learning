from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException, ForbiddenException
from ...models.user_final_quiz_attempt import UserFinalQuizAttempt
from ...models.user import User
from ...models.final_quiz import FinalQuiz
from ...models.course import Unit
from ...schemas.user_final_quiz_attempt import (
    UserFinalQuizAttemptCreate,
    UserFinalQuizAttemptComplete,
    UserFinalQuizAttemptRead,
    UserFinalQuizAttemptWithDetails,
    UserFinalQuizAttemptListResponse,
    UserFinalQuizAttemptStatsResponse
)
from ...crud.user_final_quiz_attempt import UserFinalQuizAttemptCRUD

router = APIRouter(tags=["final-quiz-attempts"])


@router.post("/attempts/start", response_model=UserFinalQuizAttemptRead, status_code=status.HTTP_201_CREATED)
async def start_final_quiz_attempt(
    attempt_data: UserFinalQuizAttemptCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> UserFinalQuizAttemptRead:
    """Start a new final quiz attempt"""
    
    user_id = current_user["id"]
    
    try:
        # Check if user already has an active attempt for this quiz
        active_attempt = await UserFinalQuizAttemptCRUD.get_active_attempt(
            db, user_id, attempt_data.final_quiz_id
        )
        
        if active_attempt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active attempt for this final quiz. Complete it first."
            )
        
        # Create new attempt
        attempt = await UserFinalQuizAttemptCRUD.create_attempt(
            db, user_id, attempt_data.final_quiz_id
        )
        
        return UserFinalQuizAttemptRead.model_validate(attempt)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put("/attempts/{attempt_id}/complete", response_model=UserFinalQuizAttemptRead)
async def complete_final_quiz_attempt(
    attempt_id: int,
    completion_data: UserFinalQuizAttemptComplete,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> UserFinalQuizAttemptRead:
    """Complete a final quiz attempt"""
    
    user_id = current_user["id"]
    
    # Get the attempt and verify ownership
    attempt = await UserFinalQuizAttemptCRUD.get_attempt_by_id(db, attempt_id)
    if not attempt:
        raise NotFoundException("Final quiz attempt not found")
    
    if attempt.user_id != user_id:
        raise ForbiddenException("You can only complete your own attempts")
    
    if attempt.completed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This attempt has already been completed"
        )
    
    # Complete the attempt
    completed_attempt = await UserFinalQuizAttemptCRUD.complete_attempt(
        db, attempt_id, completion_data
    )
    
    if not completed_attempt:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to complete the attempt"
        )
    
    return UserFinalQuizAttemptRead.model_validate(completed_attempt)


@router.get("/attempts/{attempt_id}", response_model=UserFinalQuizAttemptRead)
async def get_final_quiz_attempt(
    attempt_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> UserFinalQuizAttemptRead:
    """Get a specific final quiz attempt"""
    
    user_id = current_user["id"]
    
    attempt = await UserFinalQuizAttemptCRUD.get_attempt_by_id(db, attempt_id)
    if not attempt:
        raise NotFoundException("Final quiz attempt not found")
    
    if attempt.user_id != user_id:
        raise ForbiddenException("You can only view your own attempts")
    
    return UserFinalQuizAttemptRead.model_validate(attempt)


@router.get("/users/{user_id}/final-quiz-attempts", response_model=UserFinalQuizAttemptListResponse)
async def get_user_final_quiz_attempts(
    user_id: int,
    skip: int = Query(0, ge=0, description="Number of attempts to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of attempts to return"),
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> UserFinalQuizAttemptListResponse:
    """Get all final quiz attempts for a user"""
    
    # Check if user can view these attempts (own attempts or admin)
    current_user_id = current_user["id"]
    is_admin = current_user.get("role") == "admin"
    
    if user_id != current_user_id and not is_admin:
        raise ForbiddenException("You can only view your own attempts")
    
    # Get attempts
    attempts = await UserFinalQuizAttemptCRUD.get_attempts_by_user(
        db, user_id, skip, limit, include_details=True
    )
    
    # Get total count
    total_query = select(func.count(UserFinalQuizAttempt.id)).where(
        UserFinalQuizAttempt.user_id == user_id
    )
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0
    
    # Format attempts with details
    attempts_with_details = []
    for attempt in attempts:
        attempt_dict = UserFinalQuizAttemptRead.model_validate(attempt).model_dump()
        
        # Add additional details
        if attempt.final_quiz:
            attempt_dict["final_quiz_title"] = attempt.final_quiz.title
            attempt_dict["final_quiz_description"] = attempt.final_quiz.description
            
            if attempt.final_quiz.unit:
                attempt_dict["unit_title"] = attempt.final_quiz.unit.title
                
                if attempt.final_quiz.unit.course:
                    attempt_dict["course_title"] = attempt.final_quiz.unit.course.title
        
        attempts_with_details.append(UserFinalQuizAttemptWithDetails(**attempt_dict))
    
    return UserFinalQuizAttemptListResponse(
        attempts=attempts_with_details,
        total=total,
        user_id=user_id
    )


@router.get("/users/{user_id}/final-quiz-attempts/stats", response_model=UserFinalQuizAttemptStatsResponse)
async def get_user_final_quiz_attempt_stats(
    user_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> UserFinalQuizAttemptStatsResponse:
    """Get final quiz attempt statistics for a user"""
    
    # Check if user can view these stats (own stats or admin)
    current_user_id = current_user["id"]
    is_admin = current_user.get("role") == "admin"
    
    if user_id != current_user_id and not is_admin:
        raise ForbiddenException("You can only view your own statistics")
    
    return await UserFinalQuizAttemptCRUD.get_user_attempt_stats(db, user_id)


@router.get("/quizzes/{final_quiz_id}/attempts", response_model=UserFinalQuizAttemptRead)
async def get_user_attempt_for_quiz(
    final_quiz_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> UserFinalQuizAttemptRead:
    """Get user's attempt for a specific final quiz"""
    
    user_id = current_user["id"]
    
    attempt = await UserFinalQuizAttemptCRUD.get_attempt_by_quiz(
        db, user_id, final_quiz_id
    )
    
    if not attempt:
        raise NotFoundException("No attempt found for this final quiz")
    
    return UserFinalQuizAttemptRead.model_validate(attempt)


@router.get("/quizzes/{final_quiz_id}/active-attempt", response_model=UserFinalQuizAttemptRead)
async def get_user_active_attempt_for_quiz(
    final_quiz_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> UserFinalQuizAttemptRead:
    """Get user's active (incomplete) attempt for a specific final quiz"""
    
    user_id = current_user["id"]
    
    attempt = await UserFinalQuizAttemptCRUD.get_active_attempt(
        db, user_id, final_quiz_id
    )
    
    if not attempt:
        raise NotFoundException("No active attempt found for this final quiz")
    
    return UserFinalQuizAttemptRead.model_validate(attempt)


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


# ============================================================================
# UNIT-LEVEL FINAL QUIZ ATTEMPT ENDPOINTS
# ============================================================================

@router.post("/units/{unit_id}/final-quiz/attempt", response_model=UserFinalQuizAttemptRead, status_code=status.HTTP_201_CREATED)
async def start_unit_final_quiz_attempt(
    unit_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> UserFinalQuizAttemptRead:
    """Start a new final quiz attempt for a unit"""
    
    from sqlalchemy import select
    user_id = current_user["id"]
    
    # Get unit and its final quiz
    unit_query = select(Unit).options(
        selectinload(Unit.final_quiz)
    ).filter(Unit.id == unit_id)
    unit_result = await db.execute(unit_query)
    unit = unit_result.scalar_one_or_none()
    
    if not unit:
        raise NotFoundException("Unit not found")
    
    if not unit.final_quiz:
        raise NotFoundException("No final quiz found for this unit")
    
    try:
        # Check if user already has an active attempt
        active_attempt = await UserFinalQuizAttemptCRUD.get_active_attempt(
            db, user_id, unit.final_quiz.id
        )
        
        if active_attempt:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have an active attempt for this final quiz. Complete it first."
            )
        
        # Create new attempt
        attempt = await UserFinalQuizAttemptCRUD.create_attempt(
            db, user_id, unit.final_quiz.id
        )
        
        return UserFinalQuizAttemptRead.model_validate(attempt)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )