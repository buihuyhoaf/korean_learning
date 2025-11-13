"""
Endpoints for registering and unregistering Firebase Cloud Messaging (FCM) tokens.
"""

from __future__ import annotations

from datetime import UTC, datetime
import logging
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_current_user
from ...core.db.database import async_get_db
from ...models.user_push_token import UserPushToken
from ...schemas.push_token import PushTokenRegisterRequest, PushTokenUnregisterRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/push-tokens", tags=["push-tokens"])


@router.post("/register", status_code=status.HTTP_200_OK)
async def register_push_token(
    payload: PushTokenRegisterRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> dict[str, str]:
    """
    Register or update an FCM token for the authenticated user.

    - If the token already exists, it will be reassigned to the current user,
      marked as active, and its metadata refreshed.
    - If the token is new, it will be stored with the current user.
    """

    user_id = uuid.UUID(str(current_user["id"]))
    now = datetime.now(UTC)
    
    logger.info(
        "📱 FCM token registration request - user_id=%s, platform=%s, token_length=%d, token_preview=%s",
        user_id,
        payload.platform,
        len(payload.token),
        payload.token[:20] + "..." if len(payload.token) > 20 else payload.token
    )

    result = await db.execute(select(UserPushToken).where(UserPushToken.token == payload.token))
    push_token = result.scalar_one_or_none()

    if push_token:
        push_token.user_id = user_id
        push_token.platform = payload.platform
        push_token.last_seen = now
        push_token.is_active = True
        logger.info("✅ Reactivated FCM token for user_id=%s platform=%s token_id=%s", user_id, payload.platform, push_token.id)
    else:
        push_token = UserPushToken(
            user_id=user_id,
            token=payload.token,
            platform=payload.platform,
            last_seen=now,
            is_active=True,
        )
        db.add(push_token)
        logger.info("✅ Registered new FCM token for user_id=%s platform=%s", user_id, payload.platform)

    await db.commit()
    
    # Verify it was saved
    verify_result = await db.execute(select(UserPushToken).where(UserPushToken.token == payload.token))
    verified_token = verify_result.scalar_one_or_none()
    if verified_token:
        logger.info("✅ Verified: Token saved successfully - id=%s, is_active=%s", verified_token.id, verified_token.is_active)
    else:
        logger.error("❌ ERROR: Token was not saved to database!")

    return {"message": "Token registered"}


@router.delete("/unregister", status_code=status.HTTP_200_OK)
async def unregister_push_token(
    payload: PushTokenUnregisterRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> dict[str, str]:
    """
    Deactivate an FCM token for the authenticated user.
    """

    user_id = uuid.UUID(str(current_user["id"]))

    result = await db.execute(select(UserPushToken).where(UserPushToken.token == payload.token))
    push_token = result.scalar_one_or_none()

    if push_token and push_token.user_id == user_id:
        push_token.is_active = False
        push_token.last_seen = datetime.now(UTC)
        await db.commit()
        logger.info("Disabled FCM token for user_id=%s", user_id)
        return {"message": "Token unregistered"}

    logger.info("Attempt to disable non-existing or foreign token for user_id=%s", user_id)
    return {"message": "Token not found"}


