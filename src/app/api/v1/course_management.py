# src/app/api/v1/course_management.py
import random
from collections import defaultdict
from datetime import datetime, UTC, date
from fastapi import APIRouter, Depends, Request
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from typing import Annotated, Optional, Tuple, Any
from uuid import UUID
from pydantic import BaseModel, Field

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException
from ...crud.progress_tracking import ProgressTrackingCRUD, LessonExpBreakdown
from ...models.course import Course, Lesson, Unit
from ...models.exercise import Exercise, ExerciseQuestion
from ...models.progress import UserCourseProgress, UserUnitProgress, UserLessonProgress
from ...models.question import Question
from ...models.question_type import QuestionType
from ...models.user import User

router = APIRouter(tags=["courses-units-lessons"])


# ============================================================================
# REQUEST MODELS
# ============================================================================


class LessonProgressUpdateRequest(BaseModel):
    question_exp: int = Field(0, ge=0)
    listening_exp: int = Field(0, ge=0)
    speaking_exp: int = Field(0, ge=0)
    writing_exp: int = Field(0, ge=0)


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


def _get_question_media_url(question: Question, media_key: str) -> Optional[str]:
    """Safely extract media URLs from question object supporting legacy fields."""
    # Legacy direct attribute support (e.g., question.audio_url)
    direct_attr = getattr(question, f"{media_key}_url", None)
    if direct_attr:
        return direct_attr
    media = getattr(question, "media", None)
    if isinstance(media, dict):
        candidate_keys = (
            media_key,
            f"{media_key}_url",
            f"{media_key}Url",
            f"{media_key.upper()}_URL"
        )
        for key in candidate_keys:
            value = media.get(key)
            if value:
                return value
    return None


