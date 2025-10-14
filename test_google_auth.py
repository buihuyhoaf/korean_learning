#!/usr/bin/env python3
"""
Simple test script for Google authentication endpoint.
"""
import asyncio
import sys
import os

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from app.api.v1.google_auth import google_sign_in
from app.schemas.google_auth import GoogleSignInRequest
from app.core.db.database import async_get_db

async def test_google_auth():
    """Test Google authentication with a fake token."""
    try:
        print("Testing Google authentication endpoint...")
        
        # Create a fake request
        request = GoogleSignInRequest(token="fake_token_for_testing")
        print(f"Request created: {request}")
        
        # This will fail but we can see the debug output
        result = await google_sign_in(request, None)
        print(f"Result: {result}")
        
    except Exception as e:
        print(f"Error (expected): {e}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_google_auth())


