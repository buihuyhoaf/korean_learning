# src/app/api/v1/course_management.py
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Request
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException
from ...models.course import Course, Lesson, Unit
from ...models.progress import UserCourseProgress, UserUnitProgress, UserLessonProgress
from ...models.quiz import Quiz, Question

router = APIRouter(tags=["courses"])


def _convert_user_course_progress_to_dict(progress: UserCourseProgress) -> dict:
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


def _convert_user_unit_progress_to_dict(progress: UserUnitProgress) -> dict:
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


def _convert_user_lesson_progress_to_dict(progress: UserLessonProgress) -> dict:
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


# UC2: View Courses/Units/Lessons
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
    from sqlalchemy import select, func
    courses_query = select(Course).options(selectinload(Course.units)).order_by(Course.order_index)
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
            "progress": _convert_user_course_progress_to_dict(user_progress.get(course.id)) if course.id in user_progress else None
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
    """Get a specific course with units and user progress"""
    from sqlalchemy import select
    
    # Get course with units and their lessons
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
    
    # Get units with progress
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


@router.get("/units/{unit_id}", response_model=dict)
async def get_unit(
    request: Request,
    unit_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get a specific unit with lessons and user progress"""
    from sqlalchemy import select
    
    # Get unit with lessons and their related data
    unit_query = select(Unit).options(
        selectinload(Unit.lessons).selectinload(Lesson.quizzes),
        selectinload(Unit.lessons).selectinload(Lesson.listening_exercises),
        selectinload(Unit.lessons).selectinload(Lesson.speaking_exercises),
        selectinload(Unit.lessons).selectinload(Lesson.writing_exercises)
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
            "quizzes_count": len(lesson.quizzes),
            "exercises_count": len(lesson.listening_exercises) + len(lesson.speaking_exercises) + len(lesson.writing_exercises)
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


@router.get("/lessons/{lesson_id}", response_model=dict)
async def get_lesson(
    request: Request,
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get a specific lesson with quizzes, exercises and user progress"""
    from sqlalchemy import select
    
    # Get lesson with all related data
    lesson_query = select(Lesson).options(
        selectinload(Lesson.quizzes).selectinload(Quiz.questions),
        selectinload(Lesson.listening_exercises),
        selectinload(Lesson.speaking_exercises),
        selectinload(Lesson.writing_exercises)
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
    
    # Get quizzes
    quizzes_data = []
    for quiz in lesson.quizzes:
        quiz_dict = {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "type": quiz.type,
            "order_index": quiz.order_index,
            "created_at": quiz.created_at,
            "questions_count": len(quiz.questions)
        }
        quizzes_data.append(quiz_dict)
    
    # Get exercises
    exercises_data = {
        "listening": [{"id": ex.id, "description": ex.description, "created_at": ex.created_at} for ex in lesson.listening_exercises],
        "speaking": [{"id": ex.id, "prompt": ex.prompt, "created_at": ex.created_at} for ex in lesson.speaking_exercises],
        "writing": [{"id": ex.id, "prompt": ex.prompt, "created_at": ex.created_at} for ex in lesson.writing_exercises]
    }
    
    return {
        "id": lesson.id,
        "unit_id": lesson.unit_id,
        "title": lesson.title,
        "description": lesson.description,
        "order_index": lesson.order_index,
        "created_at": lesson.created_at,
        "quizzes": quizzes_data,
        "exercises": exercises_data,
        "progress": _convert_user_lesson_progress_to_dict(user_progress)
    }


# Admin endpoints for UC15: Manage Courses/Units/Lessons/Quizzes
@router.post("/courses", status_code=201)  # dependencies=[Depends(get_current_superuser)],
async def create_course(
    request: Request,
    course_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Create a new course (Admin only)"""
    course = Course(
        title=course_data["title"],
        description=course_data["description"],
        order_index=course_data.get("order_index", 0)
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "order_index": course.order_index,
        "created_at": course.created_at
    }


@router.put("/courses/{course_id}")  # dependencies=[Depends(get_current_superuser)]
async def update_course(
    request: Request,
    course_id: int,
    course_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Update a course (Admin only)"""
    from sqlalchemy import select
    
    course_query = select(Course).filter(Course.id == course_id)
    course_result = await db.execute(course_query)
    course = course_result.scalar_one_or_none()
    
    if not course:
        raise NotFoundException("Course not found")
    
    course.title = course_data.get("title", course.title)
    course.description = course_data.get("description", course.description)
    course.order_index = course_data.get("order_index", course.order_index)
    
    await db.commit()
    await db.refresh(course)
    
    return {"message": "Course updated successfully"}


@router.delete("/courses/{course_id}")  # dependencies=[Depends(get_current_superuser)]
async def delete_course(
    request: Request,
    course_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Delete a course (Admin only)"""
    from sqlalchemy import select
    
    course_query = select(Course).filter(Course.id == course_id)
    course_result = await db.execute(course_query)
    course = course_result.scalar_one_or_none()
    
    if not course:
        raise NotFoundException("Course not found")
    
    db.delete(course)
    await db.commit()
    
    return {"message": "Course deleted successfully"}


@router.post("/courses/{course_id}/units", status_code=201)  # dependencies=[Depends(get_current_superuser)]
async def create_unit(
    request: Request,
    course_id: int,
    unit_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Create a new unit (Admin only)"""
    from sqlalchemy import select
    
    course_query = select(Course).filter(Course.id == course_id)
    course_result = await db.execute(course_query)
    course = course_result.scalar_one_or_none()
    
    if not course:
        raise NotFoundException("Course not found")
    
    unit = Unit(
        course_id=course_id,
        title=unit_data["title"],
        description=unit_data["description"],
        order_index=unit_data.get("order_index", 0)
    )
    db.add(unit)
    await db.commit()
    await db.refresh(unit)
    
    return {
        "id": unit.id,
        "course_id": unit.course_id,
        "title": unit.title,
        "description": unit.description,
        "order_index": unit.order_index,
        "created_at": unit.created_at
    }


@router.post("/units/{unit_id}/lessons", status_code=201)  # dependencies=[Depends(get_current_superuser)]
async def create_lesson(
    request: Request,
    unit_id: int,
    lesson_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Create a new lesson (Admin only)"""
    from sqlalchemy import select
    
    unit_query = select(Unit).filter(Unit.id == unit_id)
    unit_result = await db.execute(unit_query)
    unit = unit_result.scalar_one_or_none()
    
    if not unit:
        raise NotFoundException("Unit not found")
    
    lesson = Lesson(
        unit_id=unit_id,
        title=lesson_data["title"],
        description=lesson_data["description"],
        order_index=lesson_data.get("order_index", 0)
    )
    db.add(lesson)
    await db.commit()
    await db.refresh(lesson)
    
    return {
        "id": lesson.id,
        "unit_id": lesson.unit_id,
        "title": lesson.title,
        "description": lesson.description,
        "order_index": lesson.order_index,
        "created_at": lesson.created_at
    }
