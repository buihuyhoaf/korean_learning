"""
Google Authentication endpoints.
"""
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.db.database import async_get_db
from ...core.google_auth import (
    verify_google_token,
    extract_username_from_email,
    generate_password_for_google_user,
)
from ...core.security import create_access_token, get_password_hash
from ...crud.crud_users import crud_users
from ...schemas.google_auth import (
    GoogleSignInRequest,
    GoogleSignInResponse,
    GoogleAuthError,
)
from ...core.exceptions.http_exceptions import UnauthorizedException

router = APIRouter(tags=["google-auth"])


@router.post(
    "/auth/google",
    response_model=GoogleSignInResponse,
    responses={
        400: {"model": GoogleAuthError, "description": "Invalid Google ID token"},
        500: {"model": GoogleAuthError, "description": "Internal server error"},
    },
)
async def google_sign_in(
    request: GoogleSignInRequest,
    db: Annotated[AsyncSession, Depends(async_get_db)],
) -> GoogleSignInResponse:
    """
    Authenticate user with Google ID token.
    
    This endpoint:
    1. Verifies the Google ID token
    2. Extracts user information (email, name, picture)
    3. Creates or updates user in database
    4. Returns JWT access token
    
    Parameters
    ----------
    request : GoogleSignInRequest
        Request containing Google ID token
    db : AsyncSession
        Database session
        
    Returns
    -------
    GoogleSignInResponse
        Response containing JWT access token
        
    Raises
    ------
    HTTPException
        If Google ID token is invalid or authentication fails
    """
    try:
        # Verify Google ID token
        google_user_info = await verify_google_token(request.id_token)
        
        email = google_user_info["email"]
        name = google_user_info["name"]
        picture = google_user_info.get("picture")
        
        # Check if user already exists
        existing_user = await crud_users.get(db=db, email=email, is_deleted=False)
        
        if existing_user:
            # User exists, update name and picture if changed
            existing_user = existing_user[0] if isinstance(existing_user, list) else existing_user
            
            # Check if we need to update user info
            update_data = {}
            if existing_user.get("username") != name:
                update_data["username"] = name
            if existing_user.get("picture") != picture:
                update_data["picture"] = picture
                
            if update_data:
                await crud_users.update(db=db, db_obj=existing_user, obj_in=update_data)
                
            username = existing_user["username"]
        else:
            # User doesn't exist, create new user
            username = extract_username_from_email(email)
            
            # Check if username already exists, if so append a number
            original_username = username
            counter = 1
            while await crud_users.get(db=db, username=username, is_deleted=False):
                username = f"{original_username}{counter}"
                counter += 1
            
            # Generate a random password for Google users
            random_password = generate_password_for_google_user()
            hashed_password = get_password_hash(random_password)
            
            # Create user data
            user_data = {
                "username": username,
                "email": email,
                "password": hashed_password,
                "picture": picture,
                "role": "student",  # Default role for new users
                "exp": 0,
                "streak_days": 0,
            }
            
            # Create user in database
            new_user = await crud_users.create(db=db, obj_in=user_data)
            username = new_user["username"]
        
        # Create JWT access token with 7 days expiration
        access_token_expires = timedelta(days=7)
        access_token = await create_access_token(
            data={"sub": username}, 
            expires_delta=access_token_expires
        )
        
        return GoogleSignInResponse(
            access_token=access_token,
            token_type="bearer"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions from verify_google_token
        raise
    except Exception as e:
        # Handle any unexpected errors
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error during Google authentication"
        ) from e


