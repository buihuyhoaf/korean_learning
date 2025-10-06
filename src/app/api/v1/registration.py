"""
User registration endpoint for Korean Learning Application.

This module provides a dedicated endpoint for user registration with proper
validation, password hashing, and error handling.
"""

from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import DuplicateValueException
from ...core.security import get_password_hash
from ...schemas.user import UserRegistration, UserRegistrationResponse

router = APIRouter(tags=["registration"])


@router.post(
    "/register",
    response_model=UserRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    description="Create a new user account with username, email, and password. "
               "The password will be hashed using bcrypt before storage.",
    responses={
        201: {
            "description": "User successfully registered",
            "content": {
                "application/json": {
                    "example": {
                        "message": "User registered successfully",
                        "user": {
                            "id": 1,
                            "name": "John Doe",
                            "username": "johndoe",
                            "email": "john@example.com",
                            "profile_image_url": "https://www.profileimageurl.com",
                            "tier_id": None
                        }
                    }
                }
            }
        },
        400: {
            "description": "Validation error or duplicate email/username",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Email is already registered"
                    }
                }
            }
        },
        422: {
            "description": "Request validation error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "type": "string_pattern_mismatch",
                                "loc": ["body", "password"],
                                "msg": "String should match pattern '^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[@$!%*?&])[A-Za-z\\d@$!%*?&]'",
                                "input": "weakpassword"
                            }
                        ]
                    }
                }
            }
        }
    }
)
async def register_user(
    request: Request,
    user_data: UserRegistration,
    db: Annotated[AsyncSession, Depends(async_get_db)]
) -> UserRegistrationResponse:
    """
    Register a new user with username, email, and password.
    
    This endpoint validates the input data, checks for duplicate email/username,
    hashes the password using bcrypt, and creates a new user account.
    
    Parameters
    ----------
    request : Request
        FastAPI request object for logging and rate limiting
    user_data : UserRegistration
        User registration data containing username, email, and password
    db : AsyncSession
        Database session dependency
        
    Returns
    -------
    UserRegistrationResponse
        Success message and created user information (excluding password)
        
    Raises
    ------
    HTTPException
        400: If email or username already exists
        422: If validation fails
        500: If database operation fails
    """
    try:
        # Check if email already exists using raw SQL
        from sqlalchemy import text
        
        email_exists = await db.scalar(text("SELECT id FROM users WHERE email = :email"), {"email": user_data.email})
        if email_exists:
            raise DuplicateValueException("Email is already registered")
        
        # Check if username already exists using raw SQL
        username_exists = await db.scalar(text("SELECT id FROM users WHERE username = :username"), {"username": user_data.username})
        if username_exists:
            raise DuplicateValueException("Username is already taken")
        
        # Hash the password using bcrypt
        hashed_password = get_password_hash(user_data.password)
        
        # Create user using raw SQL to avoid ORM relationship issues
        result = await db.execute(
            text("""
                INSERT INTO users (username, email, password, role, exp, streak_days, created_at)
                VALUES (:username, :email, :password, :role, :exp, :streak_days, NOW())
                RETURNING id, username, email, role, exp, streak_days, created_at
            """),
            {
                "username": user_data.username,
                "email": user_data.email,
                "password": hashed_password,
                "role": "student",
                "exp": 0,
                "streak_days": 0
            }
        )
        
        created_user = result.fetchone()
        await db.commit()
        
        # Return success response with user data (excluding password)
        user_response = {
            "id": created_user.id,
            "username": created_user.username,
            "email": created_user.email,
            "role": created_user.role,
            "exp": created_user.exp,
            "streak_days": created_user.streak_days,
            "created_at": str(created_user.created_at)
        }
        
        return UserRegistrationResponse(
            message="User registered successfully",
            user=user_response
        )
        
    except DuplicateValueException as e:
        # Re-raise duplicate value exceptions as HTTP 400
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        # Log unexpected errors and return generic error
        # In production, you might want to use proper logging here
        print(f"Registration error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred during user registration: {str(e)}"
        )
