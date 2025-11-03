# src/app/api/v1/course_management.py
from typing import Annotated, Optional
from uuid import UUID
from datetime import datetime, UTC
import random
from collections import defaultdict

from fastapi import APIRouter, Depends, Request
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException
from ...models.course import Course, Lesson, Unit
from ...models.progress import UserCourseProgress, UserUnitProgress, UserLessonProgress
from ...models.exercise import Exercise, ExerciseQuestion, ExerciseQuestionOption
from ...models.question import Question
from ...models.question_option import QuestionOption
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
        "started_at": progress.started_at.isoformat() if progress.started_at else None,
        "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
        "progress_percent": int(progress.progress_percent),
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
        "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
        "progress_percent": int(progress.progress_percent),
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
        "completed_at": progress.completed_at.isoformat() if progress.completed_at else None,
        "progress_percent": int(progress.progress_percent),
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
            "image_url": course.image_url,
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
    course_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get a specific course with units list"""
    # Get course with units
    course_query = select(Course).options(
        selectinload(Course.units).selectinload(Unit.lessons)
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
            "lessons_count": len(unit.lessons)
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
        "image_url": course.image_url,
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
    unit_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get a specific unit with lessons list"""
    # Get unit with lessons
    unit_query = select(Unit).options(
        selectinload(Unit.lessons).selectinload(Lesson.questions),
        selectinload(Unit.lessons).selectinload(Lesson.exercises)
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
    
    return {
        "id": unit.id,
        "course_id": unit.course_id,
        "title": unit.title,
        "description": unit.description,
        "order_index": unit.order_index,
        "created_at": unit.created_at,
        "lessons": lessons_data,
        "progress": _convert_user_unit_progress_to_dict(user_progress)
    }


# ============================================================================
# 3. LESSON LEVEL APIs
# ============================================================================

@router.get("/lessons/{lesson_id}", response_model=dict)
async def get_lesson(
    request: Request,
    lesson_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get a specific lesson with 13 random questions + exercises"""
    lesson_query = select(Lesson).options(
        selectinload(Lesson.exercises).selectinload(Exercise.questions).selectinload(ExerciseQuestion.options)
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
    
    # Get 13 random questions for this lesson
    # Strategy: Get random 13, then ensure we have at least 1 from each question_type_id (1-8)
    
    # Step 1: Get 13 random questions
    questions_query = select(Question).options(
        selectinload(Question.options)
    ).filter(
        Question.lesson_id == lesson_id
    ).order_by(func.random()).limit(13)
    questions_result = await db.execute(questions_query)
    selected_questions = list(questions_result.scalars().all())
    
    # Step 2: Check which question_type_ids we have
    type_ids_present = {q.question_type_id for q in selected_questions}
    missing_types = set(range(1, 9)) - type_ids_present
    
    # Step 3: If missing any types, try to get at least 1 from each missing type
    if missing_types:
        # Get existing question IDs to avoid duplicates
        existing_ids = {q.id for q in selected_questions}
        
        for question_type_id in missing_types:
            # Recalculate type counts from current selected_questions
            type_counts = defaultdict(int)
            for q in selected_questions:
                type_counts[q.question_type_id] += 1
            
            # Try to get 1 question of this type
            type_query = select(Question).options(
                selectinload(Question.options)
            ).filter(
                Question.lesson_id == lesson_id,
                Question.question_type_id == question_type_id,
                ~Question.id.in_(existing_ids)
            ).order_by(func.random()).limit(1)
            
            type_result = await db.execute(type_query)
            question = type_result.scalar_one_or_none()
            
            if question:
                # Replace one question (preferably from a type we have multiple of)
                # Find a type that has multiple questions to remove one
                if type_counts:
                    # Find type with most questions (but not the one we're trying to add)
                    type_to_replace = max(
                        [(tid, count) for tid, count in type_counts.items() if tid != question_type_id],
                        key=lambda x: x[1],
                        default=None
                    )
                    
                    if type_to_replace and type_to_replace[1] > 1:
                        type_id_to_remove = type_to_replace[0]
                        # Replace first question of this type
                        for i, q in enumerate(selected_questions):
                            if q.question_type_id == type_id_to_remove:
                                existing_ids.remove(q.id)
                                selected_questions[i] = question
                                existing_ids.add(question.id)
                                break
                    # If we can't replace (all types have only 1 question), don't add to keep count at 13
    
    # Step 4: Shuffle for random order
    random.shuffle(selected_questions)
    questions = selected_questions
    
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
            "question_type_id": question.question_type_id,
            "options": [
                {
                    "id": opt.id,
                    "option_text": opt.option_text,
                    "is_correct": opt.is_correct
                }
                for opt in question.options
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
                "text_to_speak": exercise.text_to_speak,
                "transcript": exercise.transcript,
                "prompt": exercise.prompt,
                "sample_answer": exercise.sample_answer,
                "order_index": exercise.order_index,
                "created_at": exercise.created_at.isoformat() if exercise.created_at else None,
                "questions": [
                    {
                        "id": q.id,
                        "exercise_id": q.exercise_id,
                        "question_text": q.question_text,
                        "explanation": q.explanation,
                        "order_index": q.order_index,
                        "created_at": q.created_at.isoformat() if q.created_at else None,
                        "options": [
                            {
                                "id": opt.id,
                                "question_id": opt.question_id,
                                "option_text": opt.option_text,
                                "is_correct": opt.is_correct,
                                "order_index": opt.order_index,
                                "created_at": opt.created_at.isoformat() if opt.created_at else None
                            }
                            for opt in q.options
                        ]
                    }
                    for q in exercise.questions
                ]
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
    lesson_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get all practice questions in lesson"""
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
    lesson_id: UUID,
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

async def _increment_lesson_progress(
    db: AsyncSession,
    user_id: UUID,
    lesson_id: UUID
) -> None:
    """Helper function to increment completed_questions_count for a lesson."""
    # Get or create progress record
    progress_query = select(UserLessonProgress).filter(
        and_(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.lesson_id == lesson_id
        )
    )
    progress_result = await db.execute(progress_query)
    user_progress = progress_result.scalar_one_or_none()
    
    # Count total questions for cap
    total_q_result = await db.execute(
        select(func.count()).select_from(Question).where(Question.lesson_id == lesson_id)
    )
    total_questions = total_q_result.scalar() or 0
    
    if user_progress:
        # Increment but do not exceed total
        if not user_progress.is_completed:
            user_progress.completed_questions_count = min(
                (user_progress.completed_questions_count or 0) + 1,
                total_questions
            )
    else:
        # Create with 1 completed question
        new_progress = UserLessonProgress(
            user_id=user_id,
            lesson_id=lesson_id,
            completed_questions_count=1
        )
        db.add(new_progress)
    
    await db.commit()


async def _increment_exercise_completion(
    db: AsyncSession,
    user_id: UUID,
    lesson_id: UUID
) -> None:
    """Helper function to increment completed_exercises_count for a lesson."""
    # Get or create progress record
    progress_query = select(UserLessonProgress).filter(
        and_(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.lesson_id == lesson_id
        )
    )
    progress_result = await db.execute(progress_query)
    user_progress = progress_result.scalar_one_or_none()
    
    # Count total exercises for cap
    total_e_result = await db.execute(
        select(func.count()).select_from(Exercise).where(Exercise.lesson_id == lesson_id)
    )
    total_exercises = total_e_result.scalar() or 0
    
    if user_progress:
        # Increment but do not exceed total
        if not user_progress.is_completed:
            user_progress.completed_exercises_count = min(
                (user_progress.completed_exercises_count or 0) + 1,
                total_exercises
            )
    else:
        # Create with 1 completed exercise
        new_progress = UserLessonProgress(
            user_id=user_id,
            lesson_id=lesson_id,
            completed_exercises_count=1
        )
        db.add(new_progress)
    
    await db.commit()


def _check_answer_correctness(question: Question, request: dict) -> tuple[bool, str]:
    """Check if user's answer is correct based on request payload.
    
    Returns:
        Tuple of (is_correct: bool, user_answer_str: str)
    """
    is_correct = False
    user_answer_str = ""
    
    selected_option_id = request.get("selected_option_id")
    if selected_option_id is not None:
        # Multiple choice style by explicit selected_option_id
        selected_option = next(
            (opt for opt in question.options if opt.id == selected_option_id), None
        )
        if selected_option:
            is_correct = bool(selected_option.is_correct)
            user_answer_str = selected_option.option_text
    elif "answer" in request and question.correct_answer:
        # Text-based answer
        user_answer_str = str(request.get("answer", "")).strip()
        is_correct = user_answer_str.lower() == question.correct_answer.lower().strip()
    
    return is_correct, user_answer_str


@router.post("/lessons/{lesson_id}/practice-questions/{question_id}/submit", response_model=dict)
async def submit_practice_question_answer(
    lesson_id: UUID,
    question_id: UUID,
    request: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Submit answer for a practice question in a lesson"""
    user_id = current_user["id"]
    
    # Get question and verify it belongs to lesson
    question_query = select(Question).options(
        selectinload(Question.options)
    ).filter(
        and_(
            Question.id == question_id,
            Question.lesson_id == lesson_id
        )
    )
    question_result = await db.execute(question_query)
    question = question_result.scalar_one_or_none()
    
    if not question:
        raise NotFoundException("Question not found or doesn't belong to this lesson")
    
    # Determine if answer is correct
    is_correct, user_answer_str = _check_answer_correctness(question, request)
    
    # If correct, increment completed_questions_count
    if is_correct:
        await _increment_lesson_progress(db, user_id, lesson_id)
    
    # Update lesson/unit/course progress after potential increment
    progress_result = await ProgressTrackingCRUD.update_all_progress(db, user_id, lesson_id)
    lesson_progress_obj = progress_result.get("lesson_progress")
    
    return {
        "is_correct": is_correct,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
        "message": "Answer submitted successfully",
        "lesson_progress": {
            "progress_percent": int(lesson_progress_obj.progress_percent) if lesson_progress_obj else 0
        }
    }


@router.post("/lessons/{lesson_id}/progress/update", response_model=dict)
async def update_lesson_progress_endpoint(
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Update progress for lesson, unit, and course after lesson activity"""
    user_id = current_user["id"]
    
    # Update all progress (lesson -> unit -> course)
    result = await ProgressTrackingCRUD.update_all_progress(db, user_id, lesson_id)
    
    # Convert ORM objects to dictionaries
    lesson_progress = result.get("lesson_progress")
    unit_progress = result.get("unit_progress")
    course_progress = result.get("course_progress")
    
    return {
        "message": "Progress updated successfully",
        "lesson_progress": _convert_user_lesson_progress_to_dict(lesson_progress),
        "unit_progress": _convert_user_unit_progress_to_dict(unit_progress),
        "course_progress": _convert_user_course_progress_to_dict(course_progress)
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
        "progress_percent": int(progress.progress_percent),
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
        "progress_percent": int(progress.progress_percent),
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
        "progress_percent": int(progress.progress_percent),
        "is_completed": progress.is_completed,
        "completed_at": progress.completed_at
    }
