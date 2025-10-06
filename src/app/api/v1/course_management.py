# src/app/api/v1/course_management.py
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Request
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException
from ...models.course import Course, Lesson

router = APIRouter(tags=["courses"])


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
    courses_query = db.query(Course).order_by(Course.order_index)
    courses = courses_query.offset(offset).limit(items_per_page).all()
    total = courses_query.count()
    
    # Get user progress if authenticated
    user_progress = {}
    if current_user:
        progress_query = db.query(UserCourseProgress).filter(
            UserCourseProgress.user_id == current_user["id"]
        )
        user_progress = {p.course_id: p for p in progress_query.all()}
    
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
            "progress": user_progress.get(course.id, {}).__dict__ if course.id in user_progress else None
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
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise NotFoundException("Course not found")
    
    # Get user progress
    user_progress = None
    if current_user:
        user_progress = db.query(UserCourseProgress).filter(
            UserCourseProgress.user_id == current_user["id"],
            UserCourseProgress.course_id == course_id
        ).first()
    
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
            unit_progress = db.query(UserUnitProgress).filter(
                UserUnitProgress.user_id == current_user["id"],
                UserUnitProgress.unit_id == unit.id
            ).first()
            unit_dict["progress"] = unit_progress.__dict__ if unit_progress else None
        
        units_data.append(unit_dict)
    
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "order_index": course.order_index,
        "created_at": course.created_at,
        "units": units_data,
        "progress": user_progress.__dict__ if user_progress else None
    }


@router.get("/units/{unit_id}", response_model=dict)
async def get_unit(
    request: Request,
    unit_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get a specific unit with lessons and user progress"""
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise NotFoundException("Unit not found")
    
    # Get user progress
    user_progress = None
    if current_user:
        user_progress = db.query(UserUnitProgress).filter(
            UserUnitProgress.user_id == current_user["id"],
            UserUnitProgress.unit_id == unit_id
        ).first()
    
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
            lesson_progress = db.query(UserLessonProgress).filter(
                UserLessonProgress.user_id == current_user["id"],
                UserLessonProgress.lesson_id == lesson.id
            ).first()
            lesson_dict["progress"] = lesson_progress.__dict__ if lesson_progress else None
        
        lessons_data.append(lesson_dict)
    
    return {
        "id": unit.id,
        "course_id": unit.course_id,
        "title": unit.title,
        "description": unit.description,
        "order_index": unit.order_index,
        "created_at": unit.created_at,
        "lessons": lessons_data,
        "progress": user_progress.__dict__ if user_progress else None
    }


@router.get("/lessons/{lesson_id}", response_model=dict)
async def get_lesson(
    request: Request,
    lesson_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get a specific lesson with quizzes, exercises and user progress"""
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise NotFoundException("Lesson not found")
    
    # Get user progress
    user_progress = None
    if current_user:
        user_progress = db.query(UserLessonProgress).filter(
            UserLessonProgress.user_id == current_user["id"],
            UserLessonProgress.lesson_id == lesson_id
        ).first()
    
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
        "progress": user_progress.__dict__ if user_progress else None
    }


# Admin endpoints for UC15: Manage Courses/Units/Lessons/Quizzes
@router.post("/courses", dependencies=[Depends(get_current_superuser)], status_code=201)
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
    db.commit()
    db.refresh(course)
    
    return {
        "id": course.id,
        "title": course.title,
        "description": course.description,
        "order_index": course.order_index,
        "created_at": course.created_at
    }


@router.put("/courses/{course_id}", dependencies=[Depends(get_current_superuser)])
async def update_course(
    request: Request,
    course_id: int,
    course_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Update a course (Admin only)"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise NotFoundException("Course not found")
    
    course.title = course_data.get("title", course.title)
    course.description = course_data.get("description", course.description)
    course.order_index = course_data.get("order_index", course.order_index)
    
    db.commit()
    db.refresh(course)
    
    return {"message": "Course updated successfully"}


@router.delete("/courses/{course_id}", dependencies=[Depends(get_current_superuser)])
async def delete_course(
    request: Request,
    course_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Delete a course (Admin only)"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise NotFoundException("Course not found")
    
    db.delete(course)
    db.commit()
    
    return {"message": "Course deleted successfully"}


@router.post("/courses/{course_id}/units", dependencies=[Depends(get_current_superuser)], status_code=201)
async def create_unit(
    request: Request,
    course_id: int,
    unit_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Create a new unit (Admin only)"""
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise NotFoundException("Course not found")
    
    unit = Unit(
        course_id=course_id,
        title=unit_data["title"],
        description=unit_data["description"],
        order_index=unit_data.get("order_index", 0)
    )
    db.add(unit)
    db.commit()
    db.refresh(unit)
    
    return {
        "id": unit.id,
        "course_id": unit.course_id,
        "title": unit.title,
        "description": unit.description,
        "order_index": unit.order_index,
        "created_at": unit.created_at
    }


@router.post("/units/{unit_id}/lessons", dependencies=[Depends(get_current_superuser)], status_code=201)
async def create_lesson(
    request: Request,
    unit_id: int,
    lesson_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Create a new lesson (Admin only)"""
    unit = db.query(Unit).filter(Unit.id == unit_id).first()
    if not unit:
        raise NotFoundException("Unit not found")
    
    lesson = Lesson(
        unit_id=unit_id,
        title=lesson_data["title"],
        description=lesson_data["description"],
        order_index=lesson_data.get("order_index", 0)
    )
    db.add(lesson)
    db.commit()
    db.refresh(lesson)
    
    return {
        "id": lesson.id,
        "unit_id": lesson.unit_id,
        "title": lesson.title,
        "description": lesson.description,
        "order_index": lesson.order_index,
        "created_at": lesson.created_at
    }
