from typing import List, Optional
from fastcrud import FastCRUD
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from datetime import datetime, UTC

from ..models.user_refresh_token import UserRefreshToken
from ..schemas.user_refresh_token import (
    UserRefreshTokenCreate, 
    UserRefreshTokenUpdate, 
    UserRefreshTokenUpdateInternal, 
    UserRefreshTokenDelete, 
    UserRefreshTokenRead
)


class CRUDUserRefreshToken(FastCRUD[UserRefreshToken, UserRefreshTokenCreate, UserRefreshTokenUpdate, UserRefreshTokenUpdateInternal, UserRefreshTokenDelete, UserRefreshTokenRead]):
    async def get_by_token(self, db: AsyncSession, token: str) -> Optional[UserRefreshToken]:
        """Get refresh token by token string"""
        result = await db.execute(select(UserRefreshToken).where(UserRefreshToken.token == token))
        return result.scalar_one_or_none()

    async def get_by_user_id(self, db: AsyncSession, user_id: int) -> List[UserRefreshToken]:
        """Get all refresh tokens for a user"""
        result = await db.execute(select(UserRefreshToken).where(UserRefreshToken.user_id == user_id))
        return result.scalars().all()

    async def delete_expired_tokens(self, db: AsyncSession) -> int:
        """Delete all expired refresh tokens"""
        now = datetime.now(UTC)
        result = await db.execute(
            delete(UserRefreshToken).where(UserRefreshToken.expires_at < now)
        )
        await db.commit()
        return result.rowcount

    async def delete_user_tokens(self, db: AsyncSession, user_id: int) -> int:
        """Delete all refresh tokens for a specific user"""
        result = await db.execute(
            delete(UserRefreshToken).where(UserRefreshToken.user_id == user_id)
        )
        await db.commit()
        return result.rowcount

    async def delete_token(self, db: AsyncSession, token: str) -> bool:
        """Delete a specific refresh token"""
        result = await db.execute(
            delete(UserRefreshToken).where(UserRefreshToken.token == token)
        )
        # Note: Don't commit here - let the calling service control the transaction
        return result.rowcount > 0

    async def is_token_valid(self, db: AsyncSession, token: str) -> bool:
        """Check if a refresh token is valid and not expired"""
        import logging
        logger = logging.getLogger(__name__)
        
        logger.info(f"[CRUD_REFRESH_TOKEN_DEBUG] Checking token validity, length: {len(token)}")
        
        refresh_token = await self.get_by_token(db, token)
        if not refresh_token:
            logger.warning("[CRUD_REFRESH_TOKEN_DEBUG] Token not found in database")
            return False
        
        now = datetime.now(UTC)
        is_valid = refresh_token.expires_at > now
        logger.info(f"[CRUD_REFRESH_TOKEN_DEBUG] Token found, expires_at: {refresh_token.expires_at}, now: {now}, is_valid: {is_valid}")
        
        return is_valid


crud_user_refresh_token = CRUDUserRefreshToken(UserRefreshToken)