async def _update_user_streak_if_needed(
    db: AsyncSession,
    user_id: UUID,
    user: User
) -> Tuple[bool, int]:
    """
    Update user streak if they have activity today and haven't updated streak yet.
    
    Returns:
        Tuple of (streak_updated: bool, streak_bonus_exp: int)
    """
    from ...models.gamification import UserExpLog
    
    today = date.today()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=UTC)
    today_end = datetime.combine(today, datetime.max.time()).replace(tzinfo=UTC)
    
    # Check if user has any exp logs today (any activity)
    today_exp_logs_query = select(func.count()).select_from(UserExpLog).where(
        and_(
            UserExpLog.user_id == user_id,
            UserExpLog.created_at >= today_start,
            UserExpLog.created_at < today_end
        )
    )
    today_exp_logs_result = await db.execute(today_exp_logs_query)
    today_exp_logs_count = today_exp_logs_result.scalar() or 0
    
    # Check if streak was already updated today (by checking streak_bonus logs today)
    streak_updated_today_query = select(func.count()).select_from(UserExpLog).where(
        and_(
            UserExpLog.user_id == user_id,
            UserExpLog.source == "streak_bonus",
            UserExpLog.created_at >= today_start,
            UserExpLog.created_at < today_end
        )
    )
    streak_updated_today_result = await db.execute(streak_updated_today_query)
    streak_already_updated = (streak_updated_today_result.scalar() or 0) > 0
    
    # Only update streak if:
    # 1. User has activity today (exp logs exist)
    # 2. Streak hasn't been updated today yet
    if today_exp_logs_count > 0 and not streak_already_updated:
        # Increment streak
        user.streak_days += 1
        
        # Calculate streak bonus EXP (min of streak_days * 5, max 50)
        streak_bonus = min(user.streak_days * 5, 50)
        
        if streak_bonus > 0:
            # Add streak bonus to user exp
            user.exp += streak_bonus
            
            # Log streak bonus
            streak_exp_log = UserExpLog(
                user_id=user_id,
                source="streak_bonus",
                amount=streak_bonus
            )
            db.add(streak_exp_log)
            
            return True, streak_bonus
    
    return False, 0


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
    user_uuid = UUID(str(current_user["id"])) if current_user else None
    user_progress = {}
    if user_uuid:
        progress_query = select(UserCourseProgress).where(
            UserCourseProgress.user_id == user_uuid
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
    user_uuid = UUID(str(current_user["id"])) if current_user else None
    user_progress = None
    if user_uuid:
        progress_query = select(UserCourseProgress).filter(
            UserCourseProgress.user_id == user_uuid,
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
        if user_uuid:
            unit_progress_query = select(UserUnitProgress).filter(
                UserUnitProgress.user_id == user_uuid,
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
    user_uuid = UUID(str(current_user["id"])) if current_user else None
    user_progress = None
    if user_uuid:
        progress_query = select(UserUnitProgress).filter(
            UserUnitProgress.user_id == user_uuid,
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
        
        if user_uuid:
            lesson_progress_query = select(UserLessonProgress).filter(
                UserLessonProgress.user_id == user_uuid,
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
    user_uuid = UUID(str(current_user["id"])) if current_user else None
    user_progress = None
    if user_uuid:
        progress_query = select(UserLessonProgress).filter(
            UserLessonProgress.user_id == user_uuid,
            UserLessonProgress.lesson_id == lesson_id
        )
        progress_result = await db.execute(progress_query)
        user_progress = progress_result.scalar_one_or_none()
    
    # Get 13 random questions for this lesson
    # Strategy: Get random 13, then ensure we have at least 1 from each question_type_id
    
    # Step 0: Get all available question type UUIDs from database
    question_types_query = select(QuestionType.id)
    question_types_result = await db.execute(question_types_query)
    all_question_type_ids = {row[0] for row in question_types_result.fetchall()}
    
    # Step 1: Get 13 random questions
    questions_query = select(Question).options(
        selectinload(Question.options),
        selectinload(Question.matching_pairs),
        selectinload(Question.sentence_order),
        selectinload(Question.audio_comprehension),
        selectinload(Question.pronunciation),
        selectinload(Question.blanks),
        selectinload(Question.question_type_relation)
    ).filter(
        Question.lesson_id == lesson_id
    ).order_by(func.random()).limit(13)
    questions_result = await db.execute(questions_query)
    selected_questions = list(questions_result.scalars().all())
    
    # Step 2: Check which question_type_ids we have
    type_ids_present = {q.question_type_id for q in selected_questions}
    missing_types = all_question_type_ids - type_ids_present
    
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
            # Fix: Only add NOT IN clause if existing_ids is not empty
            type_query = select(Question).options(
                selectinload(Question.options),
                selectinload(Question.matching_pairs),
                selectinload(Question.sentence_order),
                selectinload(Question.audio_comprehension),
                selectinload(Question.pronunciation),
                selectinload(Question.blanks),
                selectinload(Question.question_type_relation)
            ).filter(
                Question.lesson_id == lesson_id,
                Question.question_type_id == question_type_id
            )
            
            # Only add NOT IN filter if we have existing IDs to exclude
            if existing_ids:
                type_query = type_query.filter(~Question.id.in_(existing_ids))
            
            type_query = type_query.order_by(func.random()).limit(1)
            
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
        audio_url = _get_question_media_url(question, "audio")
        image_url = _get_question_media_url(question, "image")
        question_type_value = (
            question.question_type_relation.code
            if getattr(question, "question_type_relation", None)
            else getattr(question, "question_type", None)
        )
        question_dict = {
            "id": question.id,
            "content": question.content,
            "audio_url": audio_url,
            "image_url": image_url,
            "explanation": question.explanation,
            "question_metadata": question.question_metadata,
            "order_index": question.order_index,
            "question_type": question_type_value,
            "question_type_id": question.question_type_id,
            "options": [
                {
                    "id": opt.id,
                    "option_text": opt.option_text,
                    "is_correct": opt.is_correct
                }
                for opt in question.options
            ],
            "matching_pairs": [
                {
                    "id": pair.id,
                    "left_text": pair.left_text,
                    "left_media": pair.left_media,
                    "right_text": pair.right_text,
                    "right_media": pair.right_media,
                    "sort_order": pair.sort_order
                }
                for pair in question.matching_pairs or []
            ],
            "sentence_order": (
                {
                    "id": question.sentence_order.id,
                    "correct_sequence": question.sentence_order.correct_sequence
                }
                if question.sentence_order else None
            ),
            "audio_comprehension": (
                {
                    "id": question.audio_comprehension.id,
                    "transcript": question.audio_comprehension.transcript,
                    "tts_config": question.audio_comprehension.tts_config
                }
                if question.audio_comprehension else None
            ),
            "pronunciation": (
                {
                    "id": question.pronunciation.id,
                    "target_phrase": question.pronunciation.target_phrase,
                    "reference_audio_url": question.pronunciation.reference_audio_url,
                    "tts_config": question.pronunciation.tts_config
                }
                if question.pronunciation else None
            ),
            "blank": (
                {
                    "id": question.blanks.id,
                    "correct_answer": question.blanks.correct_answer,
                    "case_sensitive": question.blanks.case_sensitive
                }
                if question.blanks else None
            )
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
    
    # Calculate exp info (configurable)
    total_questions_result = await db.execute(
        select(func.count()).select_from(Question).where(Question.lesson_id == lesson_id)
    )
    total_questions = total_questions_result.scalar() or 0
    
    max_exp_for_lesson = lesson.max_exp or 120  # Default fallback
    exp_per_question = max_exp_for_lesson / total_questions if total_questions > 0 else 0
    
    exp_info = {
        "max_exp": max_exp_for_lesson,  # Total exp for completing all questions
        "exp_per_question": int(exp_per_question),  # Exp per correct answer
        "total_questions": total_questions  # Total questions in lesson
    }
    
    return {
        "id": lesson.id,
        "unit_id": lesson.unit_id,
        "title": lesson.title,
        "description": lesson.description,
        "order_index": lesson.order_index,
        "created_at": lesson.created_at,
        "questions": questions_data,
        "exercises": exercises_data,
        "progress": _convert_user_lesson_progress_to_dict(user_progress),
        "exp_info": exp_info  # Add exp_info for FE to calculate exp_per_question
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
        selectinload(Question.options),
        selectinload(Question.matching_pairs),
        selectinload(Question.sentence_order),
        selectinload(Question.audio_comprehension),
        selectinload(Question.pronunciation),
        selectinload(Question.blanks),
        selectinload(Question.question_type_relation)
    ).filter(
        Question.lesson_id == lesson_id
    ).order_by(Question.order_index)
    questions_result = await db.execute(questions_query)
    questions = questions_result.scalars().all()
    
    # Format questions
    questions_data = []
    for question in questions:
        audio_url = _get_question_media_url(question, "audio")
        image_url = _get_question_media_url(question, "image")
        question_type_value = (
            question.question_type_relation.code
            if getattr(question, "question_type_relation", None)
            else getattr(question, "question_type", None)
        )
        question_dict = {
            "id": question.id,
            "content": question.content,
            "audio_url": audio_url,
            "image_url": image_url,
            "explanation": question.explanation,
            "question_metadata": question.question_metadata,
            "order_index": question.order_index,
            "question_type": question_type_value,
            "options": [
                {
                    "id": opt.id,
                    "option_text": opt.option_text,
                    "is_correct": opt.is_correct,
                    "order_index": opt.order_index
                }
                for opt in question.options
            ],
            "matching_pairs": [
                {
                    "id": pair.id,
                    "left_text": pair.left_text,
                    "left_media": pair.left_media,
                    "right_text": pair.right_text,
                    "right_media": pair.right_media,
                    "sort_order": pair.sort_order
                }
                for pair in question.matching_pairs or []
            ],
            "sentence_order": (
                {
                    "id": question.sentence_order.id,
                    "correct_sequence": question.sentence_order.correct_sequence
                }
                if question.sentence_order else None
            ),
            "audio_comprehension": (
                {
                    "id": question.audio_comprehension.id,
                    "transcript": question.audio_comprehension.transcript,
                    "tts_config": question.audio_comprehension.tts_config
                }
                if question.audio_comprehension else None
            ),
            "pronunciation": (
                {
                    "id": question.pronunciation.id,
                    "target_phrase": question.pronunciation.target_phrase,
                    "reference_audio_url": question.pronunciation.reference_audio_url,
                    "tts_config": question.pronunciation.tts_config
                }
                if question.pronunciation else None
            ),
            "blank": (
                {
                    "id": question.blanks.id,
                    "correct_answer": question.blanks.correct_answer,
                    "case_sensitive": question.blanks.case_sensitive
                }
                if question.blanks else None
            )
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


def _check_answer_correctness(question: Question, request: dict) -> tuple[bool, str, Any | None]:
    """Check if user's answer is correct based on request payload.
    
    Returns:
        Tuple of (is_correct: bool, user_answer_str: str, correct_answer: Any | None)
    """
    is_correct = False
    user_answer_str = ""
    correct_answer_payload: Any | None = None
    
    question_type_code = (
        question.question_type_relation.code.upper()
        if getattr(question, "question_type_relation", None) and question.question_type_relation.code
        else None
    )
    
    selected_option_id = request.get("selected_option_id")
    if selected_option_id is not None:
        # Handle option-based answer submissions
        selected_option = next(
            (opt for opt in question.options if str(opt.id) == str(selected_option_id)), None
        )
        
        if question_type_code == "BLANK":
            correct_text = question.blanks.correct_answer if question.blanks else None
            correct_answer_payload = correct_text
            user_answer_str = selected_option.option_text if selected_option and selected_option.option_text else ""
            
            if correct_text is None:
                is_correct = False
            else:
                if question.blanks and question.blanks.case_sensitive:
                    is_correct = user_answer_str.strip() == correct_text.strip()
                else:
                    is_correct = user_answer_str.strip().lower() == correct_text.strip().lower()
        else:
            if selected_option:
                is_correct = bool(selected_option.is_correct)
                user_answer_str = selected_option.option_text
            
            correct_option_texts = [
                opt.option_text for opt in question.options if opt.is_correct and opt.option_text
            ]
            if correct_option_texts:
                correct_answer_payload = ", ".join(correct_option_texts)
            else:
                # Fallback to IDs if texts missing
                correct_answer_payload = [
                    opt.id for opt in question.options if opt.is_correct
                ]
    elif "answer" in request:
        # Text-based answer
        user_answer_str = str(request.get("answer", "")).strip()
        
        if question_type_code == "BLANK" and question.blanks:
            correct_text = question.blanks.correct_answer or ""
            correct_answer_payload = correct_text
            if question.blanks.case_sensitive:
                is_correct = user_answer_str == correct_text.strip()
            else:
                is_correct = user_answer_str.lower() == correct_text.strip().lower()
        else:
            # Attempt to pull correct answer from metadata for legacy questions
            if isinstance(question.question_metadata, dict):
                metadata_correct = question.question_metadata.get("correct_answer")
                if metadata_correct is not None:
                    correct_answer_payload = metadata_correct
                    if isinstance(metadata_correct, str):
                        is_correct = user_answer_str.lower() == metadata_correct.strip().lower()
                    elif isinstance(metadata_correct, list):
                        normalized = [str(item).strip().lower() for item in metadata_correct]
                        is_correct = user_answer_str.lower() in normalized
    
    return is_correct, user_answer_str, correct_answer_payload
    

@router.post("/lessons/{lesson_id}/practice-questions/{question_id}/submit", response_model=dict)
async def submit_practice_question_answer(
    lesson_id: UUID,
    question_id: UUID,
    request: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Submit answer for a practice question in a lesson
    
    Request body should include:
    - answer data (selected_option_id or answer)
    - exp_earned (optional, calculated by FE from exp_info.exp_per_question)
    """
    user_id = UUID(str(current_user["id"]))
    
    # Get exp_earned from request (sent by FE, calculated from exp_info.exp_per_question)
    exp_earned = request.get("exp_earned", 0)

    # Ensure lesson exists (also used for max_exp)
    lesson_query = select(Lesson).filter(Lesson.id == lesson_id)
    lesson_result = await db.execute(lesson_query)
    lesson = lesson_result.scalar_one_or_none()
    if not lesson:
        raise NotFoundException("Lesson not found")
    
    # Get question and verify it belongs to lesson
    question_query = select(Question).options(
        selectinload(Question.options),
        selectinload(Question.blanks),
        selectinload(Question.sentence_order),
        selectinload(Question.matching_pairs),
        selectinload(Question.question_type_relation)
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
    is_correct, user_answer_str, correct_answer_payload = _check_answer_correctness(question, request)
    
    # Save user answer
    from ...models.user_answer import UserAnswer
    user_answer = UserAnswer(
        user_id=user_id,
        question_id=question_id,
        answer=request,
        is_correct=is_correct,
        score=1.0 if is_correct else 0.0
    )
    db.add(user_answer)
    await db.flush()  # Get the ID for user_answer
    
    # ============================================================
    # CỘNG EXP CHO USER VÀ UPDATE STREAK
    # ============================================================
    actual_exp_earned = 0
    streak_updated = False
    streak_bonus_exp = 0
    
    if is_correct and exp_earned > 0:
        # Check if user already answered this question correctly before
        previous_answer_query = select(UserAnswer).filter(
            and_(
                UserAnswer.user_id == user_id,
                UserAnswer.question_id == question_id,
                UserAnswer.is_correct == True,
                UserAnswer.id != user_answer.id  # Exclude current answer
            )
        ).order_by(UserAnswer.answered_at.desc()).limit(1)
        previous_answer_result = await db.execute(previous_answer_query)
        previous_correct_answer = previous_answer_result.scalar_one_or_none()
        
        # Only award exp if this is first time answering correctly
        if not previous_correct_answer:
            # Validate exp_earned is reasonable
            total_questions_result = await db.execute(
                select(func.count()).select_from(Question).where(Question.lesson_id == lesson_id)
            )
            total_questions = total_questions_result.scalar() or 0
            
            max_exp_for_lesson = lesson.max_exp or 120
            max_exp_per_question = max_exp_for_lesson / total_questions if total_questions > 0 else 0
            
            # Validate: exp_earned should not exceed max_exp_per_question
            if exp_earned <= max_exp_per_question:
                actual_exp_earned = int(exp_earned)
                
                # Get user from database
                from ...models.gamification import UserExpLog
                
                user_query = select(User).filter(User.id == user_id)
                user_result = await db.execute(user_query)
                user = user_result.scalar_one_or_none()
                
                if user:
                    # 1. Cộng exp từ question vào user.exp
                    user.exp += actual_exp_earned
                    
                    # 2. Tạo log để track exp gain từ question
                    exp_log = UserExpLog(
                        user_id=user_id,
                        source="question_completed",
                        amount=actual_exp_earned
                    )
                    db.add(exp_log)
                    
                    # 3. TRIGGER STREAK UPDATE (chỉ update 1 lần mỗi ngày)
                    streak_updated, streak_bonus_exp = await _update_user_streak_if_needed(
                        db, user_id, user
                    )
            else:
                # Log warning if FE sent invalid exp
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(
                    f"Invalid exp_earned from FE: {exp_earned} (max allowed: {max_exp_per_question}) "
                    f"for user {user_id}, question {question_id}"
                )
    
    # If correct, increment completed_questions_count
    if is_correct:
        await _increment_lesson_progress(db, user_id, lesson_id)
    
    # Commit all changes (user_answer, user.exp, exp_logs, streak)
    await db.commit()
    
    # Get updated user info for response
    user_query = select(User).filter(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    current_streak = user.streak_days if user else 0
    
    return {
        "is_correct": is_correct,
        "correct_answer": correct_answer_payload,
        "explanation": question.explanation,
        "message": "Answer submitted successfully",
        "exp_earned": actual_exp_earned,  # Exp from question (0 if invalid or already earned)
        "streak_info": {
            "streak_updated": streak_updated,  # Whether streak was updated this time
            "current_streak": current_streak,  # Current streak days
            "streak_bonus_exp": streak_bonus_exp  # Bonus exp from streak (if updated)
        },
        "lesson_progress": None
    }


@router.post("/lessons/{lesson_id}/progress/update", response_model=dict)
async def update_lesson_progress_endpoint(
    lesson_id: UUID,
    payload: LessonProgressUpdateRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Update progress for lesson, unit, and course after lesson activity"""
    user_id = UUID(str(current_user["id"]))
    
    exp_breakdown = LessonExpBreakdown(
        question_exp=payload.question_exp,
        listening_exp=payload.listening_exp,
        speaking_exp=payload.speaking_exp,
        writing_exp=payload.writing_exp
    )
    
    # Update all progress (lesson -> unit -> course)
    result = await ProgressTrackingCRUD.update_all_progress(
        db, user_id, lesson_id, exp_breakdown=exp_breakdown
    )
    
    lesson_progress = result.get("lesson_progress")
    unit_progress = result.get("unit_progress")
    course_progress = result.get("course_progress")
    
    streak_info = {
        "streak_updated": False,
        "current_streak": 0,
        "streak_bonus_exp": 0
    }
    
    if lesson_progress and lesson_progress.progress_percent >= 80.0:
        user_query = select(User).filter(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        if user:
            streak_updated, streak_bonus = await _update_user_streak_if_needed(db, user_id, user)
            await db.commit()
            await db.refresh(user)
            streak_info = {
                "streak_updated": streak_updated,
                "current_streak": user.streak_days,
                "streak_bonus_exp": streak_bonus
            }
    
    return {
        "message": "Progress updated successfully",
        "lesson_progress": _convert_user_lesson_progress_to_dict(lesson_progress),
        "unit_progress": _convert_user_unit_progress_to_dict(unit_progress),
        "course_progress": _convert_user_course_progress_to_dict(course_progress),
        "streak_info": streak_info
    }


@router.get("/lessons/{lesson_id}/progress", response_model=dict)
async def get_lesson_progress(
    lesson_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get progress for a lesson"""
    user_id = UUID(str(current_user["id"]))
    
    # Calculate current progress
    progress_computation = await ProgressTrackingCRUD.calculate_lesson_progress(
        db, user_id, lesson_id
    )
    
    # Get or create progress record
    progress = await ProgressTrackingCRUD.update_lesson_progress(
        db, user_id, lesson_id, precomputed=progress_computation
    )
    
    return {
        "lesson_id": lesson_id,
        "progress_percent": int(progress.progress_percent),
        "is_completed": progress.is_completed,
        "completed_at": progress.completed_at
    }


@router.get("/units/{unit_id}/progress", response_model=dict)
async def get_unit_progress(
    unit_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get progress for a unit"""
    user_id = UUID(str(current_user["id"]))
    
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
    course_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get progress for a course"""
    user_id = UUID(str(current_user["id"]))
    
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
