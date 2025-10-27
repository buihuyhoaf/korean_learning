# src/app/api/v1/course_management.py
from typing import Annotated, List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, Request
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException
from ...models.course import Course, Lesson, Unit
from ...models.progress import UserCourseProgress, UserUnitProgress, UserLessonProgress
from ...models.final_quiz import FinalQuiz
from ...models.exercise import Exercise
from ...crud.progress_tracking import ProgressTrackingCRUD

router = APIRouter(tags=["courses-units-lessons"])


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _convert_user_course_progress_to_dict(progress: Optional[UserCourseProgress]) -> Optional[dict]:
    """Convert UserCourseProgress ORM object to dictionary."""
    if not progress:
        return None
    return {
        "id": progress.id,
        "user_id": progress.user_id,
        "course_id": progress.course_id,
        "started_at": progress.started_at,
        "completed_at": progress.completed_at,
        "progress_percent": progress.progress_percent,
        "is_completed": progress.is_completed
    }


def _convert_user_unit_progress_to_dict(progress: Optional[UserUnitProgress]) -> Optional[dict]:
    """Convert UserUnitProgress ORM object to dictionary."""
    if not progress:
        return None
    return {
        "id": progress.id,
        "user_id": progress.user_id,
        "unit_id": progress.unit_id,
        "started_at": progress.started_at,
        "completed_at": progress.completed_at,
        "progress_percent": progress.progress_percent,
        "is_completed": progress.is_completed
    }


def _convert_user_lesson_progress_to_dict(progress: Optional[UserLessonProgress]) -> Optional[dict]:
    """Convert UserLessonProgress ORM object to dictionary."""
    if not progress:
        return None
    return {
        "id": progress.id,
        "user_id": progress.user_id,
        "lesson_id": progress.lesson_id,
        "started_at": progress.started_at,
        "completed_at": progress.completed_at,
        "progress_percent": progress.progress_percent,
        "is_completed": progress.is_completed
    }


# ============================================================================
# 1. COURSE LEVEL APIs
# ============================================================================

@router.get("/courses", response_model=PaginatedListResponse[dict])
async def get_courses(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 10,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get all courses with optional user progress"""
    offset = compute_offset(page, items_per_page)
    
    # Get courses
    courses_query = select(Course).options(
        selectinload(Course.units)
    ).order_by(Course.order_index)
    result = await db.execute(courses_query.offset(offset).limit(items_per_page))
    courses = result.scalars().all()
    total_result = await db.execute(select(func.count()).select_from(Course))
    total = total_result.scalar()
    
    # Get user progress if authenticated
    user_progress = {}
    if current_user:
        progress_query = select(UserCourseProgress).where(
            UserCourseProgress.user_id == current_user["id"]
        )
        progress_result = await db.execute(progress_query)
        user_progress = {p.course_id: p for p in progress_result.scalars().all()}
    
    # Format response
    courses_data = []
    for course in courses:
        course_dict = {
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "order_index": course.order_index,
            "created_at": course.created_at,
            "units_count": len(course.units),
            "progress": _convert_user_course_progress_to_dict(user_progress.get(course.id))
        }
        courses_data.append(course_dict)
    
    response = paginated_response(
        crud_data={"data": courses_data, "total": total},
        page=page,
        items_per_page=items_per_page
    )
    return response


@router.get("/courses/{course_id}", response_model=dict)
async def get_course(
    request: Request,
    course_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get a specific course with units list"""
    # Get course with units
    course_query = select(Course).options(
        selectinload(Course.units).selectinload(Unit.lessons),
        selectinload(Course.units).selectinload(Unit.final_quiz)
    ).filter(Course.id == course_id)
    course_result = await db.execute(course_query)
    course = course_result.scalar_one_or_none()
    
    if not course:
        raise NotFoundException("Course not found")
    
    # Get user progress
    user_progress = None
    if current_user:
        progress_query = select(UserCourseProgress).filter(
            UserCourseProgress.user_id == current_user["id"],
            UserCourseProgress.course_id == course_id
        )
        progress_result = await db.execute(progress_query)
        user_progress = progress_result.scalar_one_or_none()
    
    # Format response
    units_data = []
    for unit in course.units:
        unit_dict = {
            "id": unit.id,
            "title": unit.title,
            "description": unit.description,
            "order_index": unit.order_index,
            "created_at": unit.created_at,
            "lessons_count": len(unit.lessons),
            "has_final_quiz": unit.final_quiz is not None
        }
        
        # Get user progress for unit
        if current_user:
            unit_progress_query = select(UserUnitProgress).filter(
                UserUnitProgress.user_id == current_user["id"],
                UserUnitProgress.unit_id == unit.id
            )
            unit_progress_result = await db.execute(unit_progress_query)
            unit_progress = unit_progress_result.scalar_one_or_none()
            unit_dict["progress"] = _convert_user_unit_progress_to_dict(unit_progress)
        
        units_data.append(unit_dict)
    
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "order_index": course.order_index,
        "created_at": course.created_at,
        "units": units_data,
        "progress": _convert_user_course_progress_to_dict(user_progress)
    }


