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
from ...crud.crud_users import crud_users, create_user_safe
from ...schemas.google_auth import (
    GoogleSignInRequest,
    GoogleSignInResponse,
    GoogleAuthError,
)
from ...core.exceptions.http_exceptions import UnauthorizedException

router = APIRouter(tags=["google-auth"])
logger = logging.getLogger(__name__)


@router.post("/auth/google/debug")
async def google_sign_in_debug(request: GoogleSignInRequest):
    """Debug endpoint without dependencies to test basic functionality"""
    print("=== DEBUG ENDPOINT CALLED ===")
    print(f"[DEBUG] Request received: {request}")
    print(f"[DEBUG] Token: {request.token}")
    return {"message": "Debug endpoint works", "token": request.token}


@router.post("/auth/google/simple")
async def google_sign_in_simple():
    """Ultra simple endpoint without any parameters"""
    print("=== SIMPLE ENDPOINT CALLED ===")
    return {"message": "Simple endpoint works"}


@router.post("/auth/google/test-simple")
async def google_sign_in_test_simple():
    """Ultra simple endpoint without any parameters"""
    print("=== TEST SIMPLE ENDPOINT CALLED ===")
    return {"message": "Test simple endpoint works"}


@router.post("/auth/google/test-with-request")
async def google_sign_in_test_with_request(request: GoogleSignInRequest):
    """Test endpoint with request but no DB dependency"""
    print("=== TEST WITH REQUEST ENDPOINT CALLED ===")
    print(f"Token received: {request.token}")
    return {"message": "Test with request works", "token_length": len(request.token)}


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
    # Add debug output at the very beginning
    import sys
    import os
    
    # Write to a temporary file for debugging
    with open("/tmp/google_auth_debug.txt", "a") as f:
        f.write(f"=== GOOGLE AUTH ENDPOINT CALLED at {os.getpid()} ===\n")
        f.write(f"Token length: {len(request.token)}\n")
        f.write(f"Token preview: {request.token[:50]}...\n")
        f.flush()
    
    sys.stdout.flush()
    print("=== GOOGLE AUTH ENDPOINT CALLED ===", flush=True)  # Debug print
    logger.info(f"[GOOGLE_AUTH_ENDPOINT] Starting Google sign-in process...")
    logger.info(f"[GOOGLE_AUTH_ENDPOINT] Request token length: {len(request.token)}")
    logger.info(f"[GOOGLE_AUTH_ENDPOINT] Request token preview: {request.token[:50]}...")
    
    try:
        # Test basic functionality first
        print(f"[DEBUG] Request object: {request}")
        print(f"[DEBUG] Database session: {db}")
        print(f"[DEBUG] Settings GOOGLE_CLIENT_ID: {settings.GOOGLE_CLIENT_ID}")
        print(f"[DEBUG] About to call verify_google_token...")
        # Verify Google ID token
        logger.info(f"[GOOGLE_AUTH_ENDPOINT] Step 1: Verifying Google ID token...")
        google_user_info = await verify_google_token(request.token)
        logger.info(f"[GOOGLE_AUTH_ENDPOINT] Token verification successful!")
        
        email = google_user_info['email']
        name = google_user_info.get('name', '')
        picture = google_user_info.get('picture', '')
        
        logger.info(f"[GOOGLE_AUTH_ENDPOINT] Step 2: Processing user info - Email: {email}, Name: {name}")
        logger.info(f"[GOOGLE_AUTH_ENDPOINT] Full Google user info: {google_user_info}")
        
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
                password=hashed_password,
                picture=picture,
                role="student",
                exp=0,
                streak_days=0,
                tier_id=None,
            )
            
            # Create user in database
            logger.info(f"[GOOGLE_AUTH_ENDPOINT] Saving user to database...")
            new_user = await create_user_safe(db=db, user_data=user_data)
            logger.info(f"[GOOGLE_AUTH_ENDPOINT] User created successfully: {new_user}")
            username = new_user.username
        
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
        # Write error to file for debugging
        import datetime
        with open("/tmp/google_auth_http_exception.txt", "a") as f:
            f.write(f"\n\n===== HTTPException at {datetime.datetime.now()} =====\n")
            f.write(f"Detail: {e.detail}\n")
            f.write(f"Status code: {e.status_code}\n")
            f.write("="*50 + "\n")
            f.flush()
        
        print(f"[GOOGLE_AUTH_ENDPOINT] HTTPException: {e.detail}")
        print(f"[GOOGLE_AUTH_ENDPOINT] HTTPException status: {e.status_code}")
        logger.error(f"[GOOGLE_AUTH_ENDPOINT] HTTPException: {e.detail}")
        logger.error(f"[GOOGLE_AUTH_ENDPOINT] HTTPException status: {e.status_code}")
        raise e
    except Exception as e:
        # Write error to file for debugging
        import datetime
        with open("/tmp/google_auth_error.txt", "a") as f:
            f.write(f"\n\n===== ERROR at {datetime.datetime.now()} =====\n")
            f.write(f"Error: {str(e)}\n")
            f.write(f"Error type: {type(e).__name__}\n")
            f.write(f"Full traceback:\n{traceback.format_exc()}\n")
            f.write("="*50 + "\n")
            f.flush()
        
        # Log error for debugging - use print for immediate visibility in Docker logs
        print(f"[GOOGLE_AUTH_ENDPOINT] ===== UNEXPECTED ERROR =====")
        print(f"[GOOGLE_AUTH_ENDPOINT] Error: {str(e)}")
        print(f"[GOOGLE_AUTH_ENDPOINT] Error type: {type(e).__name__}")
        print(f"[GOOGLE_AUTH_ENDPOINT] Full traceback:")
        print(traceback.format_exc())
        print(f"[GOOGLE_AUTH_ENDPOINT] ===========================")
        
        # Also log to logger
        logger.error(f"[GOOGLE_AUTH_ENDPOINT] Unexpected error during Google authentication: {str(e)}")
        logger.error(f"[GOOGLE_AUTH_ENDPOINT] Error type: {type(e).__name__}")
        logger.error(f"[GOOGLE_AUTH_ENDPOINT] Full traceback: {traceback.format_exc()}")
        
        error_detail = f"Internal server error during Google authentication"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=error_detail
        ) from e