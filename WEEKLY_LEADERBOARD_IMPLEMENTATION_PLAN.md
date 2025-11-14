# Weekly Leaderboard Implementation Plan

## 📋 Tổng quan

### Mục tiêu
Tạo leaderboard tuần gồm 20 người (1 user thật + 19 dummy). User thấy được vị trí hiện tại và thay đổi thứ hạng so với lần truy cập trước. Dummy tăng XP theo thuật toán để leaderboard trông cạnh tranh và thật.

### Key Features
- **Weekly reset**: Leaderboard reset mỗi tuần (bắt đầu thứ 2)
- **19 Dummy users**: Tạo competitive environment với dummy có avatar, tên, quốc tịch
- **XP progression algorithm**: Dummy tăng XP theo 3 phase trong tuần
- **Rank tracking**: Tính ΔRank (rank change) cho user thật
- **Deterministic seed**: Đảm bảo consistency trong tuần
- **Real-time updates**: Cron job cập nhật dummy XP mỗi ngày

---

## 🗄️ Phase 1: Database Schema (Backend)

### 1.1 Tạo Migration

**File:** `migrations/versions/YYYYMMDDHHMMSS_create_weekly_leaderboard.py`

```python
"""create weekly_leaderboard table

Revision ID: create_weekly_leaderboard
Revises: [previous_revision]
Create Date: YYYY-MM-DD HH:MM:SS
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    op.create_table(
        'weekly_leaderboard',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('week_start', sa.Date(), nullable=False),  # Monday of the week
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),  # None if dummy
        sa.Column('is_dummy', sa.Boolean(), nullable=False),
        sa.Column('dummy_id', sa.String(20), nullable=True),  # "dummy_1", "dummy_2", ...
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('avatar', sa.String(500), nullable=True),
        sa.Column('country', sa.String(10), nullable=True),  # Country code: "KR", "US", etc.
        sa.Column('xp', sa.Integer(), nullable=False, default=0),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('rank_previous', sa.Integer(), nullable=True),  # Previous rank for real users
        sa.Column('xp_week_start', sa.Integer(), nullable=True),  # User's XP at week start
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('week_start', 'user_id', 'is_dummy', 'dummy_id', 
                          name='unique_weekly_entry')
    )
    op.create_index('idx_weekly_leaderboard_week_rank', 
                   'weekly_leaderboard', 
                   ['week_start', 'rank'])
    op.create_index('idx_weekly_leaderboard_user_week', 
                   'weekly_leaderboard', 
                   ['user_id', 'week_start'], 
                   unique=False, 
                   postgresql_where=sa.text('is_dummy = false'))
    op.create_index('idx_weekly_leaderboard_dummy_week', 
                   'weekly_leaderboard', 
                   ['dummy_id', 'week_start'], 
                   unique=False, 
                   postgresql_where=sa.text('is_dummy = true'))

def downgrade():
    op.drop_table('weekly_leaderboard')
```

### 1.2 Tạo Model

**File:** `src/app/models/social.py` (thêm vào)

```python
class WeeklyLeaderboard(Base):
    __tablename__ = "weekly_leaderboard"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, init=False)
    week_start: Mapped[date] = mapped_column(Date, nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    is_dummy: Mapped[bool] = mapped_column(Boolean, nullable=False)
    dummy_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    avatar: Mapped[str | None] = mapped_column(String(500), nullable=True)
    country: Mapped[str | None] = mapped_column(String(10), nullable=True)
    xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    rank_previous: Mapped[int | None] = mapped_column(Integer, nullable=True)
    xp_week_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), init=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default_factory=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    # Relationships
    user = relationship("User", back_populates="weekly_leaderboard")

    __table_args__ = (
        UniqueConstraint('week_start', 'user_id', 'is_dummy', 'dummy_id', name='unique_weekly_entry'),
    )
```

**File:** `src/app/models/user.py` (thêm vào relationships)

```python
weekly_leaderboard = relationship("WeeklyLeaderboard", back_populates="user")
```

---

## 🗂️ Phase 2: Redis State Management

### 2.1 Dummy State Structure

**Redis Keys:**
- `weekly_leaderboard:state:{week_start}`: JSON chứa seed, pools, phase info
- `weekly_leaderboard:dummy:{week_start}:{dummy_id}`: JSON chứa XP, name, avatar, country, phase, pool
- `weekly_leaderboard:rank:{week_start}:{user_id}`: Previous rank của user thật