# ============================================================================
# 2. UNIT LEVEL APIs
# ============================================================================

@router.get("/units/{unit_id}", response_model=dict)
async def get_unit(
    request: Request,
    unit_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get a specific unit with lessons list + final quiz info"""
    # Get unit with lessons and final quiz
    unit_query = select(Unit).options(
        selectinload(Unit.lessons).selectinload(Lesson.questions),
        selectinload(Unit.lessons).selectinload(Lesson.exercises),
        selectinload(Unit.final_quiz)
    ).filter(Unit.id == unit_id)
    unit_result = await db.execute(unit_query)
    unit = unit_result.scalar_one_or_none()
    
    if not unit:
        raise NotFoundException("Unit not found")
    
    # Get user progress
    user_progress = None
    if current_user:
        progress_query = select(UserUnitProgress).filter(
            UserUnitProgress.user_id == current_user["id"],
            UserUnitProgress.unit_id == unit_id
        )
        progress_result = await db.execute(progress_query)
        user_progress = progress_result.scalar_one_or_none()
    
    # Get lessons with progress
    lessons_data = []
    for lesson in unit.lessons:
        lesson_dict = {
            "id": lesson.id,
            "title": lesson.title,
            "description": lesson.description,
            "order_index": lesson.order_index,
            "created_at": lesson.created_at,
            "questions_count": len(lesson.questions) if lesson.questions else 0,
            "exercises_count": len(lesson.exercises) if lesson.exercises else 0
        }
        
        if current_user:
            lesson_progress_query = select(UserLessonProgress).filter(
                UserLessonProgress.user_id == current_user["id"],
                UserLessonProgress.lesson_id == lesson.id
            )
            lesson_progress_result = await db.execute(lesson_progress_query)
            lesson_progress = lesson_progress_result.scalar_one_or_none()
            lesson_dict["progress"] = _convert_user_lesson_progress_to_dict(lesson_progress)
        
        lessons_data.append(lesson_dict)
    
    # Format final quiz info
    final_quiz_info = None
    if unit.final_quiz:
        final_quiz_info = {
            "id": unit.final_quiz.id,
            "title": unit.final_quiz.title,
            "description": unit.final_quiz.description,
            "type": unit.final_quiz.type,
            "order_index": unit.final_quiz.order_index
        }
    
    return {
        "id": unit.id,
        "course_id": unit.course_id,
        "title": unit.title,
        "description": unit.description,
        "order_index": unit.order_index,
        "created_at": unit.created_at,
        "lessons": lessons_data,
        "final_quiz": final_quiz_info,
        "progress": _convert_user_unit_progress_to_dict(user_progress)
    }


@router.get("/units/{unit_id}/final-quiz", response_model=dict)
async def get_unit_final_quiz(
    request: Request,
    unit_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get final quiz for a unit with questions"""
    # Get unit with final quiz and questions
    unit_query = select(Unit).options(
        selectinload(Unit.final_quiz).selectinload(FinalQuiz.questions).selectinload(
            # Note: FinalQuiz.questions relationship should exist
        )
    ).filter(Unit.id == unit_id)
    unit_result = await db.execute(unit_query)
    unit = unit_result.scalar_one_or_none()
    
    if not unit:
        raise NotFoundException("Unit not found")
    
    if not unit.final_quiz:
        raise NotFoundException("Final quiz not found for this unit")
    
    # Get questions for this final quiz
    from ...models.quiz import Question, QuestionOption
    questions_query = select(Question).options(
        selectinload(Question.options),
        selectinload(Question.question_type)
    ).filter(
        Question.quiz_id == unit.final_quiz.id
    ).order_by(Question.order_index)
    questions_result = await db.execute(questions_query)
    questions = questions_result.scalars().all()
    
    # Format questions
    questions_data = []
    for question in questions:
        question_dict = {
            "id": question.id,
            "content": question.content,
            "audio_url": question.audio_url,
            "image_url": question.image_url,
            "explanation": question.explanation,
            "order_index": question.order_index,
            "options": [
                {
                    "id": opt.id,
                    "option_text": opt.option_text,
                    "is_correct": opt.is_correct,
                    "order_index": opt.order_index
                }
                for opt in question.options
            ]
        }
        questions_data.append(question_dict)
    
    return {
        "id": unit.final_quiz.id,
        "unit_id": unit_id,
        "title": unit.final_quiz.title,
        "description": unit.final_quiz.description,
        "type": unit.final_quiz.type,
        "order_index": unit.final_quiz.order_index,
        "created_at": unit.final_quiz.created_at,
        "questions": questions_data
    }


# ============================================================================
# 3. LESSON LEVEL APIs
# ============================================================================

@router.get("/lessons/{lesson_id}", response_model=dict)
async def get_lesson(
    request: Request,
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get a specific lesson with questions + exercises"""
    # Get lesson with questions and exercises
    from ...models.quiz import Question, QuestionOption
    lesson_query = select(Lesson).options(
        selectinload(Lesson.questions).selectinload(Question.options),
        selectinload(Lesson.exercises)
    ).filter(Lesson.id == lesson_id)
    lesson_result = await db.execute(lesson_query)
    lesson = lesson_result.scalar_one_or_none()
    
    if not lesson:
        raise NotFoundException("Lesson not found")
    
    # Get user progress
    user_progress = None
    if current_user:
        progress_query = select(UserLessonProgress).filter(
            UserLessonProgress.user_id == current_user["id"],
            UserLessonProgress.lesson_id == lesson_id
        )
        progress_result = await db.execute(progress_query)
        user_progress = progress_result.scalar_one_or_none()
    
    # Format questions
    questions_data = []
    if lesson.questions:
        for question in lesson.questions:
            # Use options already loaded by selectinload
            question_dict = {
                "id": question.id,
                "content": question.content,
                "audio_url": question.audio_url,
                "image_url": question.image_url,
                "explanation": question.explanation,
                "order_index": question.order_index,
                "question_type": question.question_type,
                "options": [
                    {
                        "id": opt.id,
                        "option_text": opt.option_text,
                        "is_correct": opt.is_correct,
                        "order_index": opt.order_index
                    }
                    for opt in question.options  # Use pre-loaded options
                ]
            }
            questions_data.append(question_dict)
    
    # Format exercises
    exercises_data = []
    if lesson.exercises:
        for exercise in lesson.exercises:
            exercise_dict = {
                "id": exercise.id,
                "type": exercise.type,
                "title": exercise.title,
                "content": exercise.content,
                "audio_url": exercise.audio_url,
                "transcript": exercise.transcript,
                "prompt": exercise.prompt,
                "sample_answer": exercise.sample_answer,
                "order_index": exercise.order_index,
                "created_at": exercise.created_at
            }
            exercises_data.append(exercise_dict)
    
    return {
        "id": lesson.id,
        "unit_id": lesson.unit_id,
        "title": lesson.title,
        "description": lesson.description,
        "order_index": lesson.order_index,
        "created_at": lesson.created_at,
        "questions": questions_data,
        "exercises": exercises_data,
        "progress": _convert_user_lesson_progress_to_dict(user_progress)
    }


@router.get("/lessons/{lesson_id}/questions", response_model=dict)
async def get_lesson_questions(
    request: Request,
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get all practice questions in lesson"""
    from ...models.quiz import Question, QuestionOption
    
    # Get lesson
    lesson_query = select(Lesson).filter(Lesson.id == lesson_id)
    lesson_result = await db.execute(lesson_query)
    lesson = lesson_result.scalar_one_or_none()
    
    if not lesson:
        raise NotFoundException("Lesson not found")
    
    # Get questions for this lesson
    questions_query = select(Question).options(
        selectinload(Question.options)
    ).filter(
        Question.lesson_id == lesson_id
    ).order_by(Question.order_index)
    questions_result = await db.execute(questions_query)
    questions = questions_result.scalars().all()
    
    # Format questions
    questions_data = []
    for question in questions:
        question_dict = {
            "id": question.id,
            "content": question.content,
            "audio_url": question.audio_url,
            "image_url": question.image_url,
            "explanation": question.explanation,
            "order_index": question.order_index,
            "question_type": question.question_type,
            "options": [
                {
                    "id": opt.id,
                    "option_text": opt.option_text,
                    "is_correct": opt.is_correct,
                    "order_index": opt.order_index
                }
                for opt in question.options
            ]
        }
        questions_data.append(question_dict)
    
    return {
        "lesson_id": lesson_id,
        "questions": questions_data,
        "total": len(questions_data)
    }


@router.get("/lessons/{lesson_id}/exercises", response_model=dict)
async def get_lesson_exercises(
    request: Request,
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get all exercises (listening, speaking, writing) for a lesson"""
    # Get lesson
    lesson_query = select(Lesson).filter(Lesson.id == lesson_id)
    lesson_result = await db.execute(lesson_query)
    lesson = lesson_result.scalar_one_or_none()
    
    if not lesson:
        raise NotFoundException("Lesson not found")
    
    # Get exercises for this lesson
    exercises_query = select(Exercise).filter(
        Exercise.lesson_id == lesson_id
    ).order_by(Exercise.order_index)
    exercises_result = await db.execute(exercises_query)
    exercises = exercises_result.scalars().all()
    
    # Format exercises by type
    exercises_data = {
        "listening": [],
        "speaking": [],
        "writing": []
    }
    
    for exercise in exercises:
        exercise_dict = {
            "id": exercise.id,
            "type": exercise.type,
            "title": exercise.title,
            "content": exercise.content,
            "audio_url": exercise.audio_url,
            "transcript": exercise.transcript,
            "prompt": exercise.prompt,
            "sample_answer": exercise.sample_answer,
            "order_index": exercise.order_index,
            "created_at": exercise.created_at
        }
        
        exercises_data[exercise.type].append(exercise_dict)
    
    return {
        "lesson_id": lesson_id,
        "exercises": exercises_data,
        "total": len(exercises)
    }


# ============================================================================
# PROGRESS TRACKING ENDPOINTS
# ============================================================================

@router.post("/lessons/{lesson_id}/progress/update", response_model=dict)
async def update_lesson_progress_endpoint(
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Update progress for lesson, unit, and course after lesson activity"""
    
    user_id = current_user["id"]
    
    # Update all progress (lesson -> unit -> course)
    result = await ProgressTrackingCRUD.update_all_progress(
        db, user_id, lesson_id
    )
    
    return {
        "message": "Progress updated successfully",
        "lesson_progress": result.get("lesson_progress"),
        "unit_progress": result.get("unit_progress"),
        "course_progress": result.get("course_progress")
    }


@router.get("/lessons/{lesson_id}/progress", response_model=dict)
async def get_lesson_progress(
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get progress for a lesson"""
    
    user_id = current_user["id"]
    
    # Calculate current progress
    progress_percent = await ProgressTrackingCRUD.calculate_lesson_progress(
        db, user_id, lesson_id
    )
    
    # Get or create progress record
    progress = await ProgressTrackingCRUD.update_lesson_progress(
        db, user_id, lesson_id, progress_percent
    )
    
    return {
        "lesson_id": lesson_id,
        "progress_percent": progress.progress_percent,
        "is_completed": progress.is_completed,
        "completed_at": progress.completed_at
    }


@router.get("/units/{unit_id}/progress", response_model=dict)
async def get_unit_progress(
    unit_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get progress for a unit"""
    
    user_id = current_user["id"]
    
    # Calculate current progress
    progress_percent = await ProgressTrackingCRUD.calculate_unit_progress(
        db, user_id, unit_id
    )
    
    # Get or create progress record
    progress = await ProgressTrackingCRUD.update_unit_progress(
        db, user_id, unit_id, progress_percent
    )
    
    return {
        "unit_id": unit_id,
        "progress_percent": progress.progress_percent,
        "is_completed": progress.is_completed,
        "completed_at": progress.completed_at
    }


@router.get("/courses/{course_id}/progress", response_model=dict)
async def get_course_progress(
    course_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get progress for a course"""
    
    user_id = current_user["id"]
    
    # Calculate current progress
    progress_percent = await ProgressTrackingCRUD.calculate_course_progress(
        db, user_id, course_id
    )
    
    # Get or create progress record
    progress = await ProgressTrackingCRUD.update_course_progress(
        db, user_id, course_id, progress_percent
    )
    
    return {
        "course_id": course_id,
        "progress_percent": progress.progress_percent,
        "is_completed": progress.is_completed,
        "completed_at": progress.completed_at
    }