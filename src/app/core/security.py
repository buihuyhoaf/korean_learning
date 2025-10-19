from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Literal, cast

import bcrypt
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession

from ..crud.crud_users import crud_users
from ..crud.crud_user_refresh_token import crud_user_refresh_token
from .config import settings
from .db.crud_token_blacklist import crud_token_blacklist
from .schemas import TokenBlacklistCreate, TokenData
from .exceptions.http_exceptions import UnauthorizedException
from ..schemas.user_refresh_token import UserRefreshTokenCreate

SECRET_KEY: SecretStr = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/login")


class TokenType(str, Enum):
    ACCESS = "access"
    REFRESH = "refresh"


async def verify_password(plain_password: str, hashed_password: str) -> bool:
    correct_password: bool = bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    return correct_password


def get_password_hash(password: str) -> str:
    hashed_password: str = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    return hashed_password


async def authenticate_user(username_or_email: str, password: str, db: AsyncSession) -> dict[str, Any] | Literal[False]:
    if "@" in username_or_email:
        db_user = await crud_users.get(db=db, email=username_or_email, is_deleted=False)
    else:
        db_user = await crud_users.get(db=db, username=username_or_email, is_deleted=False)

    if not db_user:
        return False

    db_user = cast(dict[str, Any], db_user)
    if not await verify_password(password, db_user["password"]):
        return False

    return db_user


async def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # JWT expects the 'exp' field as a timestamp (seconds since epoch)
    to_encode.update({"exp": expire, "token_type": TokenType.ACCESS.value})
    encoded_jwt: str = jwt.encode(to_encode, SECRET_KEY.get_secret_value(), algorithm=ALGORITHM)
    return encoded_jwt


async def create_refresh_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # JWT expects the 'exp' field as a timestamp (seconds since epoch)
    to_encode.update({"exp": expire, "token_type": TokenType.REFRESH.value})
    encoded_jwt: str = jwt.encode(to_encode, SECRET_KEY.get_secret_value(), algorithm=ALGORITHM)
    return encoded_jwt


