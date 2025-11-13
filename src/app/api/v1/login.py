from datetime import timedelta
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import UnauthorizedException
from ...core.schemas import Token, TokenResponse
from ...core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    TokenType,
    authenticate_user,
    create_access_token,
    create_refresh_token_with_storage,
    verify_token,
    verify_refresh_token,
    rotate_refresh_token,
    invalidate_user_refresh_tokens,
)
from ...crud.crud_users import crud_users
from ...api.dependencies import get_current_user

router = APIRouter(tags=["login"])


class LoginRequest(BaseModel):
    """Login request schema for JSON requests"""
    username: str
    password: str


async def get_login_credentials(
    request: Request,
) -> tuple[str, str]:
    """
    Extract username and password from request.
    Supports both JSON (application/json) and form-urlencoded (application/x-www-form-urlencoded).
    """
    content_type = request.headers.get("content-type", "").lower()
    
    # Try JSON first (for mobile apps)
    if "application/json" in content_type:
        try:
            body = await request.json()
            username = body.get("username") or body.get("email")  # Support both username and email keys
            password = body.get("password")
            
            if not username or not password:
                raise UnauthorizedException("Username/email and password are required.")
            
            return username, password
        except UnauthorizedException:
            raise
        except Exception as e:
            raise UnauthorizedException(f"Invalid JSON request: {str(e)}")
    
    # Fallback to form-urlencoded (for web apps)
    # FastAPI will automatically parse form data if Content-Type is form-urlencoded
    try:
        form_data = await request.form()
        username = form_data.get("username")
        password = form_data.get("password")
        
        if not username or not password:
            raise UnauthorizedException("Username and password are required.")
        
        return username, password
    except UnauthorizedException:
        raise
    except Exception as e:
        raise UnauthorizedException(f"Invalid form request: {str(e)}")


@router.post("/login", response_model=Token)
async def login_for_access_token(
    response: Response,
    request: Request,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict[str, str]:
    """
    Login endpoint that supports both JSON and form-urlencoded requests.
    
    JSON format:
    {
        "username": "user123" or "user@example.com",
        "password": "password123"
    }
    
    Form-urlencoded format:
    username=user123&password=password123
    """
    # Get credentials from request (supports both JSON and form)
    username_or_email, password = await get_login_credentials(request)
    
    # Authenticate user
    user = await authenticate_user(username_or_email=username_or_email, password=password, db=db)
    if not user:
        raise UnauthorizedException("Wrong username, email or password.")

    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = await create_access_token(data={"sub": user["username"]}, expires_delta=access_token_expires)

    # Get user ID for refresh token storage
    if "@" in username_or_email:
        db_user = await crud_users.get(db=db, email=username_or_email, is_deleted=False)
    else:
        db_user = await crud_users.get(db=db, username=username_or_email, is_deleted=False)
    
    if not db_user:
        raise UnauthorizedException("User not found.")

    # Create refresh token and store in database
    refresh_token = await create_refresh_token_with_storage(
        data={"sub": user["username"]}, 
        user_id=db_user["id"], 
        db=db
    )

    return {
        "access_token": access_token, 
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(request: Request, db: AsyncSession = Depends(async_get_db)) -> dict[str, str]:
    """Refresh access token with token rotation"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("[REFRESH_ENDPOINT_DEBUG] Refresh token endpoint called")
    
    # Try to get refresh token from request body or cookies
    refresh_token = None
    
    # First try to get from request body (for mobile apps)
    try:
        body = await request.json()
        logger.info(f"[REFRESH_ENDPOINT_DEBUG] Request body keys: {list(body.keys()) if body else 'None'}")
        refresh_token = body.get("refresh_token")
        if refresh_token:
            logger.info(f"[REFRESH_ENDPOINT_DEBUG] Got refresh token from body, length: {len(refresh_token)}, starts with: {refresh_token[:20]}...")
            # Clean any potential whitespace
            refresh_token = refresh_token.strip()
            logger.info(f"[REFRESH_ENDPOINT_DEBUG] After strip - length: {len(refresh_token)}, starts with: {refresh_token[:20]}...")
        else:
            logger.info(f"[REFRESH_ENDPOINT_DEBUG] Got refresh token from body, but value is None/empty")
    except Exception as e:
        logger.warning(f"[REFRESH_ENDPOINT_DEBUG] Failed to parse request body: {e}")
        pass
    
    # Fallback to cookies (for web apps)
    if not refresh_token:
        refresh_token = request.cookies.get("refresh_token")
        logger.info(f"[REFRESH_ENDPOINT_DEBUG] Got refresh token from cookies, length: {len(refresh_token) if refresh_token else 0}")
    
    if not refresh_token:
        logger.error("[REFRESH_ENDPOINT_DEBUG] No refresh token found in request")
        raise UnauthorizedException("Refresh token missing.")

    logger.info(f"[REFRESH_ENDPOINT_DEBUG] Attempting to verify refresh token, length: {len(refresh_token)}")
    
    # Verify refresh token and get user info
    try:
        username_or_email = await verify_refresh_token(refresh_token, db)
        logger.info(f"[REFRESH_ENDPOINT_DEBUG] Token verification successful for: {username_or_email}")
    except Exception as e:
        logger.error(f"[REFRESH_ENDPOINT_DEBUG] Token verification failed: {str(e)}")
        raise
    
    # Get user for user_id
    if "@" in username_or_email:
        db_user = await crud_users.get(db=db, email=username_or_email, is_deleted=False)
    else:
        db_user = await crud_users.get(db=db, username=username_or_email, is_deleted=False)
    
    if not db_user:
        raise UnauthorizedException("User not found.")

    # Rotate tokens (invalidate old refresh token and create new ones)
    new_access_token, new_refresh_token = await rotate_refresh_token(
        old_refresh_token=refresh_token,
        user_id=db_user["id"],
        username_or_email=username_or_email,
        db=db
    )

    return {
        "access_token": new_access_token, 
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.get("/me")
async def get_current_user_info(
    request: Request,
    current_user: Annotated[dict, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> dict:
    """Return current user information (requires valid access token)"""
    return current_user
