"""
Service helpers for sending Firebase Cloud Messaging (FCM) push notifications.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Final, Sequence
import uuid

from firebase_admin import messaging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.firebase import get_firebase_app, init_firebase
from ..models.user_push_token import UserPushToken
from ..models.notification import Notification

logger = logging.getLogger(__name__)

# Firebase allows at most 500 tokens per multicast request.
MAX_TOKENS_PER_BATCH: Final[int] = 500


class FirebaseNotInitializedError(RuntimeError):
    """Raised when Firebase Admin SDK is not available."""


@dataclass(slots=True)
class PushSendResult:
    """Summarise push notification send statistics."""

    requested_tokens: int
    success: int
    failed: int

    def as_dict(self) -> dict[str, int]:
        return {
            "requested_tokens": self.requested_tokens,
            "success": self.success,
            "failed": self.failed,
        }


async def _fetch_active_tokens(db: AsyncSession, user_ids: Iterable[uuid.UUID]) -> list[UserPushToken]:
    """Retrieve active push tokens for the provided user IDs."""
    if not user_ids:
        return []

    stmt = (
        select(UserPushToken)
        .where(UserPushToken.user_id.in_(tuple(user_ids)))
        .where(UserPushToken.is_active.is_(True))
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def _send_multicast(tokens: Sequence[str], title: str, body: str) -> messaging.BatchResponse:
    """
    Execute firebase_admin.messaging.send_each in a background thread.

    Firebase's Python SDK is synchronous; dispatch from the main event loop
    to avoid blocking using asyncio.to_thread.
    
    Note: send_multicast was removed in Firebase Admin SDK 7.0.0.
    Using send_each() instead, which sends a list of messages.
    """
    notification = messaging.Notification(title=title, body=body)
    messages = [
        messaging.Message(notification=notification, token=token)
        for token in tokens
    ]

    return await asyncio.to_thread(messaging.send_each, messages)


async def send_push_notification(
    *,
    db: AsyncSession,
    user_ids: Sequence[uuid.UUID],
    title: str,
    body: str,
    notification_type: str = "system",
) -> PushSendResult:
    """
    Send an FCM notification to all active tokens associated with the provided user IDs.
    Also saves the notification to the database for each user.

    Parameters
    ----------
    db : AsyncSession
        Database session
    user_ids : Sequence[uuid.UUID]
        List of user IDs to send notifications to
    title : str
        Notification title
    body : str
        Notification body/message
    notification_type : str, optional
        Type of notification (default: "system"). Can be "system", "reminder", "achievement", etc.

    Raises
    ------
    FirebaseNotInitializedError
        If Firebase Admin SDK is not initialised (missing credentials).
    """

    firebase_app = get_firebase_app() or init_firebase()
    if firebase_app is None:
        logger.warning("Attempt to send push notification without Firebase initialised.")
        raise FirebaseNotInitializedError("Firebase not initialized")
    
    # Log Firebase project info for debugging
    try:
        project_id = firebase_app.project_id if hasattr(firebase_app, 'project_id') else None
        logger.info("Using Firebase project ID: %s for sending push notifications", project_id)
    except Exception:
        pass

    # Save notifications to database for each user
    logger.info("Saving notifications to database for %s users", len(user_ids))
    for user_id in user_ids:
        notification = Notification(
            user_id=user_id,
            title=title,
            message=body,
            type=notification_type,
            is_read=False
        )
        db.add(notification)
    
    # Commit notifications to database before sending FCM
    await db.commit()
    logger.info("✅ Saved %s notifications to database", len(user_ids))

    tokens = await _fetch_active_tokens(db, user_ids)
    if not tokens:
        logger.info("No active FCM tokens for users=%s", [str(uid) for uid in user_ids])
        return PushSendResult(requested_tokens=0, success=0, failed=0)
    
    # Log token info for debugging
    logger.info(
        "Preparing to send push notifications to %s tokens (users=%s). "
        "Token platforms: %s",
        len(tokens),
        [str(uid) for uid in user_ids],
        [t.platform for t in tokens]
    )

    success_count = 0
    failure_count = 0

    # Process tokens in batches to respect Firebase limits.
    for index in range(0, len(tokens), MAX_TOKENS_PER_BATCH):
        chunk = tokens[index : index + MAX_TOKENS_PER_BATCH]
        token_values = [token.token for token in chunk]
        logger.debug("Sending push batch %s-%s (size=%s)", index, index + len(chunk), len(chunk))

        try:
            response = await _send_multicast(token_values, title, body)
        except Exception as exc:  # noqa: BLE001
            error_code = getattr(exc, 'code', None)
            error_message = str(exc)
            logger.error(
                "Failed to send FCM batch: %s (code=%s, message=%s)",
                exc,
                error_code,
                error_message
            )
            # Log more details for permission errors
            if 'PERMISSION_DENIED' in error_message or error_code == 'PERMISSION_DENIED':
                logger.error(
                    "PERMISSION_DENIED error detected. Please check: "
                    "1. Service account has 'Firebase Admin' role or 'cloudmessaging.messages.create' permission. "
                    "2. FCM API is enabled in Google Cloud Console. "
                    "3. Service account project ID matches Firebase project ID."
                )
            failure_count += len(chunk)
            continue

        # Evaluate per-token responses.
        for token_model, send_response in zip(chunk, response.responses, strict=False):
            if send_response.success:
                success_count += 1
                logger.info("Push notification sent successfully to token=%s", token_model.token[:12])
                continue

            failure_count += 1
            exception = send_response.exception
            code = getattr(exception, "code", "unknown")
            error_message = str(exception) if exception else "Unknown error"
            logger.warning(
                "Failed to send push notification to token=%s (code=%s, error=%s)",
                token_model.token[:12],
                code,
                error_message,
            )
            
            # Log detailed error for NOT_FOUND (404)
            if code == "NOT_FOUND" or "NOT_FOUND" in error_message or "404" in error_message:
                # Get current project ID for comparison
                current_project = None
                try:
                    firebase_app = get_firebase_app()
                    if firebase_app:
                        current_project = firebase_app.project_id if hasattr(firebase_app, 'project_id') else None
                except:
                    pass
                
                logger.error(
                    "❌ NOT_FOUND (404) error for token %s (platform=%s, user_id=%s)\n"
                    "   Current Firebase project: %s\n"
                    "   Expected project: korean-learning-474814\n\n"
                    "   Possible causes:\n"
                    "   1. ⚠️  FCM API not enabled in Google Cloud Console\n"
                    "      → Enable: https://console.cloud.google.com/apis/library/fcm.googleapis.com?project=korean-learning-474814\n\n"
                    "   2. ⚠️  Service account lacks permissions\n"
                    "      → Check IAM: https://console.cloud.google.com/iam-admin/iam?project=korean-learning-474814\n"
                    "      → Required role: 'Firebase Admin SDK Administrator Service Agent'\n\n"
                    "   3. ⚠️  Token registered from different Firebase project\n"
                    "      → Token was registered when Android app used different project\n"
                    "      → Solution: Users need to re-login to register new token\n\n"
                    "   💡 Quick checks:\n"
                    "   - Run: python scripts/test_fcm_send.py\n"
                    "   - Check logs for 'Firebase initialized successfully'\n"
                    "   - Verify FCM API is enabled in Google Cloud Console",
                    token_model.token[:12],
                    token_model.platform,
                    token_model.user_id,
                    current_project or "unknown"
                )
                # Mark token as inactive - likely from wrong project or API not enabled
                token_model.is_active = False
                logger.warning(
                    "Marked token=%s as inactive due to NOT_FOUND. "
                    "Possible causes: FCM API not enabled, missing permissions, or token from wrong project",
                    token_model.token[:12]
                )
            
            # Log detailed error for permission denied
            if code == "PERMISSION_DENIED" or "PERMISSION_DENIED" in error_message:
                # Check if it's a SenderId mismatch (most common cause)
                is_sender_id_mismatch = "SenderId" in error_message or "sender" in error_message.lower()
                
                logger.error(
                    "PERMISSION_DENIED for token %s. Error: %s. "
                    "Token length: %s, Platform: %s, User ID: %s. "
                    "%s",
                    token_model.token[:12],
                    error_message,
                    len(token_model.token),
                    token_model.platform,
                    token_model.user_id,
                    "⚠️ SENDERID MISMATCH: Token was registered with a different Firebase project than the service account. "
                    "User needs to re-login to register a new token from the correct project." 
                    if is_sender_id_mismatch 
                    else "Possible causes: 1) Service account lacks permissions, 2) FCM API not enabled, 3) Token from wrong project."
                )
                # Mark token as inactive if PERMISSION_DENIED - likely from wrong project
                token_model.is_active = False
                logger.warning(
                    "Marked token=%s as inactive due to PERMISSION_DENIED%s",
                    token_model.token[:12],
                    " (SenderId mismatch - wrong Firebase project)" if is_sender_id_mismatch else ""
                )

            if code in {"registration-token-not-registered", "invalid-registration-token"}:
                token_model.is_active = False
                logger.info("Marked token=%s as inactive due to %s", token_model.token[:12], code)

    await db.commit()

    return PushSendResult(
        requested_tokens=len(tokens),
        success=success_count,
        failed=failure_count,
    )


