#!/usr/bin/env python3
"""
Test script để kiểm tra Quiz API sau khi sửa lỗi AsyncSession
"""
import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_quiz_api():
    print("=== Testing Quiz API ===")
    
    # Test 1: Get quiz without auth (should fail)
    print("\n1. Testing quiz API without authentication:")
    response = requests.get(f"{BASE_URL}/quizzes/1")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Test 2: Get quiz with invalid token (should fail)
    print("\n2. Testing quiz API with invalid token:")
    headers = {"Authorization": "Bearer invalid_token"}
    response = requests.get(f"{BASE_URL}/quizzes/1", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Test 3: Test lesson API (should work if we have data)
    print("\n3. Testing lesson API:")
    response = requests.get(f"{BASE_URL}/lessons/1")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
    
    # Test 4: Test courses API
    print("\n4. Testing courses API:")
    response = requests.get(f"{BASE_URL}/courses")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")

if __name__ == "__main__":
    test_quiz_api()







