# src/app/api/v1/challenges.py
from typing import Annotated, Any, cast
from datetime import datetime, UTC, date

from fastapi import APIRouter, Depends, Request
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, delete

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException, ForbiddenException, DuplicateValueException, BadRequestException
from ...models.user import User
from ...models.gamification import Challenge, UserChallenge, UserExpLog

router = APIRouter(tags=["challenges"])


# UC10: Join Challenges
@router.get("/challenges", response_model=PaginatedListResponse[dict])
async def get_challenges(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 10,
    status: str = None,  # "active", "upcoming", "completed", "expired"
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get all challenges with user's participation status"""
    
    offset = compute_offset(page, items_per_page)
    today = date.today()
    
    # Build query based on status filter
    base_stmt = select(Challenge)
    
    if status == "active":
        base_stmt = base_stmt.where(Challenge.start_date <= today, Challenge.end_date >= today)
    elif status == "upcoming":
        base_stmt = base_stmt.where(Challenge.start_date > today)
    elif status == "expired":
        base_stmt = base_stmt.where(Challenge.end_date < today)
    elif status == "completed":
        # Only show completed challenges if user is authenticated
        if not current_user:
            return {"data": [], "total": 0, "page": page, "items_per_page": items_per_page, "total_pages": 0}
        base_stmt = base_stmt.join(UserChallenge).where(
            UserChallenge.user_id == current_user["id"],
            UserChallenge.is_completed == True
        )
    
    stmt = base_stmt.order_by(Challenge.start_date.desc()).offset(offset).limit(items_per_page)
    challenges_result = await db.execute(stmt)
    challenges = challenges_result.scalars().all()
    total_result = await db.execute(select(func.count()).select_from(base_stmt.subquery()))
    total = total_result.scalar() or 0
    
    challenges_data = []
    for challenge in challenges:
        challenge_dict = {
            "id": challenge.id,
            "title": challenge.title,
            "description": challenge.description,
            "start_date": challenge.start_date,
            "end_date": challenge.end_date,
            "exp_reward": challenge.exp_reward,
            "status": get_challenge_status(challenge, today),
            "participants_count": (
                (await db.execute(
                    select(func.count()).select_from(UserChallenge).where(UserChallenge.challenge_id == challenge.id)
                )).scalar() or 0
            ),
            "user_participation": None
        }
        
        # Get user's participation if authenticated
        if current_user:
            uc_result = await db.execute(
                select(UserChallenge).where(
                    UserChallenge.user_id == current_user["id"],
                    UserChallenge.challenge_id == challenge.id
                )
            )
            user_challenge = uc_result.scalar_one_or_none()
            
            if user_challenge:
                challenge_dict["user_participation"] = {
                    "is_joined": True,
                    "progress_percent": user_challenge.progress_percent,
                    "is_completed": user_challenge.is_completed,
                    "completed_at": user_challenge.completed_at
                }
            else:
                challenge_dict["user_participation"] = {
                    "is_joined": False,
                    "progress_percent": 0,
                    "is_completed": False,
                    "completed_at": None
                }
        
        challenges_data.append(challenge_dict)
    
    response = paginated_response(
        crud_data={"data": challenges_data, "total": total},
        page=page,
        items_per_page=items_per_page
    )
    return response


@router.get("/challenges/{challenge_id}", response_model=dict)
async def get_challenge_details(
    request: Request,
    challenge_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get detailed information about a specific challenge"""
    
    challenge_result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = challenge_result.scalar_one_or_none()
    if not challenge:
        raise NotFoundException("Challenge not found")
    
    today = date.today()
    
    # Get participants
    participants_result = await db.execute(select(UserChallenge).where(UserChallenge.challenge_id == challenge_id))
    participants = participants_result.scalars().all()
    participants_count = len(participants)
    
    # Get user's participation
    user_participation = None
    if current_user:
        uc_result = await db.execute(
            select(UserChallenge).where(
                UserChallenge.user_id == current_user["id"],
                UserChallenge.challenge_id == challenge_id
            )
        )
        user_challenge = uc_result.scalar_one_or_none()
        
        if user_challenge:
            user_participation = {
                "is_joined": True,
                "progress_percent": user_challenge.progress_percent,
                "is_completed": user_challenge.is_completed,
                "completed_at": user_challenge.completed_at
            }
        else:
            user_participation = {
                "is_joined": False,
                "progress_percent": 0,
                "is_completed": False,
                "completed_at": None
            }
    
    return {
        "id": challenge.id,
        "title": challenge.title,
        "description": challenge.description,
        "start_date": challenge.start_date,
        "end_date": challenge.end_date,
        "exp_reward": challenge.exp_reward,
        "status": get_challenge_status(challenge, today),
        "participants_count": participants_count,
        "user_participation": user_participation
    }


@router.post("/challenges/{challenge_id}/join", response_model=dict)
async def join_challenge(
    request: Request,
    challenge_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Join a challenge"""
    
    challenge_result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = challenge_result.scalar_one_or_none()
    if not challenge:
        raise NotFoundException("Challenge not found")
    
    today = date.today()
    
    # Check if challenge is active
    if challenge.start_date > today:
        raise BadRequestException("Challenge has not started yet")
    
    if challenge.end_date < today:
        raise BadRequestException("Challenge has already ended")
    
    # Check if user already joined
    existing_participation_result = await db.execute(
        select(UserChallenge).where(
            UserChallenge.user_id == current_user["id"],
            UserChallenge.challenge_id == challenge_id
        )
    )
    existing_participation = existing_participation_result.scalar_one_or_none()
    
    if existing_participation:
        raise DuplicateValueException("You have already joined this challenge")
    
    # Create user challenge participation
    user_challenge = UserChallenge(
        user_id=current_user["id"],
        challenge_id=challenge_id,
        progress_percent=0.0,
        is_completed=False
    )
    db.add(user_challenge)
    await db.commit()
    
    return {
        "message": f"Successfully joined the '{challenge.title}' challenge!",
        "challenge": {
            "id": challenge.id,
            "title": challenge.title,
            "description": challenge.description,
            "end_date": challenge.end_date,
            "exp_reward": challenge.exp_reward
        }
    }


@router.get("/user/{username}/challenges", response_model=PaginatedListResponse[dict])
async def get_user_challenges(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 10,
    status: str = None,  # "active", "completed", "expired"
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get user's challenge participation history"""
    
    # Check permissions
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own challenges")
    
    user_result = await db.execute(select(User).where(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    offset = compute_offset(page, items_per_page)
    today = date.today()
    
    # Build query
    base_stmt = select(UserChallenge).where(UserChallenge.user_id == user.id)
    
    if status == "active":
        base_stmt = base_stmt.join(Challenge).where(
            Challenge.start_date <= today,
            Challenge.end_date >= today,
            UserChallenge.is_completed == False
        )
    elif status == "completed":
        base_stmt = base_stmt.where(UserChallenge.is_completed == True)
    elif status == "expired":
        base_stmt = base_stmt.join(Challenge).where(
            Challenge.end_date < today,
            UserChallenge.is_completed == False
        )
    
    stmt = base_stmt.order_by(UserChallenge.created_at.desc()).offset(offset).limit(items_per_page)
    user_challenges_result = await db.execute(stmt)
    user_challenges = user_challenges_result.scalars().all()
    total_result = await db.execute(select(func.count()).select_from(base_stmt.subquery()))
    total = total_result.scalar() or 0
    
    challenges_data = []
    for user_challenge in user_challenges:
        challenge_result = await db.execute(select(Challenge).where(Challenge.id == user_challenge.challenge_id))
        challenge = challenge_result.scalar_one_or_none()
        if challenge:
            challenge_dict = {
                "id": challenge.id,
                "title": challenge.title,
                "description": challenge.description,
                "start_date": challenge.start_date,
                "end_date": challenge.end_date,
                "exp_reward": challenge.exp_reward,
                "status": get_challenge_status(challenge, today),
                "participation": {
                    "progress_percent": user_challenge.progress_percent,
                    "is_completed": user_challenge.is_completed,
                    "completed_at": user_challenge.completed_at
                }
            }
            challenges_data.append(challenge_dict)
    
    response = paginated_response(
        crud_data={"data": challenges_data, "total": total},
        page=page,
        items_per_page=items_per_page
    )
    return response


@router.put("/challenges/{challenge_id}/progress", response_model=dict)
async def update_challenge_progress(
    request: Request,
    challenge_id: int,
    progress_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Update user's progress in a challenge"""
    
    challenge_result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = challenge_result.scalar_one_or_none()
    if not challenge:
        raise NotFoundException("Challenge not found")
    
    uc_result = await db.execute(
        select(UserChallenge).where(
            UserChallenge.user_id == current_user["id"],
            UserChallenge.challenge_id == challenge_id
        )
    )
    user_challenge = uc_result.scalar_one_or_none()
    
    if not user_challenge:
        raise NotFoundException("You are not participating in this challenge")
    
    # Update progress
    new_progress = progress_data.get("progress_percent", user_challenge.progress_percent)
    user_challenge.progress_percent = min(100.0, max(0.0, new_progress))
    
    # Check if challenge is completed
    if user_challenge.progress_percent >= 100.0 and not user_challenge.is_completed:
        user_challenge.is_completed = True
        user_challenge.completed_at = datetime.now(UTC)
        
        # Award EXP
        user_result = await db.execute(select(User).where(User.id == current_user["id"]))
        user = user_result.scalar_one_or_none()
        if user:
            user.exp += challenge.exp_reward
        
        # Log EXP gain
        exp_log = UserExpLog(
            user_id=current_user["id"],
            source="challenge_completed",
            amount=challenge.exp_reward
        )
        db.add(exp_log)
    
    await db.commit()
    
    return {
        "message": "Challenge progress updated successfully",
        "progress_percent": user_challenge.progress_percent,
        "is_completed": user_challenge.is_completed,
        "exp_earned": challenge.exp_reward if user_challenge.is_completed else 0
    }


def get_challenge_status(challenge: Challenge, today: date) -> str:
    """Determine challenge status based on dates"""
    if challenge.start_date > today:
        return "upcoming"
    elif challenge.end_date < today:
        return "expired"
    else:
        return "active"


# Admin endpoints for UC16: Manage Challenges
@router.post("/challenges", dependencies=[Depends(get_current_superuser)], status_code=201)
async def create_challenge(
    request: Request,
    challenge_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Create a new challenge (Admin only)"""
    
    challenge = Challenge(
        title=challenge_data["title"],
        description=challenge_data["description"],
        start_date=challenge_data["start_date"],
        end_date=challenge_data["end_date"],
        exp_reward=challenge_data.get("exp_reward", 0)
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    
    return {
        "id": challenge.id,
        "title": challenge.title,
        "description": challenge.description,
        "start_date": challenge.start_date,
        "end_date": challenge.end_date,
        "exp_reward": challenge.exp_reward
    }


@router.put("/challenges/{challenge_id}", dependencies=[Depends(get_current_superuser)])
async def update_challenge(
    request: Request,
    challenge_id: int,
    challenge_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Update a challenge (Admin only)"""
    
    challenge_result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = challenge_result.scalar_one_or_none()
    if not challenge:
        raise NotFoundException("Challenge not found")
    
    challenge.title = challenge_data.get("title", challenge.title)
    challenge.description = challenge_data.get("description", challenge.description)
    challenge.start_date = challenge_data.get("start_date", challenge.start_date)
    challenge.end_date = challenge_data.get("end_date", challenge.end_date)
    challenge.exp_reward = challenge_data.get("exp_reward", challenge.exp_reward)
    
    await db.commit()
    
    return {"message": "Challenge updated successfully"}


@router.delete("/challenges/{challenge_id}", dependencies=[Depends(get_current_superuser)])
async def delete_challenge(
    request: Request,
    challenge_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Delete a challenge (Admin only)"""
    
    challenge_result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
    challenge = challenge_result.scalar_one_or_none()
    if not challenge:
        raise NotFoundException("Challenge not found")
    
    # Delete all user challenges first
    await db.execute(delete(UserChallenge).where(UserChallenge.challenge_id == challenge_id))
    
    # Delete the challenge
    db.delete(challenge)
    await db.commit()
    
    return {"message": "Challenge deleted successfully"}


@router.get("/admin/challenges/stats", dependencies=[Depends(get_current_superuser)], response_model=dict)
async def get_challenges_stats(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Get challenge statistics (Admin only)"""
    
    today = date.today()
    
    # Get total challenges
    total_challenges = (await db.execute(select(func.count()).select_from(Challenge))).scalar() or 0
    
    # Get active challenges
    active_challenges = (await db.execute(
        select(func.count()).select_from(Challenge).where(
            Challenge.start_date <= today,
            Challenge.end_date >= today
        )
    )).scalar() or 0
    
    # Get upcoming challenges
    upcoming_challenges = (await db.execute(
        select(func.count()).select_from(Challenge).where(Challenge.start_date > today)
    )).scalar() or 0
    
    # Get expired challenges
    expired_challenges = (await db.execute(
        select(func.count()).select_from(Challenge).where(Challenge.end_date < today)
    )).scalar() or 0
    
    # Get total participants
    total_participants = (await db.execute(select(func.count()).select_from(UserChallenge))).scalar() or 0
    
    # Get completed challenges
    completed_participations = (await db.execute(
        select(func.count()).select_from(UserChallenge).where(UserChallenge.is_completed == True)
    )).scalar() or 0
    
    # Get most popular challenges
    popular_stmt = (
        select(UserChallenge.challenge_id, func.count(UserChallenge.id).label('count'))
        .group_by(UserChallenge.challenge_id)
        .order_by(func.count(UserChallenge.id).desc())
        .limit(5)
    )
    popular_result = await db.execute(popular_stmt)
    popular_challenges = popular_result.all()
    
    popular_challenges_data = []
    for challenge_id, count in popular_challenges:
        challenge_result = await db.execute(select(Challenge).where(Challenge.id == challenge_id))
        challenge = challenge_result.scalar_one_or_none()
        if challenge:
            popular_challenges_data.append({
                "id": challenge.id,
                "title": challenge.title,
                "participants_count": count
            })
    
    return {
        "total_challenges": total_challenges,
        "active_challenges": active_challenges,
        "upcoming_challenges": upcoming_challenges,
        "expired_challenges": expired_challenges,
        "total_participants": total_participants,
        "completed_participations": completed_participations,
        "completion_rate": (completed_participations / total_participants * 100) if total_participants > 0 else 0,
        "most_popular_challenges": popular_challenges_data
    }
