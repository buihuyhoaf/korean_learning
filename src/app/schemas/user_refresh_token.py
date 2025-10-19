from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class UserRefreshTokenCreate(BaseModel):
    """Pydantic model for creating UserRefreshToken"""
    model_config = ConfigDict(from_attributes=True)
    
    user_id: int
    token: str
    expires_at: datetime


class UserRefreshTokenUpdate(BaseModel):
    """Pydantic model for updating UserRefreshToken"""
    model_config = ConfigDict(from_attributes=True)
    
    user_id: Optional[int] = None
    token: Optional[str] = None
    expires_at: Optional[datetime] = None


class UserRefreshTokenUpdateInternal(UserRefreshTokenUpdate):
    """Internal update model for UserRefreshToken"""
    pass


class UserRefreshTokenDelete(BaseModel):
    """Pydantic model for deleting UserRefreshToken"""
    model_config = ConfigDict(from_attributes=True)
    
    pass


class UserRefreshTokenRead(BaseModel):
    """Pydantic model for reading UserRefreshToken"""
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    user_id: int
    token: str
    expires_at: datetime
    created_at: datetime