async def verify_token(token: str, expected_token_type: TokenType, db: AsyncSession) -> TokenData | None:
    """Verify a JWT token and return TokenData if valid.

    Parameters
    ----------
    token: str
        The JWT token to be verified.
    expected_token_type: TokenType
        The expected type of token (access or refresh)
    db: AsyncSession
        Database session for performing database operations.

    Returns
    -------
    TokenData | None
        TokenData instance if the token is valid, None otherwise.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[VERIFY_TOKEN_DEBUG] Verifying token, expected_type: {expected_token_type}, length: {len(token)}")
    
    # Check if token is blacklisted
    is_blacklisted = await crud_token_blacklist.exists(db, token=token)
    if is_blacklisted:
        logger.warning("[VERIFY_TOKEN_DEBUG] Token is blacklisted")
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM])
        logger.info(f"[VERIFY_TOKEN_DEBUG] JWT decode successful, payload keys: {list(payload.keys())}")
        
        username_or_email: str | None = payload.get("sub")
        token_type: str | None = payload.get("token_type")
        
        logger.info(f"[VERIFY_TOKEN_DEBUG] Extracted - sub: {username_or_email}, token_type: {token_type}, expected: {expected_token_type}")

        if username_or_email is None:
            logger.warning("[VERIFY_TOKEN_DEBUG] No 'sub' field in token payload")
            return None
            
        if token_type != expected_token_type.value:
            logger.warning(f"[VERIFY_TOKEN_DEBUG] Token type mismatch: got '{token_type}', expected '{expected_token_type.value}'")
            return None

        logger.info(f"[VERIFY_TOKEN_DEBUG] Token verification successful for user: {username_or_email}")
        return TokenData(username_or_email=username_or_email)

    except JWTError as e:
        logger.error(f"[VERIFY_TOKEN_DEBUG] JWT decode failed: {str(e)}")
        return None


async def blacklist_tokens(access_token: str, refresh_token: str, db: AsyncSession) -> None:
    """Blacklist both access and refresh tokens.

    Parameters
    ----------
    access_token: str
        The access token to blacklist
    refresh_token: str
        The refresh token to blacklist
    db: AsyncSession
        Database session for performing database operations.
    """
    for token in [access_token, refresh_token]:
        payload = jwt.decode(token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM])
        exp_timestamp = payload.get("exp")
        if exp_timestamp is not None:
            expires_at = datetime.fromtimestamp(exp_timestamp)
            await crud_token_blacklist.create(db, object=TokenBlacklistCreate(token=token, expires_at=expires_at))


async def blacklist_token(token: str, db: AsyncSession) -> None:
    payload = jwt.decode(token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM])
    exp_timestamp = payload.get("exp")
    if exp_timestamp is not None:
        expires_at = datetime.fromtimestamp(exp_timestamp)
        await crud_token_blacklist.create(db, object=TokenBlacklistCreate(token=token, expires_at=expires_at))


async def create_refresh_token_with_storage(data: dict[str, Any], user_id: int, db: AsyncSession, expires_delta: timedelta | None = None) -> str:
    """Create a refresh token and store it in the database"""
    import logging
    logger = logging.getLogger(__name__)
    
    # Create the refresh token JWT first
    refresh_token = await create_refresh_token(data, expires_delta)
    
    # Decode the JWT to get the exact expiration time that was set
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM], options={"verify_exp": False})
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            # Convert timestamp back to datetime for database storage
            expire = datetime.fromtimestamp(exp_timestamp, tz=UTC)
        else:
            # Fallback calculation
            expire = datetime.now(UTC) + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    except Exception as e:
        logger.error(f"[REFRESH_TOKEN_STORAGE_DEBUG] Failed to decode token for expiration: {e}")
        # Fallback calculation
        expire = datetime.now(UTC) + (expires_delta or timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))
    
    # Store refresh token in database
    refresh_token_data = UserRefreshTokenCreate(
        user_id=user_id,
        token=refresh_token,
        expires_at=expire
    )
    
    logger.info(f"[REFRESH_TOKEN_STORAGE_DEBUG] Storing refresh token for user_id: {user_id}")
    logger.info(f"[REFRESH_TOKEN_STORAGE_DEBUG] Token expires_at: {expire}")
    logger.info(f"[REFRESH_TOKEN_STORAGE_DEBUG] Token length: {len(refresh_token)}")
    logger.info(f"[REFRESH_TOKEN_STORAGE_DEBUG] Token starts with: {refresh_token[:50]}...")
    
    try:
        # Store refresh token in database and commit
        created_token = await crud_user_refresh_token.create(db=db, object=refresh_token_data)
        await db.commit()  # Ensure database transaction is committed
        
        logger.info(f"[REFRESH_TOKEN_STORAGE_DEBUG] Token stored successfully with ID: {created_token.id}")
        
        # Verify the token was actually stored by retrieving it
        verification_check = await crud_user_refresh_token.get_by_token(db, refresh_token)
        if verification_check:
            logger.info(f"[REFRESH_TOKEN_STORAGE_DEBUG] Token verification successful - retrieved from DB")
        else:
            logger.error(f"[REFRESH_TOKEN_STORAGE_DEBUG] Token verification FAILED - not found in DB after storage!")
            
        return refresh_token
        
    except Exception as e:
        logger.error(f"[REFRESH_TOKEN_STORAGE_DEBUG] Failed to store refresh token: {e}")
        await db.rollback()
        raise


async def verify_refresh_token(token: str, db: AsyncSession) -> str:
    """Verify refresh token and return username/email"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[REFRESH_TOKEN_VERIFY_DEBUG] Verifying refresh token, length: {len(token)}")
    logger.info(f"[REFRESH_TOKEN_VERIFY_DEBUG] Token starts with: {token[:50]}...")
    
    # Step 1: Verify JWT structure and signature FIRST
    try:
        payload = jwt.decode(token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM])
        logger.info(f"[REFRESH_TOKEN_VERIFY_DEBUG] JWT decode successful, payload keys: {list(payload.keys())}")
        
        username_or_email = payload.get("sub")
        token_type = payload.get("token_type")
        
        if not username_or_email:
            logger.warning("[REFRESH_TOKEN_VERIFY_DEBUG] No 'sub' field in token payload")
            raise UnauthorizedException("Invalid refresh token")
        
        if token_type != TokenType.REFRESH.value:
            logger.warning(f"[REFRESH_TOKEN_VERIFY_DEBUG] Token type mismatch: got '{token_type}', expected '{TokenType.REFRESH.value}'")
            raise UnauthorizedException("Invalid refresh token")
        
    except JWTError as e:
        logger.error(f"[REFRESH_TOKEN_VERIFY_DEBUG] JWT decode failed: {str(e)}")
        raise UnauthorizedException("Invalid refresh token")
    
    # Step 2: Check if token exists in database
    db_token_record = await crud_user_refresh_token.get_by_token(db, token)
    if not db_token_record:
        logger.warning("[REFRESH_TOKEN_VERIFY_DEBUG] Token not found in database - this indicates the token was revoked or never properly stored")
        # Log additional debug info
        logger.info(f"[REFRESH_TOKEN_VERIFY_DEBUG] User: {username_or_email}, Token length: {len(token)}")
        raise UnauthorizedException("Invalid refresh token")
    
    # Step 3: Check if token is expired in database
    now = datetime.now(UTC)
    if db_token_record.expires_at <= now:
        logger.warning(f"[REFRESH_TOKEN_VERIFY_DEBUG] Token expired in database. Expires: {db_token_record.expires_at}, Now: {now}")
        # Delete expired token from database and commit
        await crud_user_refresh_token.delete_token(db, token)
        await db.commit()
        raise UnauthorizedException("Refresh token expired")
    
    # Step 4: Check if token is blacklisted (ONLY after confirming it exists and is valid)
    is_blacklisted = await crud_token_blacklist.exists(db, token=token)
    if is_blacklisted:
        logger.warning(f"[REFRESH_TOKEN_VERIFY_DEBUG] Token is blacklisted for user: {username_or_email}")
        logger.warning(f"[REFRESH_TOKEN_VERIFY_DEBUG] Token was blacklisted but still exists in DB - cleaning up")
        # Clean up: delete the token from database since it's blacklisted but still there due to race condition
        try:
            await crud_user_refresh_token.delete_token(db, token)
            await db.commit()
            logger.info(f"[REFRESH_TOKEN_VERIFY_DEBUG] Cleaned up blacklisted token from database")
        except Exception as cleanup_error:
            logger.error(f"[REFRESH_TOKEN_VERIFY_DEBUG] Failed to cleanup blacklisted token: {cleanup_error}")
        raise UnauthorizedException("Invalid refresh token")
    
    logger.info(f"[REFRESH_TOKEN_VERIFY_DEBUG] Token verification successful for user: {username_or_email}")
    logger.info(f"[REFRESH_TOKEN_VERIFY_DEBUG] Token expires at: {db_token_record.expires_at}")
    return username_or_email


