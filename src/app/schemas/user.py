from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from ..core.schemas import PersistentDeletion, TimestampSchema, UUIDSchema


class UserBase(BaseModel):
    username: Annotated[str, Field(min_length=2, max_length=20, pattern=r"^[a-z0-9]+$", examples=["userson"])]
    email: Annotated[EmailStr, Field(examples=["user.userson@example.com"])]


# Removed UserSchema class to avoid conflicts with User model


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    username: Annotated[str, Field(min_length=2, max_length=50, pattern=r"^[a-z0-9]+$", examples=["userson"])]
    email: Annotated[EmailStr, Field(examples=["user.userson@example.com"])]
    picture: Annotated[str | None, Field(examples=["https://example.com/picture.jpg"])]
    role: Annotated[str, Field(examples=["student"])]
    exp: Annotated[int, Field(examples=[0])]
    streak_days: Annotated[int, Field(examples=[0])]
    created_at: datetime
    tier_id: Annotated[UUID | None, Field(examples=[None])]
    has_completed_entry_test: Annotated[bool, Field(examples=[False])]
    current_course_id: Annotated[UUID | None, Field(examples=[None])]
    entry_test_score: Annotated[int | None, Field(examples=[None])]


class UserSummary(BaseModel):
    """Lightweight schema for user listings in admin trackers."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: Annotated[str, Field(min_length=2, max_length=50, pattern=r"^[a-z0-9]+$", examples=["userson"])]
    email: Annotated[EmailStr, Field(examples=["user.userson@example.com"])]
    role: Annotated[str, Field(examples=["student"])]
    exp: Annotated[int, Field(examples=[0])]

class UserCreate(BaseModel):
    """Schema for creating users that matches the actual User model."""
    model_config = ConfigDict(extra="forbid")
    
    username: Annotated[str, Field(min_length=2, max_length=50, pattern=r"^[a-z0-9]+$", examples=["userson"])]
    email: Annotated[EmailStr, Field(examples=["user.userson@example.com"])]
    password: Annotated[str, Field(min_length=8, examples=["Str1ngst!"])]
    
    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password meets security requirements."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        
        has_digit = any(c.isdigit() for c in v)
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_special = any(not c.isalnum() for c in v)
        
        if not has_digit:
            raise ValueError("Password must contain at least one digit")
        if not has_upper:
            raise ValueError("Password must contain at least one uppercase letter")
        if not has_lower:
            raise ValueError("Password must contain at least one lowercase letter")
        if not has_special:
            raise ValueError("Password must contain at least one special character")
        
        return v


class UserCreateInternal(BaseModel):
    """Schema for creating users that matches the actual User model."""
    model_config = ConfigDict(extra="forbid")
    
    username: Annotated[str, Field(min_length=2, max_length=50, pattern=r"^[a-z0-9]+$", examples=["userson"])]
    email: Annotated[EmailStr, Field(examples=["user.userson@example.com"])]
    password: Annotated[str, Field(examples=["hashed_password_string"])]
    picture: Annotated[str | None, Field(default=None, examples=["https://example.com/picture.jpg"])]
    role: Annotated[str, Field(default="student", examples=["student"])]
    exp: Annotated[int, Field(default=0, examples=[0])]
    streak_days: Annotated[int, Field(default=0, examples=[0])]
    tier_id: Annotated[UUID | None, Field(default=None, examples=[None])]


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: Annotated[
        str | None, Field(min_length=2, max_length=50, pattern=r"^[a-z0-9]+$", examples=["userberg"], default=None)
    ]
    email: Annotated[EmailStr | None, Field(examples=["user.userberg@example.com"], default=None)]
    picture: Annotated[
        str | None,
        Field(
            pattern=r"^(https?|ftp)://[^\s/$.?#].[^\s]*$", examples=["https://www.example.com/picture.jpg"], default=None
        ),
    ]
    role: Annotated[str | None, Field(examples=["student"], default=None)]
    exp: Annotated[int | None, Field(examples=[0], default=None)]
    streak_days: Annotated[int | None, Field(examples=[0], default=None)]
    tier_id: Annotated[UUID | None, Field(examples=[None], default=None)]


class UserUpdateInternal(UserUpdate):
    updated_at: datetime


class UserTierUpdate(BaseModel):
    tier_id: UUID


class UserDelete(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_deleted: bool
    deleted_at: datetime


class UserRestoreDeleted(BaseModel):
    is_deleted: bool


class UserRegistration(BaseModel):
    """Schema for user registration endpoint."""
    model_config = ConfigDict(extra="forbid")
    
    username: Annotated[str, Field(min_length=2, max_length=20, pattern=r"^[a-z0-9]+$", examples=["newuser"])]
    email: Annotated[EmailStr, Field(examples=["newuser@example.com"])]
    password: Annotated[str, Field(min_length=8, examples=["SecurePass123!"])]


class UserRegistrationResponse(BaseModel):
    """Response schema for successful user registration."""
    message: str
    user: dict  # Use dict to avoid schema mismatch with actual User model