**Redis Data Structure:**
```python
# State structure
{
    "week_start": "2024-01-01",
    "seed": 12345,
    "phase": 1,  # 0-2: Phase 1, 3-5: Phase 2, 6: Phase 3
    "day_of_week": 2,  # 0-6 (Monday = 0)
    "phase1_pool": ["dummy_1", "dummy_2", ...],  # 10 dummies
    "phase2_pool": ["dummy_1", "dummy_3", ...],  # 4 dummies from phase1
    "phase3_pool": ["dummy_1", "dummy_5"],  # 2 dummies from phase2
    "last_update": "2024-01-02T00:00:00Z"
}

# Individual dummy structure
{
    "xp": 1500,
    "name": "KoreanMaster123",
    "avatar": "avatar_1",
    "country": "KR",
    "phase": 1,
    "pool": "phase1_pool",
    "baseline_xp": 1200
}
```

### 2.2 Redis Helper Functions

**File:** `src/app/core/utils/weekly_leaderboard_redis.py` (mới)

```python
import json
from datetime import date
from typing import Optional, Dict, List
from redis.asyncio import Redis

from ...core.utils.rate_limit import rate_limiter

class WeeklyLeaderboardRedis:
    """Helper class for managing weekly leaderboard state in Redis"""
    
    @staticmethod
    def _get_state_key(week_start: date) -> str:
        return f"weekly_leaderboard:state:{week_start.isoformat()}"
    
    @staticmethod
    def _get_dummy_key(week_start: date, dummy_id: str) -> str:
        return f"weekly_leaderboard:dummy:{week_start.isoformat()}:{dummy_id}"
    
    @staticmethod
    def _get_rank_key(week_start: date, user_id: str) -> str:
        return f"weekly_leaderboard:rank:{week_start.isoformat()}:{user_id}"
    
    @staticmethod
    async def get_state(week_start: date) -> Optional[Dict]:
        """Get weekly leaderboard state"""
        client = rate_limiter.get_client()
        key = WeeklyLeaderboardRedis._get_state_key(week_start)
        data = await client.get(key)
        if data:
            return json.loads(data)
        return None
    
    @staticmethod
    async def set_state(week_start: date, state: Dict, ttl: int = 604800) -> None:
        """Set weekly leaderboard state (TTL: 7 days)"""
        client = rate_limiter.get_client()
        key = WeeklyLeaderboardRedis._get_state_key(week_start)
        await client.setex(key, ttl, json.dumps(state))
    
    @staticmethod
    async def get_dummy(week_start: date, dummy_id: str) -> Optional[Dict]:
        """Get dummy user state"""
        client = rate_limiter.get_client()
        key = WeeklyLeaderboardRedis._get_dummy_key(week_start, dummy_id)
        data = await client.get(key)
        if data:
            return json.loads(data)
        return None
    
    @staticmethod
    async def set_dummy(week_start: date, dummy_id: str, dummy_data: Dict, ttl: int = 604800) -> None:
        """Set dummy user state"""
        client = rate_limiter.get_client()
        key = WeeklyLeaderboardRedis._get_dummy_key(week_start, dummy_id)
        await client.setex(key, ttl, json.dumps(dummy_data))
    
    @staticmethod
    async def get_previous_rank(week_start: date, user_id: str) -> Optional[int]:
        """Get user's previous rank from cache"""
        client = rate_limiter.get_client()
        key = WeeklyLeaderboardRedis._get_rank_key(week_start, str(user_id))
        rank = await client.get(key)
        return int(rank) if rank else None
    
    @staticmethod
    async def set_previous_rank(week_start: date, user_id: str, rank: int, ttl: int = 604800) -> None:
        """Set user's rank for next comparison"""
        client = rate_limiter.get_client()
        key = WeeklyLeaderboardRedis._get_rank_key(week_start, str(user_id))
        await client.setex(key, ttl, str(rank))
```

---

## 🔌 Phase 3: Backend API Endpoints

### 3.1 Tạo Schemas

**File:** `src/app/schemas/weekly_leaderboard.py` (mới)

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date
from uuid import UUID

class LeaderboardEntry(BaseModel):
    id: UUID
    rank: int
    name: str
    avatar: Optional[str] = None
    country: Optional[str] = None
    xp: int
    is_dummy: bool
    is_current_user: bool = False
    rank_change: Optional[int] = None  # Only for current user

