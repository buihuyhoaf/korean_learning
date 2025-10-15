"""
Google Authentication helper functions for verifying Google ID tokens.
"""
from typing import Any
import logging
import traceback

from google.auth.transport import requests
from google.oauth2 import id_token
from fastapi import HTTPException, status

from .config import settings

# Setup logging
logger = logging.getLogger(__name__)


async def verify_google_token(id_token_value: str) -> dict[str, Any]:
    """
    Verify Google ID token and extract user information.
    
    Parameters
    ----------
    id_token_value : str
        The Google ID token to verify
        
    Returns
    -------
    dict[str, Any]
        Dictionary containing user information (email, name, picture, etc.)
        
    Raises
    ------
    HTTPException
        If the token is invalid or verification fails
    """
    logger.info(f"[GOOGLE_AUTH] Starting token verification...")
    logger.info(f"[GOOGLE_AUTH] Token length: {len(id_token_value)}")
    logger.info(f"[GOOGLE_AUTH] Token preview: {id_token_value[:50]}...")
    logger.info(f"[GOOGLE_AUTH] Google Client ID: {settings.GOOGLE_CLIENT_ID}")
    
    try:
        # Verify the token
        logger.info(f"[GOOGLE_AUTH] Attempting to verify token with Google...")
        logger.debug(f"[GOOGLE_AUTH] Full token: {id_token_value}")
        
        idinfo = id_token.verify_oauth2_token(
            id_token_value, 
            requests.Request(), 
            settings.GOOGLE_CLIENT_ID
        )
        
        logger.info(f"[GOOGLE_AUTH] Token verification successful!")
        logger.info(f"[GOOGLE_AUTH] Token audience: {idinfo.get('aud', 'NOT_FOUND')}")
        logger.info(f"[GOOGLE_AUTH] Token issuer: {idinfo.get('iss', 'NOT_FOUND')}")
        logger.info(f"[GOOGLE_AUTH] Token email: {idinfo.get('email', 'NOT_FOUND')}")
        logger.info(f"[GOOGLE_AUTH] Token email_verified: {idinfo.get('email_verified', 'NOT_FOUND')}")
        
        # Check if the token was issued for our application
        if idinfo['aud'] != settings.GOOGLE_CLIENT_ID:
            logger.error(f"[GOOGLE_AUTH] Token audience mismatch! Expected: {settings.GOOGLE_CLIENT_ID}, Got: {idinfo['aud']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Google ID token: audience mismatch. Expected {settings.GOOGLE_CLIENT_ID}, got {idinfo['aud']}"
            )
            
        # Extract user information
        user_info = {
            'email': idinfo.get('email'),
            'name': idinfo.get('name'),
            'picture': idinfo.get('picture'),
            'given_name': idinfo.get('given_name'),
            'family_name': idinfo.get('family_name'),
            'email_verified': idinfo.get('email_verified', False),
            'sub': idinfo.get('sub')  # Google user ID
        }
        
        logger.info(f"[GOOGLE_AUTH] Extracted user info: {user_info}")
        
        # Validate required fields
        if not user_info['email']:
            logger.error(f"[GOOGLE_AUTH] No email found in token")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Google ID token: no email found"
            )
            
        if not user_info['email_verified']:
            logger.error(f"[GOOGLE_AUTH] Email not verified: {user_info['email']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Google ID token: email not verified"
            )
            
        logger.info(f"[GOOGLE_AUTH] Token verification completed successfully for user: {user_info['email']}")
        return user_info
        
    except HTTPException as e:
        logger.error(f"[GOOGLE_AUTH] HTTPException during token verification: {e.detail}")
        raise e
    except ValueError as e:
        # Invalid token
        logger.error(f"[GOOGLE_AUTH] ValueError during token verification: {str(e)}")
        logger.error(f"[GOOGLE_AUTH] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Google ID token: {str(e)}"
        ) from e
    except Exception as e:
        # Any other error
        logger.error(f"[GOOGLE_AUTH] Unexpected error during token verification: {str(e)}")
        logger.error(f"[GOOGLE_AUTH] Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error verifying Google ID token: {str(e)}"
        ) from e


def extract_username_from_email(email: str) -> str:
    """
    Extract username from email address.
    
    Parameters
    ----------
    email : str
        Email address
        
    Returns
    -------
    str
        Username extracted from email (part before @)
    """
    return email.split('@')[0]


def generate_password_for_google_user() -> str:
    """
    Generate a random password for Google users.
    Since Google users don't have a password, we generate a random one.
    
    Returns
    -------
    str
        Random password string
    """
    import secrets
    import string
    
    # Generate a random password with 32 characters
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(32))
    return password

