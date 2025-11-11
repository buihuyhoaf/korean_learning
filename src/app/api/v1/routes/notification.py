"""
Admin endpoints for sending push notifications via Firebase Cloud Messaging.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...dependencies import get_current_user
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import ForbiddenException
from ...schemas.notification_schemas import AdminPushNotificationRequest
from ...services.push_service import FirebaseNotInitializedError, PushSendResult, send_push_notification

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _ensure_admin(current_user: dict) -> None:
    """Ensure the current user has admin privileges."""
    if current_user.get("is_superuser") or current_user.get("role") == "admin":
        return
    raise ForbiddenException("You do not have permission to perform this action.")


@router.post("/send", status_code=status.HTTP_200_OK)
async def send_push_notifications(
    payload: AdminPushNotificationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(async_get_db),
) -> dict[str, object]:
    """
    Trigger push notifications to selected users.
    """

    _ensure_admin(current_user)

    logger.info(
        "Admin user=%s requested push notification to %s users",
        current_user.get("id"),
        len(payload.user_ids),
    )

    try:
        user_ids = [uuid.UUID(str(user_id)) for user_id in payload.user_ids]
    except (ValueError, TypeError) as exc:
        logger.warning("Invalid UUID in user_ids payload: %s", exc)
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid user ID format") from exc

    try:
        result: PushSendResult = await send_push_notification(
            db=db,
            user_ids=user_ids,
            title=payload.title,
            body=payload.body,
        )
    except FirebaseNotInitializedError as exc:
        logger.warning("Firebase not initialised when sending admin push notifications.")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    response_payload = {
        "message": "Notifications dispatched",
        "stats": result.as_dict(),
    }
    logger.info("Push notification dispatch complete: %s", response_payload["stats"])

    return response_payload