class WeeklyLeaderboardResponse(BaseModel):
    week_start: date
    entries: list[LeaderboardEntry]
    current_user_rank: Optional[int] = None
    current_user_xp: Optional[int] = None
    rank_change: Optional[int] = None  # Positive = up, Negative = down, None = no change
    
class WeeklyLeaderboardUpdateRequest(BaseModel):
    exp: int = Field(..., description="New EXP earned")

class WeeklyLeaderboardUpdateResponse(BaseModel):
    message: str
    current_xp: int
    current_rank: int
    rank_change: Optional[int] = None
```

### 3.2 Tạo API Router

**File:** `src/app/api/v1/weekly_leaderboard.py` (mới)

#### 3.2.1 GET `/api/v1/leaderboard/weekly`

**Chức năng:**
- Lấy leaderboard tuần hiện tại (top 20)
- Tính ΔRank cho user thật
- Trả về entries sorted by rank

**Logic:**
```python
from datetime import date, timedelta
from typing import Annotated
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from ...api.dependencies import get_current_user, async_get_db
from ...models.social import WeeklyLeaderboard
from ...models.user import User
from ...models.gamification import UserExpLog
from ...schemas.weekly_leaderboard import WeeklyLeaderboardResponse, LeaderboardEntry
from ...core.utils.weekly_leaderboard_redis import WeeklyLeaderboardRedis
from uuid import UUID

router = APIRouter(tags=["weekly_leaderboard"])

