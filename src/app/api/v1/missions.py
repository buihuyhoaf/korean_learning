"""
Daily Missions API

Endpoints for managing daily missions and tracking activities.
"""
import random
from typing import Annotated
from datetime import datetime, UTC, date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ...api.dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException
from ...models.user import User
from ...models.gamification import DailyMission, UserExpLog
from ...schemas.mission import (
    TodayMissionsResponse,
    MissionResponse,
    ActivityRequest,
    ActivityResponse,
    ExpRequest,
    ExpResponse
)

router = APIRouter(tags=["missions"])


async def _generate_daily_missions(
    db: AsyncSession,
    user_id: UUID,
    target_date: date
) -> list[DailyMission]:
    """Generate 3 random missions for a day"""
    mission_types = ["lesson", "speaking", "listening"]
    # Target values: random between 1-3
    target_options = [1, 2, 3]
    
    missions = []
    for i, mission_type in enumerate(mission_types):
        mission = DailyMission(
            user_id=user_id,
            mission_id=f"m{i+1}",
            type=mission_type,
            target=random.choice(target_options),
            date=target_date
        )
        missions.append(mission)
        db.add(mission)
    
    await db.commit()
    
    # Refresh to get IDs
    for mission in missions:
        await db.refresh(mission)
    
    return missions


@router.get("/missions/today", response_model=TodayMissionsResponse)
async def get_today_missions(
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> TodayMissionsResponse:
    """Get today's missions for current user. Auto-generates if not exists."""
    user_id = UUID(str(current_user["id"]))
    today = date.today()
    
    # Check existing missions
    missions_query = select(DailyMission).filter(
        DailyMission.user_id == user_id,
        DailyMission.date == today
    )
    missions_result = await db.execute(missions_query)
    existing_missions = missions_result.scalars().all()
    
    if not existing_missions:
        # Generate new missions
        existing_missions = await _generate_daily_missions(db, user_id, today)
    
    return TodayMissionsResponse(
        missions=[
            MissionResponse(
                mission_id=mission.mission_id,
                type=mission.type,
                target=mission.target,
                progress=mission.progress,
                is_completed=mission.is_completed
            )
            for mission in existing_missions
        ]
    )


@router.post("/activity", response_model=ActivityResponse)
async def track_activity(
    payload: ActivityRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> ActivityResponse:
    """Track user activity and update mission progress"""
    user_id = UUID(str(current_user["id"]))
    today = date.today()
    
    # Get active missions for this type
    missions_query = select(DailyMission).filter(
        DailyMission.user_id == user_id,
        DailyMission.date == today,
        DailyMission.type == payload.type,
        DailyMission.is_completed == False
    )
    missions_result = await db.execute(missions_query)
    missions = missions_result.scalars().all()
    
    completed_mission = None
    for mission in missions:
        mission.progress += 1
        if mission.progress >= mission.target:
            mission.is_completed = True
            mission.completed_at = datetime.now(UTC)
            completed_mission = mission
    
    await db.commit()
    
    if completed_mission:
        # Calculate expires_at (15 minutes from now)
        expires_at_ms = int((datetime.now(UTC) + timedelta(minutes=15)).timestamp() * 1000)
        return ActivityResponse(
            mission_completed=True,
            mission_id=completed_mission.mission_id,
            expires_at=expires_at_ms
        )
    
    return ActivityResponse(mission_completed=False)


@router.post("/exp", response_model=ExpResponse)
async def add_exp(
    payload: ExpRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> ExpResponse:
    """Add EXP to user (already multiplied by client)"""
    user_id = UUID(str(current_user["id"]))
    
    user_query = select(User).filter(User.id == user_id)
    user_result = await db.execute(user_query)
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise NotFoundException("User not found")
    
    user.exp += payload.exp
    
    exp_log = UserExpLog(
        user_id=user_id,
        source="lesson_activity",  # or "mission_bonus"
        amount=payload.exp
    )
    db.add(exp_log)
    await db.commit()
    
    return ExpResponse(
        message="EXP added",
        total_exp=user.exp
    )

