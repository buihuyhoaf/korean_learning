# src/app/api/v1/user_progress.py
from typing import Annotated, Any, cast
from datetime import datetime, UTC, date, timedelta

from fastapi import APIRouter, Depends, Request
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException, ForbiddenException
from ...models.user import User
from ...models.progress import UserCourseProgress, UserUnitProgress, UserLessonProgress, UserQuizAttempt
from src.app.models import UserExpLog
from ...models.gamification import DailyGoal

router = APIRouter(tags=["progress"])


# UC6: Track Progress: EXP, Streak
@router.get("/user/{username}/progress", response_model=dict)
async def get_user_progress(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get user's overall progress including EXP and streak"""
    
    # Check permissions
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own progress")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    # Get course progress
    course_progress = db.query(UserCourseProgress).filter(
        UserCourseProgress.user_id == user.id
    ).all()
    
    # Get unit progress
    unit_progress = db.query(UserUnitProgress).filter(
        UserUnitProgress.user_id == user.id
    ).all()
    
    # Get lesson progress
    lesson_progress = db.query(UserLessonProgress).filter(
        UserLessonProgress.user_id == user.id
    ).all()
    
    # Get quiz attempts
    quiz_attempts = db.query(UserQuizAttempt).filter(
        UserQuizAttempt.user_id == user.id
    ).all()
    
    # Get EXP logs
    exp_logs = db.query(UserExpLog).filter(
        UserExpLog.user_id == user.id
    ).order_by(UserExpLog.created_at.desc()).limit(10).all()
    
    # Calculate statistics
    total_courses = len(course_progress)
    completed_courses = len([cp for cp in course_progress if cp.is_completed])
    
    total_units = len(unit_progress)
    completed_units = len([up for up in unit_progress if up.is_completed])
    
    total_lessons = len(lesson_progress)
    completed_lessons = len([lp for lp in lesson_progress if lp.is_completed])
    
    total_quizzes = len(quiz_attempts)
    avg_quiz_score = sum([qa.score for qa in quiz_attempts]) / total_quizzes if total_quizzes > 0 else 0
    
    # Calculate streak
    streak_days = user.streak_days
    
    # Get recent EXP activity
    recent_exp = [
        {
            "source": log.source,
            "amount": log.amount,
            "created_at": log.created_at
        }
        for log in exp_logs
    ]
    
    return {
        "user_id": user.id,
        "username": user.username,
        "total_exp": user.exp,
        "streak_days": streak_days,
        "courses": {
            "total": total_courses,
            "completed": completed_courses,
            "progress_percent": (completed_courses / total_courses * 100) if total_courses > 0 else 0
        },
        "units": {
            "total": total_units,
            "completed": completed_units,
            "progress_percent": (completed_units / total_units * 100) if total_units > 0 else 0
        },
        "lessons": {
            "total": total_lessons,
            "completed": completed_lessons,
            "progress_percent": (completed_lessons / total_lessons * 100) if total_lessons > 0 else 0
        },
        "quizzes": {
            "total_attempts": total_quizzes,
            "average_score": round(avg_quiz_score, 2)
        },
        "recent_exp_activity": recent_exp
    }


@router.get("/user/{username}/course-progress", response_model=PaginatedListResponse[dict])
async def get_user_course_progress(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 10,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get user's course progress details"""
    
    # Check permissions
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own progress")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    offset = compute_offset(page, items_per_page)
    
    # Get course progress with course details
    progress_query = db.query(UserCourseProgress).filter(
        UserCourseProgress.user_id == user.id
    ).order_by(UserCourseProgress.created_at.desc())
    
    progress_records = progress_query.offset(offset).limit(items_per_page).all()
    total = progress_query.count()
    
    progress_data = []
    for progress in progress_records:
        # Get course details
        course = db.query(Course).filter(Course.id == progress.course_id).first()
        
        progress_dict = {
            "id": progress.id,
            "course_id": progress.course_id,
            "course_title": course.title if course else None,
            "is_completed": progress.is_completed,
            "progress_percent": progress.progress_percent,
            "completed_at": progress.completed_at,
            "created_at": progress.created_at
        }
        progress_data.append(progress_dict)
    
    response = paginated_response(
        crud_data={"data": progress_data, "total": total},
        page=page,
        items_per_page=items_per_page
    )
    return response


@router.get("/user/{username}/exp-history", response_model=PaginatedListResponse[dict])
async def get_user_exp_history(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 20,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get user's EXP earning history"""
    
    # Check permissions
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own EXP history")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    offset = compute_offset(page, items_per_page)
    
    exp_query = db.query(UserExpLog).filter(
        UserExpLog.user_id == user.id
    ).order_by(UserExpLog.created_at.desc())
    
    exp_logs = exp_query.offset(offset).limit(items_per_page).all()
    total = exp_query.count()
    
    exp_data = []
    for log in exp_logs:
        log_dict = {
            "id": log.id,
            "source": log.source,
            "amount": log.amount,
            "created_at": log.created_at
        }
        exp_data.append(log_dict)
    
    response = paginated_response(
        crud_data={"data": exp_data, "total": total},
        page=page,
        items_per_page=items_per_page
    )
    return response


@router.post("/user/{username}/update-streak", response_model=dict)
async def update_user_streak(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Update user's streak (called when user completes daily activities)"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only update your own streak")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    # Check if user has completed activities today
    today = date.today()
    today_exp_logs = db.query(UserExpLog).filter(
        UserExpLog.user_id == user.id,
        UserExpLog.created_at >= today
    ).count()
    
    if today_exp_logs > 0:
        # User has activity today, increment streak
        user.streak_days += 1
        
        # Add streak bonus EXP
        streak_bonus = min(user.streak_days * 5, 50)  # Max 50 EXP bonus
        if streak_bonus > 0:
            user.exp += streak_bonus
            
            # Log streak bonus
            exp_log = UserExpLog(
                user_id=user.id,
                source="streak_bonus",
                amount=streak_bonus
            )
            db.add(exp_log)
        
        db.commit()
        
        return {
            "message": "Streak updated successfully",
            "new_streak": user.streak_days,
            "streak_bonus_exp": streak_bonus
        }
    else:
        return {
            "message": "No activity today to update streak",
            "current_streak": user.streak_days
        }


@router.get("/user/{username}/daily-goals", response_model=dict)
async def get_user_daily_goals(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get user's daily goals and progress"""
    
    # Check permissions
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own daily goals")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    today = date.today()
    
    # Get today's goal
    today_goal = db.query(DailyGoal).filter(
        DailyGoal.user_id == user.id,
        DailyGoal.created_at == today
    ).first()
    
    # Get today's EXP earned
    today_exp = db.query(UserExpLog).filter(
        UserExpLog.user_id == user.id,
        UserExpLog.created_at >= today
    ).with_entities(func.sum(UserExpLog.amount)).scalar() or 0
    
    # Get today's lessons completed
    today_lessons = db.query(UserLessonProgress).filter(
        UserLessonProgress.user_id == user.id,
        UserLessonProgress.completed_at >= today
    ).count()
    
    if not today_goal:
        # Create default goal for today
        today_goal = DailyGoal(
            user_id=user.id,
            target_exp=100,
            target_lessons=1,
            created_at=today
        )
        db.add(today_goal)
        db.commit()
        db.refresh(today_goal)
    
    # Check if goals are completed
    exp_completed = today_exp >= today_goal.target_exp
    lessons_completed = today_lessons >= today_goal.target_lessons
    
    # Update goal completion status
    if exp_completed and lessons_completed and not today_goal.is_completed:
        today_goal.is_completed = True
        db.commit()
    
    return {
        "date": today.isoformat(),
        "target_exp": today_goal.target_exp,
        "current_exp": today_exp,
        "exp_completed": exp_completed,
        "target_lessons": today_goal.target_lessons,
        "current_lessons": today_lessons,
        "lessons_completed": lessons_completed,
        "is_completed": today_goal.is_completed,
        "progress_percent": min(100, ((today_exp / today_goal.target_exp) + (today_lessons / today_goal.target_lessons)) / 2 * 100)
    }


@router.put("/user/{username}/daily-goals", response_model=dict)
async def update_user_daily_goals(
    request: Request,
    username: str,
    goal_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Update user's daily goals"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only update your own daily goals")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    today = date.today()
    
    # Get or create today's goal
    today_goal = db.query(DailyGoal).filter(
        DailyGoal.user_id == user.id,
        DailyGoal.created_at == today
    ).first()
    
    if not today_goal:
        today_goal = DailyGoal(
            user_id=user.id,
            target_exp=goal_data.get("target_exp", 100),
            target_lessons=goal_data.get("target_lessons", 1),
            created_at=today
        )
        db.add(today_goal)
    else:
        today_goal.target_exp = goal_data.get("target_exp", today_goal.target_exp)
        today_goal.target_lessons = goal_data.get("target_lessons", today_goal.target_lessons)
    
    db.commit()
    
    return {
        "message": "Daily goals updated successfully",
        "target_exp": today_goal.target_exp,
        "target_lessons": today_goal.target_lessons
    }


# Admin endpoints for monitoring progress
@router.get("/admin/progress-stats", dependencies=[Depends(get_current_superuser)], response_model=dict)
async def get_progress_stats(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Get overall progress statistics (Admin only)"""
    
    # Get total users
    total_users = db.query(User).count()
    
    # Get active users (users with activity in last 7 days)
    week_ago = datetime.now(UTC) - timedelta(days=7)
    active_users = db.query(User).join(UserExpLog).filter(
        UserExpLog.created_at >= week_ago
    ).distinct().count()
    
    # Get average EXP
    avg_exp = db.query(func.avg(User.exp)).scalar() or 0
    
    # Get average streak
    avg_streak = db.query(func.avg(User.streak_days)).scalar() or 0
    
    # Get completion rates
    total_course_progress = db.query(UserCourseProgress).count()
    completed_courses = db.query(UserCourseProgress).filter(
        UserCourseProgress.is_completed == True
    ).count()
    
    total_lesson_progress = db.query(UserLessonProgress).count()
    completed_lessons = db.query(UserLessonProgress).filter(
        UserLessonProgress.is_completed == True
    ).count()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "average_exp": round(avg_exp, 2),
        "average_streak": round(avg_streak, 2),
        "course_completion_rate": (completed_courses / total_course_progress * 100) if total_course_progress > 0 else 0,
        "lesson_completion_rate": (completed_lessons / total_lesson_progress * 100) if total_lesson_progress > 0 else 0
    }
