"""
Google Authentication schemas.
"""
from pydantic import BaseModel


class GoogleSignInRequest(BaseModel):
    """Request schema for Google Sign-In."""
    token: str


class GoogleSignInResponse(BaseModel):
    """Response schema for Google Sign-In."""
    token: str
    token_type: str = "bearer"


class GoogleAuthError(BaseModel):
    """Error schema for Google Authentication."""
    detail: str


