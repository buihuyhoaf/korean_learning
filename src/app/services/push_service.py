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
) -> PushSendResult:
    """
    Send an FCM notification to all active tokens associated with the provided user IDs.

    Raises
    ------
    FirebaseNotInitializedError
        If Firebase Admin SDK is not initialised (missing credentials).
    """

    firebase_app = get_firebase_app() or init_firebase()
    if firebase_app is None:
        logger.warning("Attempt to send push notification without Firebase initialised.")
        raise FirebaseNotInitializedError("Firebase not initialized")

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
            
            # Log detailed error for permission denied
            if code == "PERMISSION_DENIED" or "PERMISSION_DENIED" in error_message:
                logger.error(
                    "PERMISSION_DENIED for token %s. This usually means: "
                    "1. Service account lacks 'Firebase Admin' role or 'cloudmessaging.messages.create' permission. "
                    "2. FCM API is not enabled in Google Cloud Console. "
                    "3. Token was registered with a different Firebase project (most likely cause). "
                    "Token length: %s, Platform: %s",
                    token_model.token[:12],
                    len(token_model.token),
                    token_model.platform
                )
                # Mark token as inactive if PERMISSION_DENIED - likely from wrong project
                token_model.is_active = False
                logger.warning("Marked token=%s as inactive due to PERMISSION_DENIED (likely wrong Firebase project)", token_model.token[:12])

            if code in {"registration-token-not-registered", "invalid-registration-token"}:
                token_model.is_active = False
                logger.info("Marked token=%s as inactive due to %s", token_model.token[:12], code)

    await db.commit()

    return PushSendResult(
        requested_tokens=len(tokens),
        success=success_count,
        failed=failure_count,
    )


