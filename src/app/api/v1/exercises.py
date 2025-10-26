from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException, ForbiddenException
from ...models.exercise import Exercise, ExerciseType
from ...models.course import Lesson
from ...schemas.exercise import (
    ExerciseCreate, ExerciseUpdate, ExerciseRead, 
    ExerciseListResponse, ExerciseStatsResponse
)
from ...crud.exercise import ExerciseCRUD

router = APIRouter(prefix="/exercises", tags=["exercises"])


@router.get("/lessons/{lesson_id}/exercises", response_model=ExerciseListResponse)
async def get_lesson_exercises(
    lesson_id: int,
    exercise_type: Optional[ExerciseType] = Query(None, description="Filter by exercise type"),
    skip: int = Query(0, ge=0, description="Number of exercises to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of exercises to return"),
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> ExerciseListResponse:
    """Get all exercises for a specific lesson"""
    
    # Check if lesson exists
    lesson_query = select(Lesson).where(Lesson.id == lesson_id)
    lesson_result = await db.execute(lesson_query)
    lesson = lesson_result.scalar_one_or_none()
    
    if not lesson:
        raise NotFoundException("Lesson not found")
    
    # Get exercises
    exercises = await ExerciseCRUD.get_exercises_by_lesson(
        db, lesson_id, exercise_type, skip, limit
    )
    
    # Get total count
    total = await ExerciseCRUD.get_exercise_count_by_lesson(db, lesson_id)
    
    return ExerciseListResponse(
        exercises=[ExerciseRead.model_validate(exercise) for exercise in exercises],
        total=total,
        lesson_id=lesson_id,
        exercise_type=exercise_type
    )


@router.get("/lessons/{lesson_id}/exercises/stats", response_model=ExerciseStatsResponse)
async def get_lesson_exercise_stats(
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> ExerciseStatsResponse:
    """Get exercise statistics for a lesson"""
    
    # Check if lesson exists
    lesson_query = select(Lesson).where(Lesson.id == lesson_id)
    lesson_result = await db.execute(lesson_query)
    lesson = lesson_result.scalar_one_or_none()
    
    if not lesson:
        raise NotFoundException("Lesson not found")
    
    return await ExerciseCRUD.get_exercise_stats_by_lesson(db, lesson_id)


@router.get("/exercises/{exercise_id}", response_model=ExerciseRead)
async def get_exercise(
    exercise_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> ExerciseRead:
    """Get a specific exercise by ID"""
    
    exercise = await ExerciseCRUD.get_exercise_by_id(db, exercise_id)
    if not exercise:
        raise NotFoundException("Exercise not found")
    
    return ExerciseRead.model_validate(exercise)


@router.post("/exercises", response_model=ExerciseRead, status_code=status.HTTP_201_CREATED)
async def create_exercise(
    exercise_data: ExerciseCreate,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_superuser)] = None
) -> ExerciseRead:
    """Create a new exercise (Admin only)"""
    
    # Check if lesson exists
    lesson_query = select(Lesson).where(Lesson.id == exercise_data.lesson_id)
    lesson_result = await db.execute(lesson_query)
    lesson = lesson_result.scalar_one_or_none()
    
    if not lesson:
        raise NotFoundException("Lesson not found")
    
    exercise = await ExerciseCRUD.create_exercise(db, exercise_data)
    return ExerciseRead.model_validate(exercise)


@router.put("/exercises/{exercise_id}", response_model=ExerciseRead)
async def update_exercise(
    exercise_id: int,
    exercise_data: ExerciseUpdate,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_superuser)] = None
) -> ExerciseRead:
    """Update an existing exercise (Admin only)"""
    
    exercise = await ExerciseCRUD.update_exercise(db, exercise_id, exercise_data)
    if not exercise:
        raise NotFoundException("Exercise not found")
    
    return ExerciseRead.model_validate(exercise)


@router.delete("/exercises/{exercise_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_exercise(
    exercise_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_superuser)] = None
) -> None:
    """Delete an exercise (Admin only)"""
    
    success = await ExerciseCRUD.delete_exercise(db, exercise_id)
    if not success:
        raise NotFoundException("Exercise not found")


@router.get("/lessons/{lesson_id}/exercises/listening", response_model=ExerciseListResponse)
async def get_listening_exercises(
    lesson_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> ExerciseListResponse:
    """Get listening exercises for a lesson"""
    
    exercises = await ExerciseCRUD.get_exercises_by_type(
        db, lesson_id, ExerciseType.LISTENING
    )
    
    total = await ExerciseCRUD.get_exercise_count_by_lesson(db, lesson_id)
    
    return ExerciseListResponse(
        exercises=[ExerciseRead.model_validate(exercise) for exercise in exercises],
        total=total,
        lesson_id=lesson_id,
        exercise_type=ExerciseType.LISTENING
    )


@router.get("/lessons/{lesson_id}/exercises/speaking", response_model=ExerciseListResponse)
async def get_speaking_exercises(
    lesson_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> ExerciseListResponse:
    """Get speaking exercises for a lesson"""
    
    exercises = await ExerciseCRUD.get_exercises_by_type(
        db, lesson_id, ExerciseType.SPEAKING
    )
    
    total = await ExerciseCRUD.get_exercise_count_by_lesson(db, lesson_id)
    
    return ExerciseListResponse(
        exercises=[ExerciseRead.model_validate(exercise) for exercise in exercises],
        total=total,
        lesson_id=lesson_id,
        exercise_type=ExerciseType.SPEAKING
    )


@router.get("/lessons/{lesson_id}/exercises/writing", response_model=ExerciseListResponse)
async def get_writing_exercises(
    lesson_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> ExerciseListResponse:
    """Get writing exercises for a lesson"""
    
    exercises = await ExerciseCRUD.get_exercises_by_type(
        db, lesson_id, ExerciseType.WRITING
    )
    
    total = await ExerciseCRUD.get_exercise_count_by_lesson(db, lesson_id)
    
    return ExerciseListResponse(
        exercises=[ExerciseRead.model_validate(exercise) for exercise in exercises],
        total=total,
        lesson_id=lesson_id,
        exercise_type=ExerciseType.WRITING
    )


@router.put("/exercises/reorder", status_code=status.HTTP_200_OK)
async def reorder_exercises(
    lesson_id: int,
    exercise_ids: List[int],
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
    current_user: Annotated[dict, Depends(get_current_superuser)] = None
) -> dict:
    """Reorder exercises within a lesson (Admin only)"""
    
    success = await ExerciseCRUD.reorder_exercises(db, lesson_id, exercise_ids)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to reorder exercises. Check that all exercise IDs belong to the lesson."
        )
    
    return {"message": "Exercises reordered successfully"}
