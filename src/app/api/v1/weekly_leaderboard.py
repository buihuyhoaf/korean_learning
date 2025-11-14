"""
Weekly Leaderboard API

Endpoints for managing weekly leaderboard with 19 dummy users + 1 real user.
"""
import random
import hashlib
from typing import Annotated
from datetime import date, timedelta, datetime, UTC
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload

from ...api.dependencies import get_current_user, get_current_superuser, get_optional_user
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
from ...core.logger import logging

logger = logging.getLogger(__name__)

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
        
        # Baseline streak_days: random between 1-365 (follow similar algorithm to XP)
        baseline_streak_days = [random.randint(1, 365) for _ in range(19)]
        
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
            dummy_streak_days = baseline_streak_days[i]
            
            # Save to Redis
            dummy_data = {
                "xp": dummy_xp,
                "name": shuffled_names[i],
                "avatar": shuffled_avatars[i],
                "country": shuffled_countries[i],
                "phase": 1 if dummy_id in phase1_pool else 0,
                "pool": "phase1_pool" if dummy_id in phase1_pool else None,
                "baseline_xp": dummy_xp,
                "streak_days": dummy_streak_days
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
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> WeeklyLeaderboardResponse:
    """Get current week's leaderboard - Always includes current user in top 20"""
    # Get optional user (doesn't require authentication)
    current_user = await get_optional_user(request, db)
    logger.info(f"[Leaderboard] current_user: {current_user is not None}, has token: {request.headers.get('Authorization') is not None}")
    
    week_start = get_week_start()
    
    # Get all entries for this week, sorted by XP descending
    # Eager load user relationship to avoid N+1 queries
    query = select(WeeklyLeaderboard).options(
        selectinload(WeeklyLeaderboard.user)
    ).where(
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
    
    # Re-rank ALL entries (not just top 20) to get accurate ranks
    entries = sorted(entries, key=lambda e: e.xp, reverse=True)
    previous_xp = None
    current_rank = 0
    
    for entry in entries:
        # Handle ties - same rank for same XP
        if previous_xp is not None and previous_xp == entry.xp:
            entry.rank = current_rank
        else:
            current_rank += 1
            entry.rank = current_rank
        previous_xp = entry.xp
    
    # Save ranks to DB (only top 20 to avoid unnecessary updates)
    await db.commit()
    
    # Find current user entry in ALL entries, create if not exists
    user_id = None
    current_user_entry = None
    current_user_rank = None
    rank_change = None
    
    if current_user:
        user_id = UUID(str(current_user["id"]))
        logger.info(f"[Leaderboard] Looking for user entry: user_id={user_id}, week_start={week_start}, user_email={current_user.get('email', 'N/A')}")
        
        # Find user entry in existing entries
        for entry in entries:
            if not entry.is_dummy and entry.user_id == user_id:
                current_user_entry = entry
                
                # FIX LỖI 1: Tính lại XP từ UserExpLog để đảm bảo chính xác
                week_start_datetime = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=UTC)
                week_xp_query = select(func.sum(UserExpLog.amount)).where(
                    UserExpLog.user_id == user_id,
                    UserExpLog.created_at >= week_start_datetime
                )
                week_xp_result = await db.execute(week_xp_query)
                recalculated_week_xp = week_xp_result.scalar() or 0
                
                # Cập nhật XP nếu khác với giá trị cũ
                if entry.xp != recalculated_week_xp:
                    logger.info(f"[Leaderboard] Updating XP: {entry.xp} -> {recalculated_week_xp}")
                    entry.xp = recalculated_week_xp
                    entry.updated_at = datetime.now(UTC)
                    
                    # Re-sort và re-rank lại sau khi cập nhật XP
                    entries = sorted(entries, key=lambda e: e.xp, reverse=True)
                    previous_xp = None
                    new_rank = 0
                    for e in entries:
                        if previous_xp is not None and previous_xp == e.xp:
                            e.rank = new_rank
                        else:
                            new_rank += 1
                            e.rank = new_rank
                        previous_xp = e.xp
                    
                    # Cập nhật lại current_user_rank sau khi re-rank
                    current_user_rank = entry.rank
                    # Flush để đảm bảo thay đổi được ghi nhận trong session
                    await db.flush()
                else:
                    current_user_rank = entry.rank
                
                logger.info(f"[Leaderboard] Found existing user entry: rank={entry.rank}, xp={entry.xp}")
                # Get previous rank from Redis or DB
                previous_rank = await WeeklyLeaderboardRedis.get_previous_rank(
                    week_start, 
                    str(user_id)
                )
                if previous_rank:
                    rank_change = previous_rank - entry.rank  # Positive = moved up
                    logger.info(f"[Leaderboard] Rank change: {previous_rank} -> {entry.rank} (change={rank_change})")
                # Update Redis with current rank
                await WeeklyLeaderboardRedis.set_previous_rank(
                    week_start,
                    str(user_id),
                    entry.rank
                )
                break
        
        # If user entry doesn't exist, create it with 0 XP
        if not current_user_entry:
            logger.info(f"[Leaderboard] User entry not found, creating new entry for user_id={user_id}")
            # Get user info
            user_query = select(User).where(User.id == user_id)
            user_result = await db.execute(user_query)
            user = user_result.scalar_one_or_none()
            
            if user:
                # Calculate week XP from UserExpLog
                week_start_datetime = datetime.combine(week_start, datetime.min.time()).replace(tzinfo=UTC)
                week_xp_query = select(func.sum(UserExpLog.amount)).where(
                    UserExpLog.user_id == user_id,
                    UserExpLog.created_at >= week_start_datetime
                )
                week_xp_result = await db.execute(week_xp_query)
                week_xp = week_xp_result.scalar() or 0
                
                # Get baseline XP
                baseline_query = select(func.sum(UserExpLog.amount)).where(
                    UserExpLog.user_id == user_id,
                    UserExpLog.created_at < week_start_datetime
                )
                baseline_result = await db.execute(baseline_query)
                baseline_xp = baseline_result.scalar() or 0
                
                # Create entry with current week XP
                current_user_entry = WeeklyLeaderboard(
                    week_start=week_start,
                    user_id=user_id,
                    is_dummy=False,
                    name=user.username or user.email or "User",
                    avatar=user.picture,
                    country=None,
                    xp=week_xp,
                    xp_week_start=baseline_xp,
                    rank=21  # Will be updated after re-ranking
                )
                db.add(current_user_entry)
                await db.flush()
                
                # Re-add to entries list and re-sort
                entries.append(current_user_entry)
                entries = sorted(entries, key=lambda e: e.xp, reverse=True)
                
                # Re-rank all entries
                previous_xp = None
                new_rank = 0
                for entry in entries:
                    if previous_xp is not None and previous_xp == entry.xp:
                        entry.rank = new_rank
                    else:
                        new_rank += 1
                        entry.rank = new_rank
                    previous_xp = entry.xp
                
                # Update current_user_entry rank
                current_user_rank = current_user_entry.rank
                logger.info(f"[Leaderboard] Created new user entry: rank={current_user_rank}, xp={current_user_entry.xp}")
                
                await db.commit()
    
    # Build top 20 entries: lấy top 19 entries (bỏ qua user entry), thêm user entry, sắp xếp lại
    leaderboard_entries = []
    
    # Re-sort entries after potential new user entry creation
    entries = sorted(entries, key=lambda e: e.xp, reverse=True)
    
    # Lấy top 19 entries, bỏ qua user entry nếu có
    top_19_entries = []
    for entry in entries:
        # Bỏ qua user entry (sẽ thêm lại sau)
        if current_user_entry and user_id and not entry.is_dummy and entry.user_id == user_id:
            continue
        
        if len(top_19_entries) < 19:
            top_19_entries.append(entry)
        else:
            break
    
    # Thêm user entry vào và sắp xếp lại
    if current_user_entry:
        top_19_entries.append(current_user_entry)
        top_20_entries = sorted(top_19_entries, key=lambda e: e.xp, reverse=True)
        logger.info(f"[Leaderboard] Added user entry to top 19, total entries: {len(top_20_entries)}")
    else:
        # Nếu không có user entry, chỉ lấy top 19
        top_20_entries = top_19_entries
        logger.warning(f"[Leaderboard] No current_user_entry found, showing top {len(top_20_entries)} entries only")
    
    # User luôn có trong top 20 nếu có current_user_entry
    user_in_top_20 = current_user_entry is not None
    
    # Build response entries
    for index, entry in enumerate(top_20_entries):
        # FIX: Đảm bảo is_current_user luôn là boolean, không bao giờ None
        is_current_user = bool(
            user_id and 
            not entry.is_dummy and 
            entry.user_id == user_id
        )
        
        # Calculate rank change for current user
        entry_rank_change = None
        if is_current_user and rank_change is not None:
            entry_rank_change = rank_change
        
        # FIX LỖI 2: Tính displayed_rank dựa trên vị trí trong list (xử lý ties)
        # Sau khi đã sắp xếp lại top_20_entries, chỉ cần tính rank dựa trên vị trí và XP
        displayed_rank = index + 1
        if index > 0:
            # Nếu entry trước có cùng XP, dùng cùng rank (xử lý ties)
            prev_entry = top_20_entries[index - 1]
            if prev_entry.xp == entry.xp:
                # Tìm rank của entry đầu tiên có cùng XP
                for i in range(index - 1, -1, -1):
                    if top_20_entries[i].xp != entry.xp:
                        displayed_rank = i + 2
                        break
                    if i == 0:
                        displayed_rank = 1
                        break
        
        # Cập nhật current_user_rank để nhất quán với displayed_rank
        if is_current_user:
            current_user_rank = displayed_rank
        
        # Get streak_days from User if entry has user_id, or from Redis if dummy
        entry_streak_days = None
        if not entry.is_dummy and entry.user_id and entry.user:
            entry_streak_days = entry.user.streak_days
        elif entry.is_dummy and entry.dummy_id:
            # Get streak_days from Redis for dummy users
            dummy_data = await WeeklyLeaderboardRedis.get_dummy(week_start, entry.dummy_id)
            if dummy_data:
                if "streak_days" in dummy_data and dummy_data["streak_days"] is not None:
                    entry_streak_days = dummy_data["streak_days"]
                else:
                    # Generate streak_days if missing (follow algorithm)
                    streak_seed = int(hashlib.md5(f"{week_start.isoformat()}_{entry.dummy_id}".encode()).hexdigest()[:8], 16) % (2**31)
                    random.seed(streak_seed)
                    entry_streak_days = random.randint(1, 365)
                    # Save back to Redis
                    if "streak_days" not in dummy_data:
                        dummy_data["streak_days"] = entry_streak_days
                        await WeeklyLeaderboardRedis.set_dummy(week_start, entry.dummy_id, dummy_data)
        
        leaderboard_entries.append(
            LeaderboardEntry(
                id=entry.id,
                rank=displayed_rank,
                name=entry.name,
                avatar=entry.avatar,
                country=entry.country,
                xp=entry.xp,
                is_dummy=entry.is_dummy,
                is_current_user=is_current_user,
                rank_change=entry_rank_change,
                streak_days=entry_streak_days
            )
        )
    
    return WeeklyLeaderboardResponse(
        week_start=week_start,
        entries=leaderboard_entries,
        current_user_rank=current_user_rank,  # Actual rank, not displayed rank
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

