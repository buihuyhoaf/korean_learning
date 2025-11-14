"""
Weekly Leaderboard API

Endpoints for managing weekly leaderboard with 19 dummy users + 1 real user.
"""
import random
from typing import Annotated
from datetime import date, timedelta, datetime, UTC
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException
from ...models.user import User
from ...models.social import WeeklyLeaderboard
from ...models.gamification import UserExpLog
from ...schemas.weekly_leaderboard import (
    WeeklyLeaderboardResponse,
    LeaderboardEntry,
    WeeklyLeaderboardUpdateRequest,
    WeeklyLeaderboardUpdateResponse
)
from ...core.utils.weekly_leaderboard_redis import WeeklyLeaderboardRedis

router = APIRouter(tags=["weekly_leaderboard"])

# Dummy names pool (can be expanded)
DUMMY_NAMES = [
    "KoreanMaster123", "SeoulLearner", "HangulHero", "KPopFan2024",
    "BTSArmy", "KimchiLover", "GangnamStyle", "KdramaQueen",
    "KoreanFoodie", "SeoulExplorer", "HallyuStar", "HangulKing",
    "KBeautyLover", "SeoulWalker", "HangulNinja", "KPopStar",
    "KoreanStudent", "SeoulDreamer", "HangulMaster", "KdramaFan"
]

# Avatar pool
AVATAR_POOL = [f"avatar_{i}" for i in range(1, 21)]

# Country codes
COUNTRIES = ["KR", "US", "JP", "CN", "VN", "TH", "ID", "PH", "MY", "SG"]


def get_week_start(target_date: date = None) -> date:
    """Get Monday of the week for a given date"""
    if target_date is None:
        target_date = date.today()
    # Monday is 0, Sunday is 6
    days_since_monday = target_date.weekday()
    return target_date - timedelta(days=days_since_monday)


async def initialize_weekly_leaderboard(
    db: AsyncSession,
    week_start: date
) -> None:
    """Initialize weekly leaderboard with 19 dummy users"""
    
    # Generate deterministic seed based on week_start
    seed = hash(week_start.isoformat()) % (2**31)
    random.seed(seed)
    
    # Get state from Redis or create new
    state = await WeeklyLeaderboardRedis.get_state(week_start)
    
    if not state:
        # Create 19 dummy users
        dummy_ids = [f"dummy_{i}" for i in range(1, 20)]
        
        # Shuffle pools for this week
        shuffled_names = random.sample(DUMMY_NAMES, 19)
        shuffled_avatars = random.sample(AVATAR_POOL, 19)
        shuffled_countries = random.choices(COUNTRIES, k=19)
        
        # Baseline XP: random between 500-2000
        baseline_xp = [random.randint(500, 2000) for _ in range(19)]
        
        # Select Phase 1 pool (10 dummies)
        phase1_pool = random.sample(dummy_ids, 10)
        
        # Save state to Redis
        state = {
            "week_start": week_start.isoformat(),
            "seed": seed,
            "phase": 0,
            "day_of_week": 0,
            "phase1_pool": phase1_pool,
            "phase2_pool": [],
            "phase3_pool": [],
            "last_update": datetime.now(UTC).isoformat()
        }
        await WeeklyLeaderboardRedis.set_state(week_start, state)
        
        # Create dummy entries in DB
        for i, dummy_id in enumerate(dummy_ids):
            dummy_xp = baseline_xp[i]
            
            # Save to Redis
            dummy_data = {
                "xp": dummy_xp,
                "name": shuffled_names[i],
                "avatar": shuffled_avatars[i],
                "country": shuffled_countries[i],
                "phase": 1 if dummy_id in phase1_pool else 0,
                "pool": "phase1_pool" if dummy_id in phase1_pool else None,
                "baseline_xp": dummy_xp
            }
            await WeeklyLeaderboardRedis.set_dummy(week_start, dummy_id, dummy_data)
            
            # Create DB entry
            entry = WeeklyLeaderboard(
                week_start=week_start,
                user_id=None,
                is_dummy=True,
                dummy_id=dummy_id,
                name=shuffled_names[i],
                avatar=shuffled_avatars[i],
                country=shuffled_countries[i],
                xp=dummy_xp,
                rank=i + 1  # Temporary, will be re-ranked
            )
            db.add(entry)
        
        await db.commit()
    
    # Re-rank entries
    await rerank_weekly_leaderboard(db, week_start)


async def rerank_weekly_leaderboard(
    db: AsyncSession,
    week_start: date
) -> None:
    """Re-rank all entries by XP"""
    query = select(WeeklyLeaderboard).where(
        WeeklyLeaderboard.week_start == week_start
    ).order_by(desc(WeeklyLeaderboard.xp))
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    # Assign ranks (handle ties with jitter)
    previous_xp = None
    previous_rank = 0
    
    for entry in entries[:20]:
        # Add jitter to avoid exact ties
        if previous_xp is not None and previous_xp == entry.xp:
            entry.rank = previous_rank
        else:
            previous_rank += 1
            entry.rank = previous_rank
        previous_xp = entry.xp
    
    await db.commit()