def get_week_start(target_date: date = None) -> date:
    """Get Monday of the week for a given date"""
    if target_date is None:
        target_date = date.today()
    # Monday is 0, Sunday is 6
    days_since_monday = target_date.weekday()
    return target_date - timedelta(days=days_since_monday)

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
    
    for entry in entries[:20]:
        is_current_user = (
            current_user and 
            not entry.is_dummy and 
            entry.user_id == UUID(str(current_user["id"]))
        )
        
        # Calculate rank change for current user
        entry_rank_change = None
        if is_current_user:
            current_user_entry = entry
            current_user_rank = entry.rank
            # Get previous rank from Redis or DB
            previous_rank = await WeeklyLeaderboardRedis.get_previous_rank(
                week_start, 
                str(current_user["id"])
            )
            if previous_rank:
                rank_change = previous_rank - entry.rank  # Positive = moved up
                entry_rank_change = rank_change
            # Update Redis with current rank
            await WeeklyLeaderboardRedis.set_previous_rank(
                week_start,
                str(current_user["id"]),
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
```

#### 3.2.2 POST `/api/v1/leaderboard/weekly/update-xp`

**Chức năng:**
- Cập nhật XP cho user thật
- Tính lại rank và ΔRank
- Gọi từ app khi user hoàn thành bài học

**Logic:**
```python
@router.post("/leaderboard/weekly/update-xp", response_model=WeeklyLeaderboardUpdateResponse)
async def update_user_xp(
    request: Request,
    payload: WeeklyLeaderboardUpdateRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> WeeklyLeaderboardUpdateResponse:
    """Update user's XP in weekly leaderboard"""
    from datetime import datetime, UTC
    from sqlalchemy import func
    
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
        week_start_datetime = datetime.combine(week_start, datetime.min.time())
        week_xp_query = select(func.sum(UserExpLog.amount)).where(
            UserExpLog.user_id == user_id,
            UserExpLog.created_at >= week_start_datetime.replace(tzinfo=UTC)
        )
        week_xp_result = await db.execute(week_xp_query)
        week_xp = week_xp_result.scalar() or 0
        
        # Get user's baseline XP (XP before week start)
        baseline_query = select(func.sum(UserExpLog.amount)).where(
            UserExpLog.user_id == user_id,
            UserExpLog.created_at < week_start_datetime.replace(tzinfo=UTC)
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
```

### 3.3 Helper Functions

**File:** `src/app/api/v1/weekly_leaderboard.py` (thêm vào)

```python
import random
from datetime import date, timedelta, datetime, UTC
from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

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
```

---

## ⏰ Phase 4: Cron Job - Daily Dummy XP Update

### 4.1 ARQ Worker Function

**File:** `src/app/core/worker/functions.py` (thêm vào)

```python
async def update_weekly_leaderboard_dummy_xp(ctx: Worker) -> str:
    """Daily cron job to update dummy XP based on phase"""
    from datetime import date, datetime, UTC
    from sqlalchemy.ext.asyncio import AsyncSession
    from ...core.db.database import async_get_db
    from ...api.v1.weekly_leaderboard import (
        get_week_start,
        rerank_weekly_leaderboard,
        WeeklyLeaderboardRedis
    )
    from ...models.social import WeeklyLeaderboard
    from sqlalchemy import select
    import random
    
    async for db in async_get_db():
        try:
            week_start = get_week_start()
            today = date.today()
            day_of_week = today.weekday()  # 0 = Monday, 6 = Sunday
            
            # Determine phase
            if day_of_week < 3:
                phase = 1  # Days 0-2
            elif day_of_week < 6:
                phase = 2  # Days 3-5
            else:
                phase = 3  # Day 6
            
            # Get state
            state = await WeeklyLeaderboardRedis.get_state(week_start)
            if not state:
                # Initialize if not exists
                from ...api.v1.weekly_leaderboard import initialize_weekly_leaderboard
                await initialize_weekly_leaderboard(db, week_start)
                state = await WeeklyLeaderboardRedis.get_state(week_start)
            
            # Update phase pools if needed
            if phase == 2 and not state.get("phase2_pool"):
                # Select 4 from phase1_pool
                phase1_pool = state.get("phase1_pool", [])
                state["phase2_pool"] = random.sample(phase1_pool, min(4, len(phase1_pool)))
                await WeeklyLeaderboardRedis.set_state(week_start, state)
            
            if phase == 3 and not state.get("phase3_pool"):
                # Select 2 from phase2_pool
                phase2_pool = state.get("phase2_pool", [])
                state["phase3_pool"] = random.sample(phase2_pool, min(2, len(phase2_pool)))
                await WeeklyLeaderboardRedis.set_state(week_start, state)
            
            # Get all dummy entries
            query = select(WeeklyLeaderboard).where(
                WeeklyLeaderboard.week_start == week_start,
                WeeklyLeaderboard.is_dummy == True
            )
            result = await db.execute(query)
            dummy_entries = result.scalars().all()
            
            # Set seed for deterministic updates
            random.seed(state.get("seed", 0))
            
            # Update XP based on phase
            for entry in dummy_entries:
                dummy_data = await WeeklyLeaderboardRedis.get_dummy(week_start, entry.dummy_id)
                if not dummy_data:
                    continue
                
                # Determine XP increase
                xp_increase = 0
                if phase == 1:
                    if entry.dummy_id in state.get("phase1_pool", []):
                        # Phase 1 pool: 50-150 XP
                        xp_increase = random.randint(50, 150)
                    else:
                        # Others: 10-50 XP
                        xp_increase = random.randint(10, 50)
                elif phase == 2:
                    if entry.dummy_id in state.get("phase2_pool", []):
                        # Phase 2 pool: 150-300 XP
                        xp_increase = random.randint(150, 300)
                    else:
                        # Others: 10-50 XP
                        xp_increase = random.randint(10, 50)
                elif phase == 3:
                    if entry.dummy_id in state.get("phase3_pool", []):
                        # Phase 3 pool: 300-500 XP
                        xp_increase = random.randint(300, 500)
                    else:
                        # Others: 10-50 XP
                        xp_increase = random.randint(10, 50)
                
                # Add small jitter to avoid exact ties
                jitter = random.randint(-5, 5)
                xp_increase = max(0, xp_increase + jitter)
                
                # Update XP
                entry.xp += xp_increase
                dummy_data["xp"] = entry.xp
                dummy_data["phase"] = phase
                
                # Save to Redis
                await WeeklyLeaderboardRedis.set_dummy(week_start, entry.dummy_id, dummy_data)
            
            # Re-rank
            await rerank_weekly_leaderboard(db, week_start)
            
            # Update state
            state["phase"] = phase
            state["day_of_week"] = day_of_week
            state["last_update"] = datetime.now(UTC).isoformat()
            await WeeklyLeaderboardRedis.set_state(week_start, state)
            
            await db.commit()
            
            return f"Weekly leaderboard updated for {week_start}, phase {phase}"
            
        except Exception as e:
            logging.error(f"Error updating weekly leaderboard: {e}")
            raise
        finally:
            break
```

### 4.2 Update Worker Settings

**File:** `src/app/core/worker/settings.py` (update)

```python
from arq.connections import RedisSettings
from arq.cron import CronJob

from ...core.config import settings
from .functions import (
    sample_background_task, 
    shutdown, 
    startup,
    update_weekly_leaderboard_dummy_xp
)

REDIS_QUEUE_HOST = settings.REDIS_QUEUE_HOST
REDIS_QUEUE_PORT = settings.REDIS_QUEUE_PORT


class WorkerSettings:
    functions = [sample_background_task]
    redis_settings = RedisSettings(host=REDIS_QUEUE_HOST, port=REDIS_QUEUE_PORT)
    on_startup = startup
    on_shutdown = shutdown
    handle_signals = False
    
    # Cron jobs - run daily at 00:00 UTC
    cron_jobs = [
        CronJob(
            update_weekly_leaderboard_dummy_xp,
            minute=0,
            hour=0,
            run_at_startup=False
        )
    ]
```

### 4.3 Admin Endpoint for Manual Trigger

**File:** `src/app/api/v1/weekly_leaderboard.py` (thêm vào)

```python
from ...api.dependencies import get_current_superuser

@router.post("/admin/leaderboard/weekly/simulate", dependencies=[Depends(get_current_superuser)])
async def simulate_daily_update(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Manually trigger daily dummy XP update (Admin only)"""
    from ...core.worker.functions import update_weekly_leaderboard_dummy_xp
    
    # Run the update function
    result = await update_weekly_leaderboard_dummy_xp(None)
    
    return {
        "message": "Weekly leaderboard updated",
        "result": result
    }
```

---

## 📱 Phase 5: Android App - Data Layer

### 5.1 API Models

**File:** `app/src/main/java/com/seoulhankuko/app/data/api/model/WeeklyLeaderboardModels.kt` (mới)

```kotlin
package com.seoulhankuko.app.data.api.model

import com.google.gson.annotations.SerializedName

// Leaderboard Entry
data class LeaderboardEntry(
    val id: String,
    val rank: Int,
    val name: String,
    val avatar: String? = null,
    val country: String? = null,
    val xp: Int,
    @SerializedName("is_dummy")
    val isDummy: Boolean,
    @SerializedName("is_current_user")
    val isCurrentUser: Boolean = false,
    @SerializedName("rank_change")
    val rankChange: Int? = null  // Positive = up, Negative = down
)

// Weekly Leaderboard Response
data class WeeklyLeaderboardResponse(
    @SerializedName("week_start")
    val weekStart: String,  // ISO date format
    val entries: List<LeaderboardEntry>,
    @SerializedName("current_user_rank")
    val currentUserRank: Int? = null,
    @SerializedName("current_user_xp")
    val currentUserXp: Int? = null,
    @SerializedName("rank_change")
    val rankChange: Int? = null
)

// Update XP Request
data class WeeklyLeaderboardUpdateRequest(
    val exp: Int
)

// Update XP Response
data class WeeklyLeaderboardUpdateResponse(
    val message: String,
    @SerializedName("current_xp")
    val currentXp: Int,
    @SerializedName("current_rank")
    val currentRank: Int,
    @SerializedName("rank_change")
    val rankChange: Int? = null
)
```

### 5.2 API Service

**File:** `app/src/main/java/com/seoulhankuko/app/data/api/service/ApiService.kt` (thêm vào)

```kotlin
// Weekly Leaderboard endpoints
@GET("v1/leaderboard/weekly")
suspend fun getWeeklyLeaderboard(
    @Header("Authorization") token: String? = null
): Response<WeeklyLeaderboardResponse>

@POST("v1/leaderboard/weekly/update-xp")
suspend fun updateWeeklyLeaderboardXp(
    @Header("Authorization") token: String? = null,
    @Body body: WeeklyLeaderboardUpdateRequest
): Response<WeeklyLeaderboardUpdateResponse>
```

### 5.3 Repository

**File:** `app/src/main/java/com/seoulhankuko/app/data/repository/WeeklyLeaderboardRepository.kt` (mới)

```kotlin
package com.seoulhankuko.app.data.repository

import com.seoulhankuko.app.data.api.model.*
import com.seoulhankuko.app.data.api.service.ApiService
import javax.inject.Inject

class WeeklyLeaderboardRepository @Inject constructor(
    private val apiService: ApiService
) {
    suspend fun getWeeklyLeaderboard(token: String?): Result<WeeklyLeaderboardResponse> {
        return try {
            val response = apiService.getWeeklyLeaderboard(token)
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Failed to get weekly leaderboard"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    suspend fun updateXp(exp: Int, token: String?): Result<WeeklyLeaderboardUpdateResponse> {
        return try {
            val response = apiService.updateWeeklyLeaderboardXp(
                token, 
                WeeklyLeaderboardUpdateRequest(exp = exp)
            )
            if (response.isSuccessful && response.body() != null) {
                Result.success(response.body()!!)
            } else {
                Result.failure(Exception("Failed to update XP"))
            }
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
}
```

---

## 🎨 Phase 6: Android App - UI

### 6.1 Update LeaderboardScreen

**File:** `app/src/main/java/com/seoulhankuko/app/presentation/screens/LeaderboardScreen.kt` (update)

```kotlin
@Composable
fun LeaderboardScreen(
    onNavigateBack: () -> Unit,
    weeklyLeaderboardViewModel: WeeklyLeaderboardViewModel = hiltViewModel()
) {
    val leaderboard by weeklyLeaderboardViewModel.leaderboard.collectAsStateWithLifecycle()
    val isLoading by weeklyLeaderboardViewModel.isLoading.collectAsStateWithLifecycle()
    val error by weeklyLeaderboardViewModel.error.collectAsStateWithLifecycle()
    
    LaunchedEffect(Unit) {
        weeklyLeaderboardViewModel.loadLeaderboard()
    }
    
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp)
    ) {
        // Header
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            TextButton(onClick = onNavigateBack) {
                Text("← Back")
            }
            
            Text(
                text = "🏆 Weekly Leaderboard",
                style = MaterialTheme.typography.headlineLarge,
                fontWeight = FontWeight.Bold
            )
            
            Spacer(modifier = Modifier.width(80.dp))
        }
        
        Spacer(modifier = Modifier.height(32.dp))
        
        if (isLoading) {
            CircularProgressIndicator(modifier = Modifier.align(Alignment.CenterHorizontally))
        } else if (error != null) {
            Text(
                text = "Error: $error",
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(16.dp)
            )
        } else {
            leaderboard?.let { data ->
                // Current user rank card
                if (data.currentUserRank != null) {
                    CurrentUserRankCard(
                        rank = data.currentUserRank,
                        xp = data.currentUserXp ?: 0,
                        rankChange = data.rankChange
                    )
                }
                
                Spacer(modifier = Modifier.height(24.dp))
                
                // Leaderboard list
                Text(
                    text = "Top 20:",
                    style = MaterialTheme.typography.titleLarge,
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(bottom = 16.dp)
                )
                
                LazyColumn(
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(data.entries) { entry ->
                        LeaderboardEntryCard(
                            entry = entry,
                            isHighlighted = entry.isCurrentUser
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun CurrentUserRankCard(
    rank: Int,
    xp: Int,
    rankChange: Int?
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.primaryContainer
        )
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "Your Rank:",
                        style = MaterialTheme.typography.titleMedium
                    )
                    Text(
                        text = "#$rank",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary
                    )
                    Text(
                        text = "$xp XP",
                        style = MaterialTheme.typography.bodyMedium
                    )
                }
                
                // Rank change indicator
                rankChange?.let { change ->
                    RankChangeIndicator(change = change)
                }
            }
        }
    }
}

@Composable
fun RankChangeIndicator(change: Int) {
    val (icon, color, text) = when {
        change > 0 -> Triple("↑", Color(0xFF4CAF50), "+$change")  // Green
        change < 0 -> Triple("↓", Color(0xFFF44336), "$change")    // Red
        else -> Triple("→", Color(0xFF757575), "0")                // Gray
    }
    
    Row(
        verticalAlignment = Alignment.CenterVertically,
        horizontalArrangement = Arrangement.spacedBy(4.dp)
    ) {
        Text(
            text = icon,
            style = MaterialTheme.typography.titleLarge,
            color = color
        )
        Text(
            text = text,
            style = MaterialTheme.typography.titleMedium,
            color = color,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
fun LeaderboardEntryCard(
    entry: LeaderboardEntry,
    isHighlighted: Boolean = false
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(
            containerColor = if (isHighlighted) 
                MaterialTheme.colorScheme.secondaryContainer 
            else 
                MaterialTheme.colorScheme.surface
        ),
        border = if (isHighlighted) 
            BorderStroke(2.dp, MaterialTheme.colorScheme.primary) 
        else null
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(16.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            // Rank
            Text(
                text = getRankEmoji(entry.rank) ?: "#${entry.rank}",
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold
            )
            
            // Avatar + Name
            Row(
                modifier = Modifier.weight(1f).padding(horizontal = 16.dp),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Avatar (placeholder)
                Box(
                    modifier = Modifier
                        .size(40.dp)
                        .clip(CircleShape)
                        .background(MaterialTheme.colorScheme.primaryContainer),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = entry.name.take(1).uppercase(),
                        style = MaterialTheme.typography.titleMedium
                    )
                }
                
                Column {
                    Text(
                        text = entry.name,
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = if (isHighlighted) FontWeight.Bold else FontWeight.Normal
                    )
                    entry.country?.let {
                        Text(
                            text = it,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
            
            // XP
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    text = "${entry.xp} XP",
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold
                )
                if (isHighlighted && entry.rankChange != null && entry.rankChange != 0) {
                    Text(
                        text = if (entry.rankChange > 0) "+${entry.rankChange}" else "${entry.rankChange}",
                        style = MaterialTheme.typography.bodySmall,
                        color = if (entry.rankChange > 0) Color(0xFF4CAF50) else Color(0xFFF44336)
                    )
                }
            }
        }
    }
}

fun getRankEmoji(rank: Int): String? {
    return when (rank) {
        1 -> "🥇"
        2 -> "🥈"
        3 -> "🥉"
        else -> null
    }
}
```

### 6.2 ViewModel

**File:** `app/src/main/java/com/seoulhankuko/app/presentation/viewmodel/WeeklyLeaderboardViewModel.kt` (mới)

```kotlin
package com.seoulhankuko.app.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.seoulhankuko.app.data.api.model.WeeklyLeaderboardResponse
import com.seoulhankuko.app.data.repository.WeeklyLeaderboardRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class WeeklyLeaderboardViewModel @Inject constructor(
    private val repository: WeeklyLeaderboardRepository
) : ViewModel() {
    
    private val _leaderboard = MutableStateFlow<WeeklyLeaderboardResponse?>(null)
    val leaderboard: StateFlow<WeeklyLeaderboardResponse?> = _leaderboard.asStateFlow()
    
    private val _isLoading = MutableStateFlow(false)
    val isLoading: StateFlow<Boolean> = _isLoading.asStateFlow()
    
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()
    
    fun loadLeaderboard(token: String? = null) {
        viewModelScope.launch {
            _isLoading.value = true
            _error.value = null
            
            repository.getWeeklyLeaderboard(token)
                .onSuccess { response ->
                    _leaderboard.value = response
                }
                .onFailure { exception ->
                    _error.value = exception.message
                }
            
            _isLoading.value = false
        }
    }
    
    fun updateXp(exp: Int, token: String? = null) {
        viewModelScope.launch {
            repository.updateXp(exp, token)
                .onSuccess { response ->
                    // Reload leaderboard to get updated rank
                    loadLeaderboard(token)
                }
                .onFailure { exception ->
                    _error.value = exception.message
                }
        }
    }
}
```

---

## 🧪 Phase 7: Testing

### 7.1 Backend Tests

**File:** `tests/test_weekly_leaderboard_api.py` (mới)

```python
import pytest
from datetime import date, timedelta
from uuid import uuid4

@pytest.mark.asyncio
async def test_get_weekly_leaderboard(client, test_user, auth_token):
    """Test getting weekly leaderboard"""
    response = await client.get(
        "/api/v1/leaderboard/weekly",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "week_start" in data
    assert "entries" in data
    assert len(data["entries"]) == 20  # 19 dummies + 1 user
    
@pytest.mark.asyncio
async def test_update_user_xp(client, test_user, auth_token):
    """Test updating user XP"""
    response = await client.post(
        "/api/v1/leaderboard/weekly/update-xp",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"exp": 100}
    )
    assert response.status_code == 200
    data = response.json()
    assert "current_xp" in data
    assert "current_rank" in data

@pytest.mark.asyncio
async def test_rank_change_calculation(client, test_user, auth_token):
    """Test rank change calculation"""
    # First call - no previous rank
    response1 = await client.get(
        "/api/v1/leaderboard/weekly",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response1.status_code == 200
    data1 = response1.json()
    initial_rank = data1["current_user_rank"]
    
    # Update XP
    await client.post(
        "/api/v1/leaderboard/weekly/update-xp",
        headers={"Authorization": f"Bearer {auth_token}"},
        json={"exp": 500}
    )
    
    # Second call - should have rank change
    response2 = await client.get(
        "/api/v1/leaderboard/weekly",
        headers={"Authorization": f"Bearer {auth_token}"}
    )
    assert response2.status_code == 200
    data2 = response2.json()
    assert "rank_change" in data2
    assert data2["current_user_rank"] != initial_rank
```

---

## ✅ Checklist Implementation

### Backend
- [ ] Tạo migration cho `weekly_leaderboard` table
- [ ] Tạo `WeeklyLeaderboard` model
- [ ] Update User model relationship
- [ ] Tạo Redis helper functions
- [ ] Tạo schemas
- [ ] Implement `GET /api/v1/leaderboard/weekly`
- [ ] Implement `POST /api/v1/leaderboard/weekly/update-xp`
- [ ] Implement `initialize_weekly_leaderboard()` helper
- [ ] Implement `rerank_weekly_leaderboard()` helper
- [ ] Implement ARQ cron job for daily updates
- [ ] Register router trong `__init__.py`
- [ ] Update worker settings với cron job
- [ ] Run migration
- [ ] Test endpoints với Postman/curl

### Android App - Data Layer
- [ ] Tạo `WeeklyLeaderboardModels.kt`
- [ ] Thêm endpoints vào `ApiService.kt`
- [ ] Tạo `WeeklyLeaderboardRepository.kt`
- [ ] Test API calls

### Android App - Presentation Layer
- [ ] Tạo `WeeklyLeaderboardViewModel.kt`
- [ ] Update `LeaderboardScreen.kt` UI
- [ ] Tạo `CurrentUserRankCard` component
- [ ] Tạo `RankChangeIndicator` component
- [ ] Tạo `LeaderboardEntryCard` component
- [ ] Add rank change animation
- [ ] Integrate với lesson completion flow

### Integration
- [ ] Integrate XP update khi user hoàn thành bài học
- [ ] Test end-to-end flow
- [ ] Test weekly reset
- [ ] Test rank change tracking

### Testing
- [ ] Backend unit tests
- [ ] Backend integration tests
- [ ] Android unit tests
- [ ] Manual testing: check leaderboard display
- [ ] Manual testing: verify rank change
- [ ] Manual testing: weekly reset

---

## 🚀 Timeline Estimate

- **Phase 1 (Database)**: 3-4 hours
- **Phase 2 (Redis)**: 2-3 hours
- **Phase 3 (Backend API)**: 6-8 hours
- **Phase 4 (Cron Job)**: 4-5 hours
- **Phase 5 (Android Data)**: 2-3 hours
- **Phase 6 (Android UI)**: 5-7 hours
- **Phase 7 (Testing)**: 4-5 hours

**Total Estimate**: 26-35 hours (4-5 ngày làm việc)

---

## 🔍 Edge Cases & Considerations

### 1. Week Start Calculation
- Sử dụng Monday làm ngày bắt đầu tuần
- Xử lý timezone đúng (server UTC)
- Reset tuần mới vào 00:00 UTC thứ 2

### 2. User XP Calculation
- XP tuần = tổng XP từ UserExpLog trong tuần
- Hoặc dùng XP tích lũy và lưu baseline tại week_start
- Cần quyết định strategy rõ ràng

### 3. Deterministic Seed
- Seed dựa trên `week_start` để đảm bảo consistency
- Cùng seed → cùng dummy names, avatars, pools
- Jitter nhỏ để tránh tie XP

### 4. Race Conditions
- Concurrent XP updates → dùng database transaction
- Rank calculation → lock khi re-ranking
- Cron job overlap → sử dụng lock trong Redis

### 5. Dummy Pool Management
- Phase 1 pool: 10 dummies (chọn từ 19)
- Phase 2 pool: 4 dummies (chọn từ Phase 1 pool)
- Phase 3 pool: 2 dummies (chọn từ Phase 2 pool)
- Lưu pools trong Redis state

### 6. Performance
- Cache leaderboard trong Redis (TTL 5 phút)
- Index database đúng cách
- Limit query chỉ lấy top 20

### 7. User Not in Top 20
- Hiển thị rank nhưng không trong top 20 list
- Hoặc hiển thị ở cuối list với rank thực tế

---

## 📚 Notes

- **XP Strategy**: Cần quyết định dùng XP tuần (từ UserExpLog) hay XP tích lũy (user.exp)
- **Weekly Reset**: Cần xử lý reset tuần mới khi cron job chạy vào thứ 2
- **Dummy Variety**: Có thể mở rộng pools cho names, avatars, countries
- **Rank Tie**: Sử dụng jitter để tránh tie XP, nhưng vẫn cần handle edge case
- **Monitoring**: Log cron job execution và error handling
- **Future Enhancements**: 
  - Badge cho top 3
  - Historical leaderboard
  - Friends leaderboard
  - Country-based leaderboard

