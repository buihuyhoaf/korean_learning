# src/app/api/v1/badges.py
from typing import Annotated, Any, cast
from uuid import UUID
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, Request
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException, ForbiddenException, DuplicateValueException
from ...models.user import User
from ...models.gamification import Badge, UserBadge

router = APIRouter(tags=["badges"])


# UC8: Earn Badges
@router.get("/badges", response_model=PaginatedListResponse[dict])
async def get_all_badges(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 20,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get all available badges with user's earned status"""
    
    offset = compute_offset(page, items_per_page)
    
    # Get all badges
    badges_query = db.query(Badge).order_by(Badge.created_at.desc())
    badges = badges_query.offset(offset).limit(items_per_page).all()
    total = badges_query.count()
    
    # Get user's earned badges if authenticated
    user_earned_badges = set()
    if current_user:
        earned_badges = db.query(UserBadge).filter(UserBadge.user_id == current_user["id"]).all()
        user_earned_badges = {eb.badge_id for eb in earned_badges}
    
    badges_data = []
    for badge in badges:
        badge_dict = {
            "id": badge.id,
            "name": badge.name,
            "description": badge.description,
            "icon_url": badge.icon_url,
            "created_at": badge.created_at,
            "is_earned": badge.id in user_earned_badges,
            "earned_at": None
        }
        
        # Get earned date if user has this badge
        if badge.id in user_earned_badges and current_user:
            user_badge = db.query(UserBadge).filter(
                UserBadge.user_id == current_user["id"],
                UserBadge.badge_id == badge.id
            ).first()
            if user_badge:
                badge_dict["earned_at"] = user_badge.earned_at
        
        badges_data.append(badge_dict)
    
    response = paginated_response(
        crud_data={"data": badges_data, "total": total},
        page=page,
        items_per_page=items_per_page
    )
    return response


@router.get("/user/{username}/badges", response_model=PaginatedListResponse[dict])
async def get_user_badges(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 20,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get user's earned badges"""
    
    # Check permissions
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own badges")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    offset = compute_offset(page, items_per_page)
    
    # Get user's earned badges
    badges_query = db.query(UserBadge).filter(UserBadge.user_id == user.id).order_by(UserBadge.earned_at.desc())
    user_badges = badges_query.offset(offset).limit(items_per_page).all()
    total = badges_query.count()
    
    badges_data = []
    for user_badge in user_badges:
        badge = db.query(Badge).filter(Badge.id == user_badge.badge_id).first()
        if badge:
            badge_dict = {
                "id": badge.id,
                "name": badge.name,
                "description": badge.description,
                "icon_url": badge.icon_url,
                "earned_at": user_badge.earned_at,
                "created_at": badge.created_at
            }
            badges_data.append(badge_dict)
    
    response = paginated_response(
        crud_data={"data": badges_data, "total": total},
        page=page,
        items_per_page=items_per_page
    )
    return response


@router.get("/user/{username}/badges/summary", response_model=dict)
async def get_user_badges_summary(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get user's badge summary and statistics"""
    
    # Check permissions
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own badge summary")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    # Get total badges available
    total_badges = db.query(Badge).count()
    
    # Get user's earned badges
    earned_badges = db.query(UserBadge).filter(UserBadge.user_id == user.id).all()
    earned_count = len(earned_badges)
    
    # Get recent badges (last 5)
    recent_badges = db.query(UserBadge).filter(UserBadge.user_id == user.id).order_by(
        UserBadge.earned_at.desc()
    ).limit(5).all()
    
    recent_badges_data = []
    for user_badge in recent_badges:
        badge = db.query(Badge).filter(Badge.id == user_badge.badge_id).first()
        if badge:
            recent_badges_data.append({
                "id": badge.id,
                "name": badge.name,
                "description": badge.description,
                "icon_url": badge.icon_url,
                "earned_at": user_badge.earned_at
            })
    
    # Calculate completion percentage
    completion_percentage = (earned_count / total_badges * 100) if total_badges > 0 else 0
    
    return {
        "total_badges": total_badges,
        "earned_badges": earned_count,
        "completion_percentage": round(completion_percentage, 2),
        "recent_badges": recent_badges_data,
        "next_badges": get_next_available_badges(user.id, db)
    }


@router.post("/user/{username}/badges/{badge_id}/earn", response_model=dict)
async def earn_badge(
    request: Request,
    username: str,
    badge_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Earn a badge (usually called by system when conditions are met)"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only earn badges for yourself")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    badge = db.query(Badge).filter(Badge.id == badge_id).first()
    if not badge:
        raise NotFoundException("Badge not found")
    
    # Check if user already has this badge
    existing_user_badge = db.query(UserBadge).filter(
        UserBadge.user_id == user.id,
        UserBadge.badge_id == badge_id
    ).first()
    
    if existing_user_badge:
        raise DuplicateValueException("User already has this badge")
    
    # Create user badge
    user_badge = UserBadge(
        user_id=user.id,
        badge_id=badge_id,
        earned_at=datetime.now(UTC)
    )
    db.add(user_badge)
    
    # Add EXP bonus for earning badge
    badge_exp_bonus = 50  # Standard badge EXP bonus
    user.exp += badge_exp_bonus
    
    # Log EXP gain
    from ...models.gamification import UserExpLog
    exp_log = UserExpLog(
        user_id=user.id,
        source="badge_earned",
        amount=badge_exp_bonus
    )
    db.add(exp_log)
    
    db.commit()
    
    return {
        "message": f"Congratulations! You earned the '{badge.name}' badge!",
        "badge": {
            "id": badge.id,
            "name": badge.name,
            "description": badge.description,
            "icon_url": badge.icon_url,
            "earned_at": user_badge.earned_at
        },
        "exp_bonus": badge_exp_bonus
    }


@router.get("/badges/{badge_id}", response_model=dict)
async def get_badge_details(
    request: Request,
    badge_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get detailed information about a specific badge"""
    
    badge = db.query(Badge).filter(Badge.id == badge_id).first()
    if not badge:
        raise NotFoundException("Badge not found")
    
    # Get users who have earned this badge
    users_with_badge = db.query(UserBadge).filter(UserBadge.badge_id == badge_id).count()
    
    # Check if current user has this badge
    user_has_badge = False
    earned_at = None
    if current_user:
        user_badge = db.query(UserBadge).filter(
            UserBadge.user_id == current_user["id"],
            UserBadge.badge_id == badge_id
        ).first()
        if user_badge:
            user_has_badge = True
            earned_at = user_badge.earned_at
    
    return {
        "id": badge.id,
        "name": badge.name,
        "description": badge.description,
        "icon_url": badge.icon_url,
        "created_at": badge.created_at,
        "users_earned": users_with_badge,
        "user_has_badge": user_has_badge,
        "user_earned_at": earned_at
    }


def get_next_available_badges(user_id: UUID, db: AsyncSession) -> list:
    """Get badges that user hasn't earned yet"""
    # Get all badges
    all_badges = db.query(Badge).all()
    
    # Get user's earned badges
    earned_badge_ids = db.query(UserBadge.badge_id).filter(UserBadge.user_id == user_id).all()
    earned_badge_ids = {eb[0] for eb in earned_badge_ids}
    
    # Filter unearned badges
    unearned_badges = [badge for badge in all_badges if badge.id not in earned_badge_ids]
    
    # Return first 5 unearned badges
    return [
        {
            "id": badge.id,
            "name": badge.name,
            "description": badge.description,
            "icon_url": badge.icon_url
        }
        for badge in unearned_badges[:5]
    ]


# Admin endpoints for UC16: Manage Badges
@router.post("/badges", dependencies=[Depends(get_current_superuser)], status_code=201)
async def create_badge(
    request: Request,
    badge_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Create a new badge (Admin only)"""
    
    badge = Badge(
        name=badge_data["name"],
        description=badge_data["description"],
        icon_url=badge_data.get("icon_url")
    )
    db.add(badge)
    db.commit()
    db.refresh(badge)
    
    return {
        "id": badge.id,
        "name": badge.name,
        "description": badge.description,
        "icon_url": badge.icon_url,
        "created_at": badge.created_at
    }


@router.put("/badges/{badge_id}", dependencies=[Depends(get_current_superuser)])
async def update_badge(
    request: Request,
    badge_id: int,
    badge_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Update a badge (Admin only)"""
    
    badge = db.query(Badge).filter(Badge.id == badge_id).first()
    if not badge:
        raise NotFoundException("Badge not found")
    
    badge.name = badge_data.get("name", badge.name)
    badge.description = badge_data.get("description", badge.description)
    badge.icon_url = badge_data.get("icon_url", badge.icon_url)
    
    db.commit()
    
    return {"message": "Badge updated successfully"}


@router.delete("/badges/{badge_id}", dependencies=[Depends(get_current_superuser)])
async def delete_badge(
    request: Request,
    badge_id: int,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Delete a badge (Admin only)"""
    
    badge = db.query(Badge).filter(Badge.id == badge_id).first()
    if not badge:
        raise NotFoundException("Badge not found")
    
    # Delete all user badges first
    db.query(UserBadge).filter(UserBadge.badge_id == badge_id).delete()
    
    # Delete the badge
    db.delete(badge)
    db.commit()
    
    return {"message": "Badge deleted successfully"}


@router.get("/admin/badges/stats", dependencies=[Depends(get_current_superuser)], response_model=dict)
async def get_badges_stats(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Get badge statistics (Admin only)"""
    
    # Get total badges
    total_badges = db.query(Badge).count()
    
    # Get total badge awards
    total_awards = db.query(UserBadge).count()
    
    # Get most popular badges
    popular_badges = db.query(UserBadge.badge_id, func.count(UserBadge.id).label('count')).group_by(
        UserBadge.badge_id
    ).order_by(func.count(UserBadge.id).desc()).limit(10).all()
    
    popular_badges_data = []
    for badge_id, count in popular_badges:
        badge = db.query(Badge).filter(Badge.id == badge_id).first()
        if badge:
            popular_badges_data.append({
                "id": badge.id,
                "name": badge.name,
                "description": badge.description,
                "icon_url": badge.icon_url,
                "award_count": count
            })
    
    # Get users with most badges
    top_users = db.query(UserBadge.user_id, func.count(UserBadge.id).label('badge_count')).group_by(
        UserBadge.user_id
    ).order_by(func.count(UserBadge.id).desc()).limit(10).all()
    
    top_users_data = []
    for user_id, badge_count in top_users:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            top_users_data.append({
                "user_id": user.id,
                "username": user.username,
                "badge_count": badge_count
            })
    
    return {
        "total_badges": total_badges,
        "total_awards": total_awards,
        "average_awards_per_badge": total_awards / total_badges if total_badges > 0 else 0,
        "most_popular_badges": popular_badges_data,
        "top_users_by_badges": top_users_data
    }
