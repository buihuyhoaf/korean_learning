# src/app/api/v1/daily_goals.py
from typing import Annotated, Any, cast
from datetime import datetime, UTC, date, timedelta

from fastapi import APIRouter, Depends, Request
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException, ForbiddenException, BadRequestException
from ...models.user import User
from ...models.gamification import DailyGoal, UserExpLog

router = APIRouter(tags=["daily_goals"])


# UC9: Set Daily Goal
@router.get("/user/{username}/daily-goals", response_model=dict)
async def get_user_daily_goals(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    date_range: str = None,  # "week", "month", "year" or specific date
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
    
    # Determine date range
    if date_range == "week":
        start_date = today - timedelta(days=7)
        end_date = today
    elif date_range == "month":
        start_date = today - timedelta(days=30)
        end_date = today
    elif date_range == "year":
        start_date = today - timedelta(days=365)
        end_date = today
    else:
        # Default to today
        start_date = today
        end_date = today
    
    # Get daily goals in date range
    goals_query = db.query(DailyGoal).filter(
        DailyGoal.user_id == user.id,
        DailyGoal.created_at >= start_date,
        DailyGoal.created_at <= end_date
    ).order_by(DailyGoal.created_at.desc())
    
    goals = goals_query.all()
    
    # Get today's goal specifically
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
    from ...models.progress import UserLessonProgress
    today_lessons = db.query(UserLessonProgress).filter(
        UserLessonProgress.user_id == user.id,
        UserLessonProgress.completed_at >= today
    ).count()
    
    # Create today's goal if it doesn't exist
    if not today_goal:
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
    
    # Format goals data
    goals_data = []
    for goal in goals:
        goal_date = goal.created_at
        
        # Get EXP and lessons for this specific date
        date_exp = db.query(UserExpLog).filter(
            UserExpLog.user_id == user.id,
            UserExpLog.created_at >= goal_date,
            UserExpLog.created_at < goal_date + timedelta(days=1)
        ).with_entities(func.sum(UserExpLog.amount)).scalar() or 0
        
        date_lessons = db.query(UserLessonProgress).filter(
            UserLessonProgress.user_id == user.id,
            UserLessonProgress.completed_at >= goal_date,
            UserLessonProgress.completed_at < goal_date + timedelta(days=1)
        ).count()
        
        goals_data.append({
            "date": goal_date.isoformat(),
            "target_exp": goal.target_exp,
            "current_exp": date_exp,
            "exp_completed": date_exp >= goal.target_exp,
            "target_lessons": goal.target_lessons,
            "current_lessons": date_lessons,
            "lessons_completed": date_lessons >= goal.target_lessons,
            "is_completed": goal.is_completed,
            "progress_percent": min(100, ((date_exp / goal.target_exp) + (date_lessons / goal.target_lessons)) / 2 * 100) if goal.target_exp > 0 and goal.target_lessons > 0 else 0
        })
    
    return {
        "user_id": user.id,
        "username": user.username,
        "date_range": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        },
        "today_goal": {
            "date": today.isoformat(),
            "target_exp": today_goal.target_exp,
            "current_exp": today_exp,
            "exp_completed": exp_completed,
            "target_lessons": today_goal.target_lessons,
            "current_lessons": today_lessons,
            "lessons_completed": lessons_completed,
            "is_completed": today_goal.is_completed,
            "progress_percent": min(100, ((today_exp / today_goal.target_exp) + (today_lessons / today_goal.target_lessons)) / 2 * 100) if today_goal.target_exp > 0 and today_goal.target_lessons > 0 else 0
        },
        "goals_history": goals_data,
        "statistics": calculate_goals_statistics(goals_data)
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
    
    # Validate goal data
    target_exp = goal_data.get("target_exp", 100)
    target_lessons = goal_data.get("target_lessons", 1)
    
    if target_exp < 0 or target_lessons < 0:
        raise BadRequestException("Goals must be positive values")
    
    if target_exp > 1000 or target_lessons > 20:
        raise BadRequestException("Goals exceed maximum allowed values")
    
    # Get or create today's goal
    today_goal = db.query(DailyGoal).filter(
        DailyGoal.user_id == user.id,
        DailyGoal.created_at == today
    ).first()
    
    if not today_goal:
        today_goal = DailyGoal(
            user_id=user.id,
            target_exp=target_exp,
            target_lessons=target_lessons,
            created_at=today
        )
        db.add(today_goal)
    else:
        today_goal.target_exp = target_exp
        today_goal.target_lessons = target_lessons
    
    db.commit()
    
    return {
        "message": "Daily goals updated successfully",
        "goals": {
            "date": today.isoformat(),
            "target_exp": today_goal.target_exp,
            "target_lessons": today_goal.target_lessons
        }
    }


@router.get("/user/{username}/daily-goals/streak", response_model=dict)
async def get_daily_goals_streak(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get user's daily goals completion streak"""
    
    # Check permissions
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own streak")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    # Get completed goals in chronological order
    completed_goals = db.query(DailyGoal).filter(
        DailyGoal.user_id == user.id,
        DailyGoal.is_completed == True
    ).order_by(DailyGoal.created_at.desc()).all()
    
    # Calculate current streak
    current_streak = 0
    longest_streak = 0
    temp_streak = 0
    
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    for i, goal in enumerate(completed_goals):
        goal_date = goal.created_at
        
        if i == 0:
            # First goal (most recent)
            if goal_date == today or goal_date == yesterday:
                current_streak = 1
                temp_streak = 1
            else:
                current_streak = 0
                temp_streak = 0
        else:
            # Check if this goal is consecutive with the previous one
            prev_goal_date = completed_goals[i-1].created_at
            if goal_date == prev_goal_date - timedelta(days=1):
                temp_streak += 1
                if i == len(completed_goals) - 1:  # Last goal
                    current_streak = temp_streak
            else:
                longest_streak = max(longest_streak, temp_streak)
                temp_streak = 1
    
    longest_streak = max(longest_streak, temp_streak)
    
    # Get total completed goals
    total_completed = len(completed_goals)
    
    # Get total days since user started
    first_goal = db.query(DailyGoal).filter(DailyGoal.user_id == user.id).order_by(DailyGoal.created_at.asc()).first()
    total_days = 0
    if first_goal:
        total_days = (today - first_goal.created_at).days + 1
    
    completion_rate = (total_completed / total_days * 100) if total_days > 0 else 0
    
    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "total_completed": total_completed,
        "total_days": total_days,
        "completion_rate": round(completion_rate, 2),
        "streak_status": "active" if current_streak > 0 else "broken"
    }


@router.post("/user/{username}/daily-goals/complete", response_model=dict)
async def mark_daily_goals_complete(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Manually mark daily goals as complete (for testing or special cases)"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only complete your own daily goals")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    today = date.today()
    
    # Get today's goal
    today_goal = db.query(DailyGoal).filter(
        DailyGoal.user_id == user.id,
        DailyGoal.created_at == today
    ).first()
    
    if not today_goal:
        raise NotFoundException("No daily goal found for today")
    
    if today_goal.is_completed:
        return {"message": "Daily goals already completed today"}
    
    # Mark as completed
    today_goal.is_completed = True
    db.commit()
    
    # Award completion bonus EXP
    completion_bonus = 25
    user.exp += completion_bonus
    
    # Log EXP gain
    exp_log = UserExpLog(
        user_id=user.id,
        source="daily_goals_completion",
        amount=completion_bonus
    )
    db.add(exp_log)
    
    db.commit()
    
    return {
        "message": "Daily goals marked as complete!",
        "completion_bonus_exp": completion_bonus,
        "total_exp": user.exp
    }


def calculate_goals_statistics(goals_data: list) -> dict:
    """Calculate statistics from goals data"""
    if not goals_data:
        return {
            "completion_rate": 0,
            "average_progress": 0,
            "total_goals": 0,
            "completed_goals": 0
        }
    
    total_goals = len(goals_data)
    completed_goals = len([goal for goal in goals_data if goal["is_completed"]])
    average_progress = sum([goal["progress_percent"] for goal in goals_data]) / total_goals
    completion_rate = (completed_goals / total_goals * 100) if total_goals > 0 else 0
    
    return {
        "completion_rate": round(completion_rate, 2),
        "average_progress": round(average_progress, 2),
        "total_goals": total_goals,
        "completed_goals": completed_goals
    }


# Admin endpoints for monitoring daily goals
@router.get("/admin/daily-goals/stats", dependencies=[Depends(get_current_superuser)], response_model=dict)
async def get_daily_goals_stats(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Get daily goals statistics (Admin only)"""
    
    today = date.today()
    
    # Get total users with daily goals
    total_users_with_goals = db.query(DailyGoal.user_id).distinct().count()
    
    # Get today's goals
    today_goals = db.query(DailyGoal).filter(DailyGoal.created_at == today).all()
    
    # Calculate completion statistics
    completed_today = len([goal for goal in today_goals if goal.is_completed])
    completion_rate = (completed_today / len(today_goals) * 100) if today_goals else 0
    
    # Get average goals per user
    avg_exp_goal = db.query(func.avg(DailyGoal.target_exp)).filter(DailyGoal.created_at == today).scalar() or 0
    avg_lessons_goal = db.query(func.avg(DailyGoal.target_lessons)).filter(DailyGoal.created_at == today).scalar() or 0
    
    # Get streak statistics
    streak_stats = db.query(
        func.max(DailyGoal.created_at).label('max_date'),
        func.count(DailyGoal.id).label('total_goals')
    ).filter(DailyGoal.is_completed == True).first()
    
    return {
        "total_users_with_goals": total_users_with_goals,
        "today_goals": {
            "total": len(today_goals),
            "completed": completed_today,
            "completion_rate": round(completion_rate, 2)
        },
        "average_goals": {
            "target_exp": round(avg_exp_goal, 2),
            "target_lessons": round(avg_lessons_goal, 2)
        },
        "streak_stats": {
            "total_completed_goals": streak_stats.total_goals if streak_stats else 0,
            "last_completion": streak_stats.max_date if streak_stats else None
        }
    }
