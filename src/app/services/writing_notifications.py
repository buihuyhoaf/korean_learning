"""
Service for sending writing evaluation notifications via FCM and persisting them.
"""

from __future__ import annotations

import asyncio
import logging
import uuid

from firebase_admin import messaging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.firebase import get_firebase_app, init_firebase
from ..models.notification import Notification
from ..models.user_push_token import UserPushToken

logger = logging.getLogger(__name__)


async def notify_writing_graded(
    *,
    db: AsyncSession,
    user_id: uuid.UUID,
    submission_id: uuid.UUID,
    lesson_id: uuid.UUID,
    title: str = "Bài viết đã được chấm",
    body: str = "Giáo viên đã chấm bài viết của bạn",
) -> None:
    """
    Send FCM notification and persist notification record for a graded writing submission.
    
    This function:
    1. Sends an FCM push notification to the user's devices
    2. Saves a notification record in the database with type='writing_graded'
    3. Handles errors gracefully (logs but doesn't raise)
    
    Parameters
    ----------
    db:
        Database session.
    user_id:
        ID of the user who submitted the writing.
    submission_id:
        ID of the writing submission that was graded.
    lesson_id:
        ID of the lesson containing the writing exercise.
    title:
        Notification title (defaults to Vietnamese message).
    body:
        Notification body text (defaults to Vietnamese message).
    """
    try:
        # Send FCM push notification with data payload
        try:
            firebase_app = get_firebase_app() or init_firebase()
            if firebase_app is None:
                logger.warning("Firebase not initialized, skipping FCM notification")
            else:
                # Fetch active push tokens for the user
                stmt = (
                    select(UserPushToken)
                    .where(UserPushToken.user_id == user_id)
                    .where(UserPushToken.is_active.is_(True))
                )
                result = await db.execute(stmt)
                tokens = list(result.scalars().all())
                
                if tokens:
                    # Create FCM message with data payload
                    message = messaging.MulticastMessage(
                        notification=messaging.Notification(title=title, body=body),
                        data={
                            "type": "writing_graded",
                            "lesson_id": str(lesson_id),
                            "submission_id": str(submission_id),
                        },
                        tokens=[token.token for token in tokens],
                    )
                    
                    # Send in background thread
                    response = await asyncio.to_thread(messaging.send_multicast, message)
                    
                    success_count = sum(1 for r in response.responses if r.success)
                    failed_count = len(response.responses) - success_count
                    
                    logger.info(
                        "Writing graded notification sent: user_id=%s submission_id=%s success=%s failed=%s",
                        user_id,
                        submission_id,
                        success_count,
                        failed_count,
                    )
                    
                    # Mark inactive tokens
                    for token_model, send_response in zip(tokens, response.responses, strict=False):
                        if not send_response.success:
                            code = getattr(send_response.exception, "code", "unknown")
                            if code in {"registration-token-not-registered", "invalid-registration-token"}:
                                token_model.is_active = False
                                logger.info("Marked token=%s as inactive", token_model.token[:12])
                    
                    await db.flush()
                else:
                    logger.info("No active FCM tokens for user_id=%s", user_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Failed to send FCM notification for writing_graded (user_id=%s submission_id=%s): %s",
                user_id,
                submission_id,
                exc,
                exc_info=True,
            )
            # Continue to save notification even if FCM fails
        
        # Save notification to database
        notification = Notification(
            user_id=user_id,
            title=title,
            message=body,
            type="writing_graded",
            is_read=False,
        )
        db.add(notification)
        await db.flush()
        
        logger.info(
            "Writing graded notification saved to database: user_id=%s submission_id=%s notification_id=%s",
            user_id,
            submission_id,
            notification.id,
        )
        
    except Exception as exc:  # noqa: BLE001
        logger.error(
            "Error in notify_writing_graded (user_id=%s submission_id=%s): %s",
            user_id,
            submission_id,
            exc,
            exc_info=True,
        )
        # Don't raise - notification failure shouldn't break grading flow

