# src/app/api/v1/user_notifications.py
from typing import Annotated, Any, cast
from uuid import UUID
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, Request
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from ...api.dependencies import get_current_user, get_current_superuser
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import NotFoundException, ForbiddenException
from ...models.user import User
from ...models.notification import Notification

router = APIRouter(tags=["notifications"])


# UC13: Receive Notifications
@router.get("/user/{username}/notifications", response_model=PaginatedListResponse[dict])
async def get_user_notifications(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    page: int = 1,
    items_per_page: int = 20,
    unread_only: bool = False,
    notification_type: str = None,
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get user's notifications"""
    
    # Check permissions
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own notifications")
    
    # Get user
    user_result = await db.execute(select(User).filter(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    offset = compute_offset(page, items_per_page)
    
    # Build query
    query = select(Notification).filter(Notification.user_id == user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    if notification_type:
        query = query.filter(Notification.type == notification_type)
    
    query = query.order_by(Notification.created_at.desc())
    
    # Get total count
    count_query = select(func.count()).select_from(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        count_query = count_query.filter(Notification.is_read == False)
    if notification_type:
        count_query = count_query.filter(Notification.type == notification_type)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()
    
    # Get paginated notifications
    notifications_result = await db.execute(query.offset(offset).limit(items_per_page))
    notifications = notifications_result.scalars().all()
    
    notifications_data = []
    for notification in notifications:
        notification_dict = {
            "id": str(notification.id),
            "title": notification.title,
            "message": notification.message,
            "type": notification.type,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
            "metadata": notification.notification_metadata  # Include metadata in response
        }
        notifications_data.append(notification_dict)
    
    response = paginated_response(
        crud_data={"data": notifications_data, "total": total},
        page=page,
        items_per_page=items_per_page
    )
    return response


@router.get("/user/{username}/notifications/unread-count", response_model=dict)
async def get_unread_notifications_count(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)] = None
) -> dict:
    """Get count of unread notifications"""
    
    # Check permissions
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only view your own notification count")
    
    # Get user
    user_result = await db.execute(select(User).filter(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    # Get unread count
    count_query = select(func.count()).select_from(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read == False
    )
    unread_count_result = await db.execute(count_query)
    unread_count = unread_count_result.scalar_one()
    
    return {
        "unread_count": unread_count,
        "username": username
    }


@router.put("/user/{username}/notifications/{notification_id}/read", response_model=dict)
async def mark_notification_read(
    request: Request,
    username: str,
    notification_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Mark a notification as read"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only mark your own notifications as read")
    
    # Get user
    user_result = await db.execute(select(User).filter(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    # Get notification
    notification_result = await db.execute(
        select(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user.id
        )
    )
    notification = notification_result.scalar_one_or_none()
    
    if not notification:
        raise NotFoundException("Notification not found")
    
    notification.is_read = True
    await db.commit()
    
    return {"message": "Notification marked as read"}


@router.put("/user/{username}/notifications/mark-all-read", response_model=dict)
async def mark_all_notifications_read(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Mark all notifications as read"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only mark your own notifications as read")
    
    # Get user
    user_result = await db.execute(select(User).filter(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    # Update all unread notifications
    from sqlalchemy import update
    update_stmt = (
        update(Notification)
        .where(
            Notification.user_id == user.id,
            Notification.is_read == False
        )
        .values(is_read=True)
    )
    result = await db.execute(update_stmt)
    updated_count = result.rowcount
    await db.commit()
    
    return {
        "message": f"Marked {updated_count} notifications as read",
        "updated_count": updated_count
    }


@router.delete("/user/{username}/notifications/{notification_id}", response_model=dict)
async def delete_notification(
    request: Request,
    username: str,
    notification_id: UUID,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Delete a notification"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only delete your own notifications")
    
    # Get user
    user_result = await db.execute(select(User).filter(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    # Get notification
    notification_result = await db.execute(
        select(Notification).filter(
            Notification.id == notification_id,
            Notification.user_id == user.id
        )
    )
    notification = notification_result.scalar_one_or_none()
    
    if not notification:
        raise NotFoundException("Notification not found")
    
    from sqlalchemy import delete
    delete_stmt = delete(Notification).where(Notification.id == notification_id)
    await db.execute(delete_stmt)
    await db.commit()
    
    return {"message": "Notification deleted successfully"}


@router.delete("/user/{username}/notifications/clear-all", response_model=dict)
async def clear_all_notifications(
    request: Request,
    username: str,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Clear all notifications"""
    
    # Check permissions
    if current_user["username"] != username:
        raise ForbiddenException("You can only clear your own notifications")
    
    # Get user
    user_result = await db.execute(select(User).filter(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    # Get count before deletion
    count_query = select(func.count()).select_from(Notification).filter(Notification.user_id == user.id)
    count_result = await db.execute(count_query)
    deleted_count = count_result.scalar_one()
    
    # Delete all notifications
    from sqlalchemy import delete
    delete_stmt = delete(Notification).where(Notification.user_id == user.id)
    await db.execute(delete_stmt)
    await db.commit()
    
    return {
        "message": f"Cleared {deleted_count} notifications",
        "deleted_count": deleted_count
    }


@router.post("/user/{username}/notifications", response_model=dict)
async def create_notification(
    request: Request,
    username: str,
    notification_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    current_user: Annotated[dict, Depends(get_current_user)]
) -> dict:
    """Create a notification for a user"""
    
    # Check permissions (users can create notifications for themselves, admins can create for anyone)
    if current_user["username"] != username and current_user["role"] != "admin":
        raise ForbiddenException("You can only create notifications for yourself")
    
    # Get user
    user_result = await db.execute(select(User).filter(User.username == username))
    user = user_result.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")
    
    notification = Notification(
        user_id=user.id,
        title=notification_data["title"],
        message=notification_data["message"],
        type=notification_data.get("type", "system"),
        is_read=False
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    
    return {
        "message": "Notification created successfully",
        "notification": {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "type": notification.type,
            "is_read": notification.is_read,
            "created_at": notification.created_at
        }
    }


# System notification functions
def create_achievement_notification(db: AsyncSession, user_id: UUID, achievement_type: str, details: str) -> None:
    """Create an achievement notification"""
    notification = Notification(
        user_id=user_id,
        title=f"🎉 Achievement Unlocked!",
        message=f"You've earned a new achievement: {achievement_type}. {details}",
        type="achievement",
        is_read=False
    )
    db.add(notification)


def create_friend_request_notification(db: AsyncSession, user_id: UUID, requester_username: str) -> None:
    """Create a friend request notification"""
    notification = Notification(
        user_id=user_id,
        title="👥 New Friend Request",
        message=f"{requester_username} sent you a friend request!",
        type="social",
        is_read=False
    )
    db.add(notification)


def create_challenge_notification(db: AsyncSession, user_id: UUID, challenge_title: str, message: str) -> None:
    """Create a challenge notification"""
    notification = Notification(
        user_id=user_id,
        title=f"🏆 Challenge Update: {challenge_title}",
        message=message,
        type="challenge",
        is_read=False
    )
    db.add(notification)


def create_reminder_notification(db: AsyncSession, user_id: UUID, message: str) -> None:
    """Create a reminder notification"""
    notification = Notification(
        user_id=user_id,
        title="⏰ Learning Reminder",
        message=message,
        type="reminder",
        is_read=False
    )
    db.add(notification)


def create_system_notification(db: AsyncSession, user_id: UUID, title: str, message: str) -> None:
    """Create a system notification"""
    notification = Notification(
        user_id=user_id,
        title=title,
        message=message,
        type="system",
        is_read=False
    )
    db.add(notification)


# Admin endpoints for managing notifications
@router.get("/admin/notifications/stats", dependencies=[Depends(get_current_superuser)], response_model=dict)
async def get_notifications_stats(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Get notification statistics (Admin only)"""
    
    # Get total notifications
    total_query = select(func.count()).select_from(Notification)
    total_result = await db.execute(total_query)
    total_notifications = total_result.scalar_one()
    
    # Get unread notifications
    unread_query = select(func.count()).select_from(Notification).filter(Notification.is_read == False)
    unread_result = await db.execute(unread_query)
    unread_notifications = unread_result.scalar_one()
    
    # Get notifications by type
    notifications_by_type = {}
    type_query = (
        select(Notification.type, func.count(Notification.id).label('count'))
        .group_by(Notification.type)
    )
    type_result = await db.execute(type_query)
    type_rows = type_result.all()
    
    for notification_type, count in type_rows:
        notifications_by_type[notification_type] = count
    
    # Get recent notifications (last 24 hours)
    from datetime import timedelta
    yesterday = datetime.now(UTC) - timedelta(days=1)
    recent_query = select(func.count()).select_from(Notification).filter(
        Notification.created_at >= yesterday
    )
    recent_result = await db.execute(recent_query)
    recent_notifications = recent_result.scalar_one()
    
    return {
        "total_notifications": total_notifications,
        "unread_notifications": unread_notifications,
        "read_notifications": total_notifications - unread_notifications,
        "notifications_by_type": notifications_by_type,
        "recent_notifications_24h": recent_notifications
    }


@router.post("/admin/notifications/broadcast", dependencies=[Depends(get_current_superuser)], response_model=dict)
async def broadcast_notification(
    request: Request,
    notification_data: dict,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> dict:
    """Broadcast notification to all users (Admin only)"""
    
    # Get all users
    users_query = select(User)
    users_result = await db.execute(users_query)
    users = users_result.scalars().all()
    
    notifications_created = 0
    for user in users:
        notification = Notification(
            user_id=user.id,
            title=notification_data["title"],
            message=notification_data["message"],
            type=notification_data.get("type", "system"),
            is_read=False
        )
        db.add(notification)
        notifications_created += 1
    
    await db.commit()
    
    return {
        "message": f"Broadcast notification sent to {notifications_created} users",
        "notifications_created": notifications_created
    }


@router.delete("/admin/notifications/cleanup", dependencies=[Depends(get_current_superuser)], response_model=dict)
async def cleanup_old_notifications(
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
    days_old: int = 30
) -> dict:
    """Clean up old notifications (Admin only)"""
    
    from datetime import timedelta
    cutoff_date = datetime.now(UTC) - timedelta(days=days_old)
    
    # Get count before deletion
    count_query = select(func.count()).select_from(Notification).filter(
        Notification.created_at < cutoff_date,
        Notification.is_read == True
    )
    count_result = await db.execute(count_query)
    deleted_count = count_result.scalar_one()
    
    # Delete old read notifications
    from sqlalchemy import delete
    delete_stmt = delete(Notification).where(
        Notification.created_at < cutoff_date,
        Notification.is_read == True
    )
    await db.execute(delete_stmt)
    await db.commit()
    
    return {
        "message": f"Cleaned up {deleted_count} old notifications",
        "deleted_count": deleted_count,
        "cutoff_date": cutoff_date
    }
