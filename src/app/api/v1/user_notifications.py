# src/app/api/v1/user_notifications.py
from typing import Annotated, Any, cast
from uuid import UUID
from datetime import datetime, UTC

from fastapi import APIRouter, Depends, Request
from fastcrud.paginated import PaginatedListResponse, compute_offset, paginated_response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func

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
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    offset = compute_offset(page, items_per_page)
    
    # Build query
    query = db.query(Notification).filter(Notification.user_id == user.id)
    
    if unread_only:
        query = query.filter(Notification.is_read == False)
    
    if notification_type:
        query = query.filter(Notification.type == notification_type)
    
    query = query.order_by(Notification.created_at.desc())
    
    notifications = query.offset(offset).limit(items_per_page).all()
    total = query.count()
    
    notifications_data = []
    for notification in notifications:
        notification_dict = {
            "id": notification.id,
            "title": notification.title,
            "message": notification.message,
            "type": notification.type,
            "is_read": notification.is_read,
            "created_at": notification.created_at
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
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    unread_count = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read == False
    ).count()
    
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
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user.id
    ).first()
    
    if not notification:
        raise NotFoundException("Notification not found")
    
    notification.is_read = True
    db.commit()
    
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
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    # Update all unread notifications
    updated_count = db.query(Notification).filter(
        Notification.user_id == user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    
    db.commit()
    
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
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user.id
    ).first()
    
    if not notification:
        raise NotFoundException("Notification not found")
    
    db.delete(notification)
    db.commit()
    
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
    
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise NotFoundException("User not found")
    
    # Delete all notifications
    deleted_count = db.query(Notification).filter(Notification.user_id == user.id).count()
    db.query(Notification).filter(Notification.user_id == user.id).delete()
    
    db.commit()
    
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
    
    user = db.query(User).filter(User.username == username).first()
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
    db.commit()
    db.refresh(notification)
    
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
    total_notifications = db.query(Notification).count()
    
    # Get unread notifications
    unread_notifications = db.query(Notification).filter(Notification.is_read == False).count()
    
    # Get notifications by type
    notifications_by_type = {}
    type_query = db.query(Notification.type, func.count(Notification.id).label('count')).group_by(
        Notification.type
    ).all()
    
    for notification_type, count in type_query:
        notifications_by_type[notification_type] = count
    
    # Get recent notifications (last 24 hours)
    from datetime import timedelta
    yesterday = datetime.now(UTC) - timedelta(days=1)
    recent_notifications = db.query(Notification).filter(
        Notification.created_at >= yesterday
    ).count()
    
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
    users = db.query(User).all()
    
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
    
    db.commit()
    
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
    
    # Delete old read notifications
    deleted_count = db.query(Notification).filter(
        Notification.created_at < cutoff_date,
        Notification.is_read == True
    ).count()
    
    db.query(Notification).filter(
        Notification.created_at < cutoff_date,
        Notification.is_read == True
    ).delete()
    
    db.commit()
    
    return {
        "message": f"Cleaned up {deleted_count} old notifications",
        "deleted_count": deleted_count,
        "cutoff_date": cutoff_date
    }
