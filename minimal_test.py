#!/usr/bin/env python3
"""
Minimal test server for Google authentication.
This bypasses all the complex dependencies and just tests the core functionality.
"""
import asyncio
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class GoogleSignInRequest(BaseModel):
    token: str

class GoogleSignInResponse(BaseModel):
    token: str
    token_type: str = "bearer"

@app.post("/api/v1/auth/google")
async def google_sign_in(request: GoogleSignInRequest):
    """Minimal Google auth endpoint for testing."""
    try:
        print(f"[DEBUG] Received Google token: {request.token[:50]}...")
        
        # For testing, just return a mock response
        # In real implementation, this would verify the Google token
        
        mock_jwt_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.mock.jwt.token"
        
        print(f"[DEBUG] Returning mock JWT token")
        
        return GoogleSignInResponse(
            token=mock_jwt_token,
            token_type="bearer"
        )
        
    except Exception as e:
        print(f"[ERROR] Google authentication failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error during Google authentication"
        )

if __name__ == "__main__":
    import uvicorn
    print("Starting minimal test server...")
    print("Test with: curl -X POST http://localhost:8000/api/v1/auth/google -H 'Content-Type: application/json' -d '{\"token\": \"test_token\"}'")
    uvicorn.run(app, host="0.0.0.0", port=8000)
