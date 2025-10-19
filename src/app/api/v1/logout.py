from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Response, Request
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.db.database import async_get_db
from ...core.exceptions.http_exceptions import UnauthorizedException
from ...core.security import (
    blacklist_tokens, 
    blacklist_token,
    oauth2_scheme, 
    verify_token, 
    TokenType, 
    invalidate_refresh_token,
    invalidate_user_refresh_tokens
)
from ...crud.crud_users import crud_users

router = APIRouter(tags=["login"])


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    access_token: str = Depends(oauth2_scheme),
    refresh_token: Optional[str] = Cookie(None, alias="refresh_token"),
    db: AsyncSession = Depends(async_get_db),
) -> dict[str, str]:
    try:
        # Get refresh token from request body or cookies
        if not refresh_token:
            try:
                body = await request.json()
                refresh_token = body.get("refresh_token")
            except:
                pass

        # Verify access token to get user info
        token_data = await verify_token(access_token, TokenType.ACCESS, db)
        if not token_data:
            raise UnauthorizedException("Invalid access token")

        # Get user to find user_id
        if "@" in token_data.username_or_email:
            db_user = await crud_users.get(db=db, email=token_data.username_or_email, is_deleted=False)
        else:
            db_user = await crud_users.get(db=db, username=token_data.username_or_email, is_deleted=False)
        
        if not db_user:
            raise UnauthorizedException("User not found")

        try:
            # Only invalidate the specific refresh token used for logout, not all user tokens
            if refresh_token:
                await invalidate_refresh_token(refresh_token, db)
            
            # Blacklist the access token
            await blacklist_token(access_token, db)
            
            # Commit all logout operations atomically
            await db.commit()
            
            # Clear refresh token cookie
            if refresh_token:
                response.delete_cookie(key="refresh_token")

            return {"message": "Logged out successfully"}
            
        except Exception as e:
            await db.rollback()
            raise

    except JWTError:
        raise UnauthorizedException("Invalid token.")
