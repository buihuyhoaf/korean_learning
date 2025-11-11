"""
Notification Schemas

Pydantic schemas for notification models.
"""
from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# Notification Schemas
# ============================================================================

class NotificationBase(BaseModel):
    """Base schema for Notification"""
    user_id: UUID = Field(..., description="User UUID")
    title: str = Field(..., max_length=200, description="Notification title")
    message: str = Field(..., description="Notification message")
    type: str = Field(..., max_length=50, description="Notification type: system, reminder, achievement")
    is_read: bool = Field(default=False, description="Whether the notification has been read")


class NotificationCreate(NotificationBase):
    """Schema for creating a notification"""
    model_config = ConfigDict(extra="forbid")


class NotificationUpdate(BaseModel):
    """Schema for updating a notification"""
    title: Optional[str] = Field(None, max_length=200, description="Notification title")
    message: Optional[str] = Field(None, description="Notification message")
    type: Optional[str] = Field(None, max_length=50, description="Notification type")
    is_read: Optional[bool] = Field(None, description="Whether the notification has been read")
    model_config = ConfigDict(extra="forbid")


class NotificationResponse(NotificationBase):
    """Schema for reading notification data"""
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class AdminPushNotificationRequest(BaseModel):
    """Payload for admin-triggered push notifications."""

    user_ids: list[UUID] = Field(..., min_length=1, description="Target user IDs (UUID)")
    title: str = Field(..., min_length=1, max_length=200, description="Notification title")
    body: str = Field(..., min_length=1, description="Notification body")

    model_config = ConfigDict(extra="forbid")

