# src/app/api/v1/user_progress.py
from typing import Annotated, Any, cast, Sequence
from datetime import datetime, UTC, date, timedelta, time
from uuid import UUID

from fastapi import APIRouter, Depends, Request, Query
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, or_

from ...api.dependencies import get_current_user, get_current_superuser, get_current_admin_or_teacher
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException, ForbiddenException
from ...models.user import User
from ...models.progress import UserCourseProgress, UserUnitProgress, UserLessonProgress
from ...models.gamification import DailyGoal, UserExpLog
from ...models.course import Course
from ...schemas.user import UserSummary
from ...schemas.progress_tracking import ExpSeriesResponse, UserExpSeries, DateRange, ExpPoint


async def fetch_progress_tracker_users(
    db: AsyncSession,
    search_term: str,
    limit: int,
) -> list[UserSummary]:
    """Shared helper to search users for the admin progress tracker."""
    normalized = search_term.strip()
    if not normalized:
        return []

    stmt = (
        select(User)
        .where(
            or_(
                User.username.ilike(f"%{normalized}%"),
                User.email.ilike(f"%{normalized}%"),
            )
        )
        .order_by(User.username.asc())
        .limit(limit)
    )
    users_result = await db.execute(stmt)
    users = users_result.scalars().all()

    return [UserSummary.model_validate(user) for user in users]


def _build_empty_exp_series_response() -> ExpSeriesResponse:
    today = datetime.now(UTC).date()
    return ExpSeriesResponse(
        date_range=DateRange(start=today, end=today),
        series=[],
    )


