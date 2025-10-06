# src/app/api/v1/leaderboard.py
from typing import Annotated, Any, cast
from datetime import datetime, UTC, date

from fastapi import APIRouter, Depends, Request
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException, ForbiddenException
from ...models.user import User
from ...models.social import Leaderboard

router = APIRouter(tags=["leaderboard"])


# UC12: View Leaderboard
@router.get("/leaderboard", response_model=PaginatedListResponse[dict])
async def get_leaderboard(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 50,
    season: str = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get global leaderboard"""
    
    offset = compute_offset(page, items_per_page)
    
    # Build query
    if season:
        # Get leaderboard for specific season
        query = db.query(Leaderboard).filter(Leaderboard.season == season)
    else:
        # Get current season leaderboard (most recent)
        query = db.query(Leaderboard).order_by(Leaderboard.season.desc())
    
    query = query.order_by(Leaderboard.rank.asc())
    
    leaderboard_entries = query.offset(offset).limit(items_per_page).all()
    total = query.count()
    
    leaderboard_data = []
    for entry in leaderboard_entries:
        user = db.query(User).filter(User.id == entry.user_id).first()
        if user:
            entry_dict = {
                "rank": entry.rank,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "exp": user.exp,
                    "streak_days": user.streak_days
                },
                "season": entry.season,
                "exp": entry.exp,
                "updated_at": entry.updated_at
            }
            leaderboard_data.append(entry_dict)
    
    # Get current user's rank if authenticated
    user_rank = None
    if current_user:
        user_entry = db.query(Leaderboard).filter(
            Leaderboard.user_id == current_user["id"],
            Leaderboard.season == (season or get_current_season())
        ).first()
        
        if user_entry:
            user_rank = {
                "rank": user_entry.rank,
                "exp": user_entry.exp,
                "season": user_entry.season
            }
    
    response = paginated_response(
        crud_data={"data": leaderboard_data, "total": total},
        page=page,
        items_per_page=items_per_page
    )
    response["user_rank"] = user_rank
    
    return response


@router.get("/leaderboard/friends", response_model=dict)
async def get_friends_leaderboard(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)],
    season: str = None
) -> dict:
    """Get friends leaderboard"""
    
    if not current_user:
        raise ForbiddenException("Authentication required to view friends leaderboard")
    
    user = db.query(User).filter(User.username == current_user["username"]).first()
    if not user:
        raise NotFoundException("User not found")
    
    current_season = season or get_current_season()
    
    # Get user's friends
    from ...models.social import Friend
    friends_query = db.query(Friend).filter(
        Friend.user_id == user.id,
        Friend.status == "accepted"
    )
    friends = friends_query.all()
    
    # Get friend user IDs
    friend_user_ids = [friend.friend_user_id for friend in friends]
    
    # Add current user to the list
    friend_user_ids.append(user.id)
    
    # Get leaderboard entries for friends
    leaderboard_entries = db.query(Leaderboard).filter(
        Leaderboard.user_id.in_(friend_user_ids),
        Leaderboard.season == current_season
    ).order_by(Leaderboard.rank.asc()).all()
    
    friends_leaderboard = []
    for entry in leaderboard_entries:
        friend_user = db.query(User).filter(User.id == entry.user_id).first()
        if friend_user:
            entry_dict = {
                "rank": entry.rank,
                "user": {
                    "id": friend_user.id,
                    "username": friend_user.username,
                    "exp": friend_user.exp,
                    "streak_days": friend_user.streak_days,
                    "is_current_user": friend_user.id == user.id
                },
                "exp": entry.exp,
                "updated_at": entry.updated_at
            }
            friends_leaderboard.append(entry_dict)
    
    return {
        "season": current_season,
        "friends_leaderboard": friends_leaderboard,
        "total_friends": len(friends)
    }


@router.get("/leaderboard/seasons", response_model=dict)
async def get_leaderboard_seasons(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Get available leaderboard seasons"""
    
    seasons_query = db.query(Leaderboard.season).distinct().order_by(Leaderboard.season.desc())
    seasons = [season[0] for season in seasons_query.all()]
    
    return {
        "seasons": seasons,
        "current_season": get_current_season()
    }


@router.get("/user/{username}/leaderboard-history", response_model=PaginatedListResponse[dict])
async def get_user_leaderboard_history(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 10,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get user's leaderboard history across seasons"""
    
    # Check permissions
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own leaderboard history")
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    offset = compute_offset(page, items_per_page)
    
    # Get user's leaderboard entries
    entries_query = db.query(Leaderboard).filter(
        Leaderboard.user_id == user.id
    ).order_by(Leaderboard.season.desc())
    
    entries = entries_query.offset(offset).limit(items_per_page).all()
    total = entries_query.count()
    
    history_data = []
    for entry in entries:
        entry_dict = {
            "season": entry.season,
            "rank": entry.rank,
            "exp": entry.exp,
            "updated_at": entry.updated_at
        }
        history_data.append(entry_dict)
    
    response = paginated_response(
        crud_data={"data": history_data, "total": total},
        page=page,
        items_per_page=items_per_page
    )
    return response


def get_current_season() -> str:
    """Get current season identifier"""
    now = datetime.now(UTC)
    year = now.year
    month = now.month
    
    # Define seasons (3-month periods)
    if month <= 3:
        return f"{year}-Q1"
    elif month <= 6:
        return f"{year}-Q2"
    elif month <= 9:
        return f"{year}-Q3"
    else:
        return f"{year}-Q4"


def update_leaderboard(db: AsyncSession, season: str = None) -> None:
    """Update leaderboard for a season"""
    if not season:
        season = get_current_season()
    
    # Get all users ordered by EXP
    users = db.query(User).order_by(User.exp.desc()).all()
    
    # Clear existing leaderboard for this season
    db.query(Leaderboard).filter(Leaderboard.season == season).delete()
    
    # Create new leaderboard entries
    for rank, user in enumerate(users, 1):
        leaderboard_entry = Leaderboard(
            user_id=user.id,
            season=season,
            rank=rank,
            exp=user.exp,
            updated_at=datetime.now(UTC)
        )
        db.add(leaderboard_entry)
    
    db.commit()


# Admin endpoints for UC17: Monitor Leaderboard
@router.post("/admin/leaderboard/update", dependencies=[Depends(get_current_superuser)], response_model=dict)
async def update_leaderboard_admin(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    season: str = None
) -> dict:
    """Update leaderboard (Admin only)"""
    
    if not season:
        season = get_current_season()
    
    update_leaderboard(db, season)
    
    return {
        "message": f"Leaderboard updated for season {season}",
        "season": season,
        "updated_at": datetime.now(UTC)
    }


@router.get("/admin/leaderboard/stats", dependencies=[Depends(get_current_superuser)], response_model=dict)
async def get_leaderboard_stats(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Get leaderboard statistics (Admin only)"""
    
    # Get total users
    total_users = db.query(User).count()
    
    # Get leaderboard entries by season
    seasons_query = db.query(Leaderboard.season, func.count(Leaderboard.id).label('count')).group_by(
        Leaderboard.season
    ).order_by(Leaderboard.season.desc())
    
    seasons_stats = []
    for season, count in seasons_query.all():
        seasons_stats.append({
            "season": season,
            "participants": count
        })
    
    # Get top performers across all seasons
    top_performers = db.query(
        Leaderboard.user_id,
        func.avg(Leaderboard.rank).label('avg_rank'),
        func.max(Leaderboard.exp).label('max_exp')
    ).group_by(Leaderboard.user_id).order_by(
        func.avg(Leaderboard.rank).asc()
    ).limit(10).all()
    
    top_performers_data = []
    for user_id, avg_rank, max_exp in top_performers:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            top_performers_data.append({
                "user_id": user.id,
                "username": user.username,
                "average_rank": round(avg_rank, 2),
                "max_exp": max_exp
            })
    
    # Get current season stats
    current_season = get_current_season()
    current_season_participants = db.query(Leaderboard).filter(
        Leaderboard.season == current_season
    ).count()
    
    return {
        "total_users": total_users,
        "current_season": current_season,
        "current_season_participants": current_season_participants,
        "seasons_stats": seasons_stats,
        "top_performers": top_performers_data
    }


@router.get("/admin/leaderboard/{season}/details", dependencies=[Depends(get_current_superuser)], response_model=dict)
async def get_season_leaderboard_details(
    request: Request,
    season: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 100
) -> dict:
    """Get detailed leaderboard for a specific season (Admin only)"""
    
    offset = compute_offset(page, items_per_page)
    
    # Get leaderboard entries for the season
    entries_query = db.query(Leaderboard).filter(
        Leaderboard.season == season
    ).order_by(Leaderboard.rank.asc())
    
    entries = entries_query.offset(offset).limit(items_per_page).all()
    total = entries_query.count()
    
    entries_data = []
    for entry in entries:
        user = db.query(User).filter(User.id == entry.user_id).first()
        if user:
            entry_dict = {
                "rank": entry.rank,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "exp": user.exp,
                    "streak_days": user.streak_days,
                    "created_at": user.created_at
                },
                "exp": entry.exp,
                "updated_at": entry.updated_at
            }
            entries_data.append(entry_dict)
    
    return {
        "season": season,
        "data": entries_data,
        "total": total,
        "page": page,
        "items_per_page": items_per_page,
        "total_pages": (total + items_per_page - 1) // items_per_page
    }
