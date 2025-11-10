"""
Pydantic schemas for user push token registration.
"""

from pydantic import BaseModel, Field, ConfigDict


class PushTokenRegisterRequest(BaseModel):
    """
    Request body for registering/updating an FCM token.
    """

    token: str = Field(..., min_length=1, description="FCM device token")
    platform: str = Field(..., min_length=1, max_length=32, description="Client platform (e.g., android, ios)")

    model_config = ConfigDict(extra="forbid")


class PushTokenUnregisterRequest(BaseModel):
    """
    Request body for unregistering (disabling) an FCM token.
    """

    token: str = Field(..., min_length=1, description="FCM device token to disable")

    model_config = ConfigDict(extra="forbid")