@router.get("/leaderboard/weekly", response_model=WeeklyLeaderboardResponse)
async def get_weekly_leaderboard(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> WeeklyLeaderboardResponse:
    """Get current week's leaderboard"""
    week_start = get_week_start()
    
    # Get all entries for this week, sorted by XP descending
    query = select(WeeklyLeaderboard).where(
        WeeklyLeaderboard.week_start == week_start
    ).order_by(desc(WeeklyLeaderboard.xp))
    
    result = await db.execute(query)
    entries = result.scalars().all()
    
    # If no entries exist, initialize the week
    if not entries:
        await initialize_weekly_leaderboard(db, week_start)
        # Re-fetch entries
        result = await db.execute(query)
        entries = result.scalars().all()
    
    # Re-rank entries (in case of XP changes)
    entries = sorted(entries, key=lambda e: e.xp, reverse=True)
    for rank, entry in enumerate(entries[:20], 1):
        entry.rank = rank
    
    # Save ranks to DB
    await db.commit()
    
    # Build response
    leaderboard_entries = []
    current_user_entry = None
    current_user_rank = None
    rank_change = None
    
    user_id = None
    if current_user:
        user_id = UUID(str(current_user["id"]))
    
    for entry in entries[:20]:
        is_current_user = (
            user_id and 
            not entry.is_dummy and 
            entry.user_id == user_id
        )
        
        # Calculate rank change for current user
        entry_rank_change = None
        if is_current_user:
            current_user_entry = entry
            current_user_rank = entry.rank
            # Get previous rank from Redis or DB
            previous_rank = await WeeklyLeaderboardRedis.get_previous_rank(
                week_start, 
                str(user_id)
            )
            if previous_rank:
                rank_change = previous_rank - entry.rank  # Positive = moved up
                entry_rank_change = rank_change
            # Update Redis with current rank
            await WeeklyLeaderboardRedis.set_previous_rank(
                week_start,
                str(user_id),
                entry.rank
            )
        
        leaderboard_entries.append(
            LeaderboardEntry(
                id=entry.id,
                rank=entry.rank,
                name=entry.name,
                avatar=entry.avatar,
                country=entry.country,
                xp=entry.xp,
                is_dummy=entry.is_dummy,
                is_current_user=is_current_user,
                rank_change=entry_rank_change
            )
        )
    
    return WeeklyLeaderboardResponse(
        week_start=week_start,
        entries=leaderboard_entries,
        current_user_rank=current_user_rank,
        current_user_xp=current_user_entry.xp if current_user_entry else None,
        rank_change=rank_change
    )


@router.post("/leaderboard/weekly/update-xp", response_model=WeeklyLeaderboardUpdateResponse)
async def update_user_xp(
    request: Request,
    payload: WeeklyLeaderboardUpdateRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> WeeklyLeaderboardUpdateResponse:
    """Update user's XP in weekly leaderboard"""
    user_id = UUID(str(current_user["id"]))
    week_start = get_week_start()
    
    # Get or create user's entry
    query = select(WeeklyLeaderboard).where(
        WeeklyLeaderboard.week_start == week_start,
        WeeklyLeaderboard.user_id == user_id,
        WeeklyLeaderboard.is_dummy == False
    )
    result = await db.execute(query)
    entry = result.scalar_one_or_none()
    
    if not entry:
        # Get user info
        user_query = select(User).where(User.id == user_id)
        user_result = await db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise NotFoundException("User not found")
        
        # Calculate week XP (total XP - XP at week start)
        # Get user's XP at week start (from UserExpLog)
        week_start_datetime = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=UTC)
        week_xp_query = select(func.sum(UserExpLog.amount)).where(
            UserExpLog.user_id == user_id,
            UserExpLog.created_at >= week_start_datetime
        )
        week_xp_result = await db.execute(week_xp_query)
        week_xp = week_xp_result.scalar() or 0
        
        # Get user's baseline XP (XP before week start)
        baseline_query = select(func.sum(UserExpLog.amount)).where(
            UserExpLog.user_id == user_id,
            UserExpLog.created_at < week_start_datetime
        )
        baseline_result = await db.execute(baseline_query)
        baseline_xp = baseline_result.scalar() or 0
        
        # Create entry
        entry = WeeklyLeaderboard(
            week_start=week_start,
            user_id=user_id,
            is_dummy=False,
            name=user.username,
            avatar=user.picture,
            country=None,  # Could add country to User model
            xp=week_xp + payload.exp,
            xp_week_start=baseline_xp,
            rank=21  # Will be updated after re-ranking
        )
        db.add(entry)
        await db.flush()
    else:
        # Update existing entry
        entry.xp += payload.exp
        entry.updated_at = datetime.now(UTC)
    
    # Re-rank all entries
    await rerank_weekly_leaderboard(db, week_start)
    
    # Get updated entry
    await db.refresh(entry)
    
    # Calculate rank change
    previous_rank = await WeeklyLeaderboardRedis.get_previous_rank(
        week_start, 
        str(user_id)
    )
    rank_change = None
    if previous_rank:
        rank_change = previous_rank - entry.rank
    
    # Update Redis cache
    await WeeklyLeaderboardRedis.set_previous_rank(
        week_start,
        str(user_id),
        entry.rank
    )
    
    await db.commit()
    
    return WeeklyLeaderboardUpdateResponse(
        message="XP updated successfully",
        current_xp=entry.xp,
        current_rank=entry.rank,
        rank_change=rank_change
    )


@router.post("/admin/leaderboard/weekly/simulate", dependencies=[Depends(get_current_superuser)])
async def simulate_daily_update(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Manually trigger daily dummy XP update (Admin only)"""
    from ...core.worker.functions import update_weekly_leaderboard_dummy_xp
    from arq.worker import Worker
    
    # Run the update function manually
    try:
        # Create a dummy worker context
        ctx = Worker(ctx={})
        result = await update_weekly_leaderboard_dummy_xp(ctx)
        return {
            "message": "Weekly leaderboard updated successfully",
            "result": result
        }
    except Exception as e:
        return {
            "message": "Error updating weekly leaderboard",
            "error": str(e)
        }

