#!/usr/bin/env python3
"""Test authentication for dashboard_stats endpoint."""

import os
import sys

# Set environment before importing ANY acas_pro module
os.environ['LLM_API_KEY'] = 'test-key-for-testing'
os.environ['ACAS_SECRET_KEY'] = 'test-secret-key-for-testing-only-32chars'
os.environ['ACAS_ENVIRONMENT'] = 'testing'

from acas_pro.core.config import reset_config, get_config
reset_config()  # Clear any cached config

from acas_pro.web import create_app
from acas_pro.web.routes.auth import generate_token

def test_dashboard_stats_auth():
    """Test that /api/dashboard/stats requires authentication."""
    app = create_app()
    app.config['TESTING'] = True
    
    with app.test_client() as client:
        # Test 1: Without auth, should return 401
        print("Test 1: Accessing /api/dashboard/stats without auth...")
        response = client.get('/api/dashboard/stats')
        print(f"  Status: {response.status_code}")
        if response.status_code == 401:
            print("  PASS: Returns 401 as expected")
        else:
            print(f"  FAIL: Expected 401, got {response.status_code}")
            print(f"  Response: {response.get_json()}")
        
        # Test 2: With valid auth, should return data
        print("\nTest 2: Accessing /api/dashboard/stats with valid auth...")
        token = generate_token('1', 'testuser')
        response = client.get(
            '/api/dashboard/stats',
            headers={'Authorization': f'Bearer {token}'}
        )
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            print("  PASS: Returns 200 with valid auth")
            data = response.get_json()
            print(f"  Data keys: {list(data.keys())}")
        else:
            print(f"  FAIL: Expected 200, got {response.status_code}")
            print(f"  Response: {response.get_json()}")

if __name__ == '__main__':
    test_dashboard_stats_auth()
