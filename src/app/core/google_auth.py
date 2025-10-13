"""
Google Authentication helper functions for verifying Google ID tokens.
"""
from typing import Any

from google.auth.transport import requests
from google.oauth2 import id_token
from fastapi import HTTPException, status

from .config import settings


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
    try:
        # Verify the token
        idinfo = id_token.verify_oauth2_token(
            id_token_value, 
            requests.Request(), 
            settings.GOOGLE_CLIENT_ID
        )
        
        # Check if the token was issued for our application
        if idinfo['aud'] != settings.GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Google ID token"
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
        
        # Validate required fields
        if not user_info['email'] or not user_info['email_verified']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Google ID token: email not verified"
            )
            
        return user_info
        
    except ValueError as e:
        # Invalid token
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Google ID token"
        ) from e
    except Exception as e:
        # Any other error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verifying Google ID token"
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