async def build_exp_series_response(
    db: AsyncSession,
    target_ids: Sequence[UUID],
    days: int,
) -> ExpSeriesResponse:
    """Shared helper to compose EXP time-series payload for given users."""
    if not target_ids:
        return _build_empty_exp_series_response()

    end_date = datetime.now(UTC).date()
    start_date = end_date - timedelta(days=days - 1)
    cutoff = datetime.combine(start_date, time.min, tzinfo=UTC)

    user_rows = await db.execute(
        select(User.id, User.username, User.exp).where(User.id.in_(target_ids))
    )
    raw_user_rows = user_rows.all()
    user_map = {row.id: {"username": row.username, "total_exp": row.exp or 0} for row in raw_user_rows}

    if len(user_map) != len(target_ids):
        raise NotFoundException("At least one user could not be found")

    baseline_rows = await db.execute(
        select(
            UserExpLog.user_id,
            func.coalesce(func.sum(UserExpLog.amount), 0).label("baseline"),
        )
        .where(
            UserExpLog.user_id.in_(target_ids),
            UserExpLog.created_at < cutoff,
        )
        .group_by(UserExpLog.user_id)
    )
    baseline_map = {row.user_id: int(row.baseline or 0) for row in baseline_rows.all()}

    bucket = func.date_trunc("day", UserExpLog.created_at)
    timeseries_rows = await db.execute(
        select(
            UserExpLog.user_id,
            bucket.label("bucket"),
            func.coalesce(func.sum(UserExpLog.amount), 0).label("exp_delta"),
        )
        .where(
            UserExpLog.user_id.in_(target_ids),
            UserExpLog.created_at >= cutoff,
        )
        .group_by(UserExpLog.user_id, bucket)
        .order_by(bucket.asc())
    )

    per_user_daily: dict[UUID, dict[date, int]] = {user_id: {} for user_id in target_ids}
    for user_id, bucket_value, exp_delta in timeseries_rows.all():
        day = bucket_value.date()
        per_user_daily[user_id][day] = int(exp_delta or 0)

    day_span = (end_date - start_date).days
    timeline = [start_date + timedelta(days=offset) for offset in range(day_span + 1)]

    series_payload: list[UserExpSeries] = []
    for user_id in target_ids:
        user_info = user_map[user_id]
        baseline_exp = baseline_map.get(user_id, 0)
        cumulative = baseline_exp
        points: list[ExpPoint] = []

        daily_map = per_user_daily.get(user_id, {})
        for day in timeline:
            delta = daily_map.get(day, 0)
            cumulative += delta
            points.append(
                ExpPoint(
                    date=day,
                    exp_delta=delta,
                    cumulative_exp=cumulative,
                )
            )

        series_payload.append(
            UserExpSeries(
                user_id=user_id,
                username=user_info["username"],
                baseline_exp=baseline_exp,
                series=points,
            )
        )

    return ExpSeriesResponse(
        date_range=DateRange(start=start_date, end=end_date),
        series=series_payload,
    )


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
    
    user_result = await db.execute(select(User).where(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    # Get course progress
    course_result = await db.execute(
        select(UserCourseProgress).where(UserCourseProgress.user_id == user.id)
    )
    course_progress = course_result.scalars().all()
    
    # Get unit progress
    unit_result = await db.execute(
        select(UserUnitProgress).where(UserUnitProgress.user_id == user.id)
    )
    unit_progress = unit_result.scalars().all()
    
    # Get lesson progress
    lesson_result = await db.execute(
        select(UserLessonProgress).where(UserLessonProgress.user_id == user.id)
    )
    lesson_progress = lesson_result.scalars().all()
    
    # Get EXP logs
    exp_logs_result = await db.execute(
        select(UserExpLog)
        .where(UserExpLog.user_id == user.id)
        .order_by(UserExpLog.created_at.desc())
        .limit(10)
    )
    exp_logs = exp_logs_result.scalars().all()
    
    # Calculate statistics
    total_courses = len(course_progress)
    completed_courses = len([cp for cp in course_progress if cp.is_completed])
    
    total_units = len(unit_progress)
    completed_units = len([up for up in unit_progress if up.is_completed])
    
    total_lessons = len(lesson_progress)
    completed_lessons = len([lp for lp in lesson_progress if lp.is_completed])
    
    # Note: UserQuizAttempt has been removed
    total_quizzes = 0
    avg_quiz_score = 0.0
    
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
    
    user_result = await db.execute(select(User).where(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    offset = compute_offset(page, items_per_page)
    
    # Get course progress with course details
    base_stmt = (
        select(UserCourseProgress)
        .where(UserCourseProgress.user_id == user.id)
        .order_by(UserCourseProgress.created_at.desc())
    )
    progress_records_result = await db.execute(base_stmt.offset(offset).limit(items_per_page))
    progress_records = progress_records_result.scalars().all()
    total_result = await db.execute(select(func.count()).select_from(base_stmt.subquery()))
    total = total_result.scalar() or 0
    
    progress_data = []
    for progress in progress_records:
        # Get course details
        course_result = await db.execute(select(Course).where(Course.id == progress.course_id))
        course = course_result.scalar_one_or_none()
        
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
    
    user_result = await db.execute(select(User).where(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    offset = compute_offset(page, items_per_page)
    
    base_stmt = (
        select(UserExpLog)
        .where(UserExpLog.user_id == user.id)
        .order_by(UserExpLog.created_at.desc())
    )
    exp_logs_result = await db.execute(base_stmt.offset(offset).limit(items_per_page))
    exp_logs = exp_logs_result.scalars().all()
    total_result = await db.execute(select(func.count()).select_from(base_stmt.subquery()))
    total = total_result.scalar() or 0
    
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
    
    user_result = await db.execute(select(User).where(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    # Check if user has completed activities today
    today = date.today()
    today_exp_logs = (
        await db.execute(
            select(func.count()).select_from(UserExpLog).where(
        UserExpLog.user_id == user.id,
        UserExpLog.created_at >= today
            )
        )
    ).scalar() or 0
    
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
        
        await db.commit()
        
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
    
    user_result = await db.execute(select(User).where(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    today = date.today()
    
    # Get today's goal
    today_goal_result = await db.execute(
        select(DailyGoal).where(
        DailyGoal.user_id == user.id,
        DailyGoal.created_at == today
        )
    )
    today_goal = today_goal_result.scalar_one_or_none()
    
    # Get today's EXP earned
    today_exp = (
        await db.execute(
            select(func.sum(UserExpLog.amount)).where(
        UserExpLog.user_id == user.id,
        UserExpLog.created_at >= today
            )
        )
    ).scalar() or 0
    
    # Get today's lessons completed
    today_lessons = (
        await db.execute(
            select(func.count()).select_from(UserLessonProgress).where(
        UserLessonProgress.user_id == user.id,
        UserLessonProgress.completed_at >= today
            )
        )
    ).scalar() or 0
    
    if not today_goal:
        # Create default goal for today
        today_goal = DailyGoal(
            user_id=user.id,
            target_exp=100,
            target_lessons=1,
            created_at=today
        )
        db.add(today_goal)
        await db.commit()
        await db.refresh(today_goal)
    
    # Check if goals are completed
    exp_completed = today_exp >= today_goal.target_exp
    lessons_completed = today_lessons >= today_goal.target_lessons
    
    # Update goal completion status
    if exp_completed and lessons_completed and not today_goal.is_completed:
        today_goal.is_completed = True
        await db.commit()
    
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
    
    user_result = await db.execute(select(User).where(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    today = date.today()
    
    # Get or create today's goal
    today_goal_result = await db.execute(
        select(DailyGoal).where(
        DailyGoal.user_id == user.id,
        DailyGoal.created_at == today
        )
    )
    today_goal = today_goal_result.scalar_one_or_none()
    
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
    
    await db.commit()
    
    return {
        "message": "Daily goals updated successfully",
        "target_exp": today_goal.target_exp,
        "target_lessons": today_goal.target_lessons
    }


# Admin endpoints for monitoring progress
@router.get(
    "/admin/progress-tracking/users",
    response_model=list[UserSummary],
)
async def search_users_for_progress_tracker(
    request: Request,
    search: Annotated[str, Query(min_length=1, description="Username or email fragment to search for")],
    limit: Annotated[int, Query(ge=1, le=25)] = 10,
    current_user: Annotated[dict, Depends(get_current_admin_or_teacher)] = None,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
) -> list[UserSummary]:
    """Search for users by username or email for the admin progress tracker."""
    return await fetch_progress_tracker_users(db=db, search_term=search, limit=limit)


@router.get(
    "/admin/progress-tracking/exp-series",
    response_model=ExpSeriesResponse,
)
async def get_users_exp_series(
    request: Request,
    user_ids: Annotated[str, Query(min_length=1, description="Comma separated list of user UUIDs")],
    days: Annotated[int, Query(ge=1, le=365)] = 30,
    current_user: Annotated[dict, Depends(get_current_admin_or_teacher)] = None,
    db: Annotated[AsyncSession, Depends(async_get_db)] = None,
) -> ExpSeriesResponse:
    """Return EXP time-series data for the selected users."""
    raw_ids = [uid.strip() for uid in user_ids.split(",") if uid.strip()]
    if not raw_ids:
        return _build_empty_exp_series_response()

    try:
        target_ids = [UUID(uid) for uid in raw_ids]
    except ValueError as exc:
        raise NotFoundException("One or more user IDs are invalid") from exc

    return await build_exp_series_response(db=db, target_ids=target_ids, days=days)


@router.get("/admin/progress-stats", dependencies=[Depends(get_current_superuser)], response_model=dict)
async def get_progress_stats(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Get overall progress statistics (Admin only)"""
    
    # Get total users
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar() or 0
    
    # Get active users (users with activity in last 7 days)
    week_ago = datetime.now(UTC) - timedelta(days=7)
    active_users = (
        await db.execute(
            select(func.count()).select_from(User).join(UserExpLog).where(
        UserExpLog.created_at >= week_ago
            ).distinct()
        )
    ).scalar() or 0
    
    # Get average EXP
    avg_exp = (await db.execute(select(func.avg(User.exp)))).scalar() or 0
    
    # Get average streak
    avg_streak = (await db.execute(select(func.avg(User.streak_days)))).scalar() or 0
    
    # Get completion rates
    total_course_progress = (await db.execute(select(func.count()).select_from(UserCourseProgress))).scalar() or 0
    completed_courses = (
        await db.execute(
            select(func.count()).select_from(UserCourseProgress).where(UserCourseProgress.is_completed == True)
        )
    ).scalar() or 0
    
    total_lesson_progress = (await db.execute(select(func.count()).select_from(UserLessonProgress))).scalar() or 0
    completed_lessons = (
        await db.execute(
            select(func.count()).select_from(UserLessonProgress).where(UserLessonProgress.is_completed == True)
        )
    ).scalar() or 0
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "average_exp": round(avg_exp, 2),
        "average_streak": round(avg_streak, 2),
        "course_completion_rate": (completed_courses / total_course_progress * 100) if total_course_progress > 0 else 0,
        "lesson_completion_rate": (completed_lessons / total_lesson_progress * 100) if total_lesson_progress > 0 else 0
    }
