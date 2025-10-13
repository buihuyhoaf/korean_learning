#!/usr/bin/env python3
"""
Simple test script for Google authentication helper functions.
"""
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.core.google_auth import verify_google_token, extract_username_from_email, generate_password_for_google_user

async def test_google_auth_helper():
    """Test Google authentication helper functions."""
    try:
        print("Testing Google authentication helper functions...")
        
        # Test extract_username_from_email
        username = extract_username_from_email("test@example.com")
        print(f"Extracted username: {username}")
        
        # Test generate_password_for_google_user
        password = generate_password_for_google_user()
        print(f"Generated password length: {len(password)}")
        
        # Test verify_google_token with fake token (will fail)
        try:
            result = await verify_google_token("fake_token")
            print(f"Token verification result: {result}")
        except Exception as e:
            print(f"Token verification failed (expected): {e}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_google_auth_helper())
