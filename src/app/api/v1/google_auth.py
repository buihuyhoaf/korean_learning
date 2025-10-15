"""
Google Authentication endpoints.
"""
from datetime import timedelta
from typing import Annotated
import logging
import traceback

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
logger = logging.getLogger(__name__)


@router.post("/auth/google/test")
async def google_sign_in_test(request: GoogleSignInRequest):
    """Simple test endpoint without dependencies"""
    print("=== TEST ENDPOINT CALLED ===")
    return {"message": "Test endpoint works", "token_length": len(request.token)}


@router.post("/auth/google/simple")
async def google_sign_in_simple():
    """Ultra simple endpoint without any parameters"""
    print("=== SIMPLE ENDPOINT CALLED ===")
    return {"message": "Simple endpoint works"}


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
    print("=== GOOGLE AUTH ENDPOINT CALLED ===")  # Debug print
    logger.info(f"[GOOGLE_AUTH_ENDPOINT] Starting Google sign-in process...")
    logger.info(f"[GOOGLE_AUTH_ENDPOINT] Request token length: {len(request.token)}")
    logger.info(f"[GOOGLE_AUTH_ENDPOINT] Request token preview: {request.token[:50]}...")
    
    try:
        # Test basic functionality first
        print(f"[DEBUG] Request object: {request}")
        print(f"[DEBUG] Database session: {db}")
        print(f"[DEBUG] Settings GOOGLE_CLIENT_ID: {settings.GOOGLE_CLIENT_ID}")
        # Verify Google ID token
        logger.info(f"[GOOGLE_AUTH_ENDPOINT] Step 1: Verifying Google ID token...")
        google_user_info = await verify_google_token(request.token)
        logger.info(f"[GOOGLE_AUTH_ENDPOINT] Token verification successful!")
        
        email = google_user_info['email']
        name = google_user_info.get('name', '')
        picture = google_user_info.get('picture', '')
        
        logger.info(f"[GOOGLE_AUTH_ENDPOINT] Step 2: Processing user info - Email: {email}, Name: {name}")
        
        # Check if user already exists
        logger.info(f"[GOOGLE_AUTH_ENDPOINT] Step 3: Checking if user exists in database...")
        existing_user = await crud_users.get(db=db, email=email)
        logger.info(f"[GOOGLE_AUTH_ENDPOINT] User exists check result: {existing_user is not None}")
        
        if existing_user:
            # User exists, get username
            logger.info(f"[GOOGLE_AUTH_ENDPOINT] Step 4a: User exists, retrieving username...")
            existing_user = existing_user[0] if isinstance(existing_user, list) else existing_user
            username = existing_user["username"]
            logger.info(f"[GOOGLE_AUTH_ENDPOINT] Existing user username: {username}")
        else:
            # User doesn't exist, create new user
            logger.info(f"[GOOGLE_AUTH_ENDPOINT] Step 4b: User doesn't exist, creating new user...")
            username = extract_username_from_email(email)
            logger.info(f"[GOOGLE_AUTH_ENDPOINT] Initial username: {username}")
            
            # Check if username already exists, if so append a number
            original_username = username
            counter = 1
            while await crud_users.get(db=db, username=username):
                username = f"{original_username}{counter}"
                counter += 1
                logger.info(f"[GOOGLE_AUTH_ENDPOINT] Username conflict, trying: {username}")
            
            logger.info(f"[GOOGLE_AUTH_ENDPOINT] Final username: {username}")
            
            # Generate a random password for Google users
            logger.info(f"[GOOGLE_AUTH_ENDPOINT] Generating password for Google user...")
            random_password = generate_password_for_google_user()
            hashed_password = get_password_hash(random_password)
            
            # Create user data
            logger.info(f"[GOOGLE_AUTH_ENDPOINT] Creating user data object...")
            from ...schemas.user import UserCreateInternal
            
            user_data = UserCreateInternal(
                username=username,
                email=email,
                hashed_password=hashed_password,
            )
            
            # Create user in database
            logger.info(f"[GOOGLE_AUTH_ENDPOINT] Saving user to database...")
            new_user = await crud_users.create(db=db, object=user_data)
            logger.info(f"[GOOGLE_AUTH_ENDPOINT] User created successfully: {new_user}")
            username = new_user["username"]
        
        # Create JWT access token with 7 days expiration
        logger.info(f"[GOOGLE_AUTH_ENDPOINT] Step 5: Creating JWT access token for username: {username}")
        access_token_expires = timedelta(days=7)
        access_token = await create_access_token(
            data={"sub": username}, 
            expires_delta=access_token_expires
        )
        logger.info(f"[GOOGLE_AUTH_ENDPOINT] JWT token created successfully")
        
        response = GoogleSignInResponse(
            token=access_token,
            token_type="bearer"
        )
        
        logger.info(f"[GOOGLE_AUTH_ENDPOINT] Google sign-in completed successfully for user: {email}")
        return response
        
    except HTTPException as e:
        logger.error(f"[GOOGLE_AUTH_ENDPOINT] HTTPException: {e.detail}")
        logger.error(f"[GOOGLE_AUTH_ENDPOINT] HTTPException status: {e.status_code}")
        raise e
    except Exception as e:
        # Log error for debugging
        logger.error(f"[GOOGLE_AUTH_ENDPOINT] Unexpected error during Google authentication: {str(e)}")
        logger.error(f"[GOOGLE_AUTH_ENDPOINT] Error type: {type(e).__name__}")
        logger.error(f"[GOOGLE_AUTH_ENDPOINT] Full traceback: {traceback.format_exc()}")
        
        error_detail = f"Internal server error during Google authentication: {str(e)}"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        ) from e