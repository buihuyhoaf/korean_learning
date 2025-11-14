import asyncio
import hashlib
import logging
import random
from datetime import date, datetime, UTC

import uvloop
from arq.worker import Worker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)


# -------- background tasks --------
async def sample_background_task(ctx: Worker, name: str) -> str:
    await asyncio.sleep(5)
    return f"Task {name} is complete!"


async def update_weekly_leaderboard_dummy_xp(ctx: Worker) -> str:
    """Daily cron job to update dummy XP based on phase"""
    from ...core.db.database import local_session
    from ...api.v1.weekly_leaderboard import (
        get_week_start,
        rerank_weekly_leaderboard,
    )
    from ...models.social import WeeklyLeaderboard
    from ...core.utils.weekly_leaderboard_redis import WeeklyLeaderboardRedis
    
    async with local_session() as db:
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
                
                # Ensure streak_days exists (create if missing, following algorithm)
                if "streak_days" not in dummy_data or dummy_data.get("streak_days") is None:
                    # Generate deterministic streak_days based on dummy_id and week_start
                    streak_seed = int(hashlib.md5(f"{week_start.isoformat()}_{entry.dummy_id}".encode()).hexdigest()[:8], 16) % (2**31)
                    random.seed(streak_seed)
                    dummy_data["streak_days"] = random.randint(1, 365)
                
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
            
            logger.info(f"Weekly leaderboard updated for {week_start}, phase {phase}")
            return f"Weekly leaderboard updated for {week_start}, phase {phase}"
            
        except Exception as e:
            logger.exception(f"Error updating weekly leaderboard: {e}")
            await db.rollback()
            raise


# -------- base functions --------
async def startup(ctx: Worker) -> None:
    logging.info("Worker Started")


async def shutdown(ctx: Worker) -> None:
    logging.info("Worker end")