async def rotate_refresh_token(old_refresh_token: str, user_id: int, username_or_email: str, db: AsyncSession) -> tuple[str, str]:
    """Rotate refresh token: invalidate old one and create new access/refresh tokens"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[TOKEN_ROTATION_DEBUG] Rotating tokens for user_id: {user_id}")
    logger.info(f"[TOKEN_ROTATION_DEBUG] Old token length: {len(old_refresh_token)}")
    
    # Create new access token
    new_access_token = await create_access_token(data={"sub": username_or_email})
    
    # Create new refresh token
    new_refresh_token = await create_refresh_token(data={"sub": username_or_email})
    
    # Get the exact expiration time from the JWT
    try:
        payload = jwt.decode(new_refresh_token, SECRET_KEY.get_secret_value(), algorithms=[ALGORITHM], options={"verify_exp": False})
        exp_timestamp = payload.get("exp")
        if exp_timestamp:
            expire = datetime.fromtimestamp(exp_timestamp, tz=UTC)
        else:
            expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    except Exception as e:
        logger.error(f"[TOKEN_ROTATION_DEBUG] Failed to decode token for expiration: {e}")
        expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    
    # CRITICAL: Store new refresh token FIRST, then invalidate old token atomically
    try:
        # Step 1: Store new refresh token in database
        refresh_token_data = UserRefreshTokenCreate(
            user_id=user_id,
            token=new_refresh_token,
            expires_at=expire
        )
        created_token = await crud_user_refresh_token.create(db=db, object=refresh_token_data)
        logger.info(f"[TOKEN_ROTATION_DEBUG] New refresh token stored in database with ID: {created_token.id}")
        
        # Step 2: Delete old refresh token from database FIRST (to prevent verification during rotation)
        deleted = await crud_user_refresh_token.delete_token(db, old_refresh_token)
        logger.info(f"[TOKEN_ROTATION_DEBUG] Old token deleted from database: {deleted}")
        
        # Step 3: Blacklist old refresh token AFTER deleting from DB (to prevent reuse)
        await blacklist_token(old_refresh_token, db)
        logger.info(f"[TOKEN_ROTATION_DEBUG] Old token blacklisted")
        
        # Commit all changes atomically
        await db.commit()
        logger.info(f"[TOKEN_ROTATION_DEBUG] All changes committed successfully")
        
    except Exception as e:
        logger.error(f"[TOKEN_ROTATION_DEBUG] Error during token rotation: {e}")
        await db.rollback()
        raise
    
    logger.info(f"[TOKEN_ROTATION_DEBUG] Token rotation completed successfully for user_id: {user_id}")
    
    return new_access_token, new_refresh_token


async def invalidate_user_refresh_tokens(user_id: int, db: AsyncSession) -> None:
    """Invalidate all refresh tokens for a user"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[INVALIDATE_TOKENS_DEBUG] Invalidating all refresh tokens for user_id: {user_id}")
    
    # Get all user's refresh tokens
    user_tokens = await crud_user_refresh_token.get_by_user_id(db, user_id)
    
    # Blacklist each token
    for token_obj in user_tokens:
        await blacklist_token(token_obj.token, db)
    
    # Delete all tokens from database
    await crud_user_refresh_token.delete_user_tokens(db, user_id)
    
    logger.info(f"[INVALIDATE_TOKENS_DEBUG] Invalidated {len(user_tokens)} refresh tokens for user_id: {user_id}")


async def invalidate_refresh_token(token: str, db: AsyncSession) -> None:
    """Invalidate a specific refresh token"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info(f"[INVALIDATE_TOKEN_DEBUG] Invalidating refresh token, length: {len(token)}")
    
    try:
        # Step 1: Delete from database FIRST (to prevent verification during invalidation)
        deleted = await crud_user_refresh_token.delete_token(db, token)
        logger.info(f"[INVALIDATE_TOKEN_DEBUG] Token deleted from database: {deleted}")
        
        # Step 2: Blacklist the token AFTER deleting (to prevent reuse)
        await blacklist_token(token, db)
        logger.info(f"[INVALIDATE_TOKEN_DEBUG] Token blacklisted")
        
        # Commit the transaction
        await db.commit()
        logger.info(f"[INVALIDATE_TOKEN_DEBUG] Refresh token invalidated successfully")
        
    except Exception as e:
        logger.error(f"[INVALIDATE_TOKEN_DEBUG] Error invalidating refresh token: {e}")
        await db.rollback()
        raise
