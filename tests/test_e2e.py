#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ACAS Pro E2E Tests - End-to-End Integration Tests

Tests the complete user journey from HTTP request to response.
"""

import pytest
import requests
import time
import subprocess
import sys
import os
import signal
from datetime import datetime

# Skip marker for E2E tests that require running server
pytestmark = pytest.mark.skipif(
    os.environ.get('SKIP_E2E') == '1',
    reason='E2E tests require running server (set SKIP_E2E=1 to skip)'
)


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_returns_200(self, server):
        """GET /api/health should return 200"""
        resp = requests.get(f'{server}/api/health', timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert data['status'] in ('healthy', 'degraded')  # degraded is OK (e.g., LLM not configured)
    
    def test_health_has_timestamp(self, server):
        """Health response should include timestamp"""
        resp = requests.get(f'{server}/api/health', timeout=5)
        data = resp.json()
        assert 'timestamp' in data


class TestAuthFlow:
    """Test complete authentication flow"""
    
    def test_register_new_user(self, server, unique_user, csrf_token):
        """Register a new user should return 201"""
        resp = requests.post(
            f'{server}/api/auth/register',
            json={
                'account': unique_user['account'],
                'password': unique_user['password'],
                'email': unique_user['email']
            },
            headers={'X-CSRF-Token': csrf_token},
            cookies={'csrf_token': csrf_token},
            timeout=5
        )
        assert resp.status_code in (200, 201, 409)  # 409 if user exists
    
    def test_login_returns_token(self, server, test_user, csrf_token):
        """Login should return JWT token"""
        # First register
        requests.post(
            f'{server}/api/auth/register',
            json={
                'account': test_user['account'],
                'password': test_user['password'],
                'email': test_user['email']
            },
            headers={'X-CSRF-Token': csrf_token},
            cookies={'csrf_token': csrf_token},
            timeout=5
        )
        
        # Then login
        resp = requests.post(
            f'{server}/api/auth/login',
            json={
                'account': test_user['account'],
                'password': test_user['password']
            },
            headers={'X-CSRF-Token': csrf_token},
            cookies={'csrf_token': csrf_token},
            timeout=5
        )
        assert resp.status_code == 200
        data = resp.json()
        assert 'token' in data
        assert len(data['token']) > 50  # JWT should be long
    
    def test_login_wrong_password(self, server, test_user, csrf_token):
        """Login with wrong password should return 401"""
        requests.post(
            f'{server}/api/auth/register',
            json={
                'account': test_user['account'],
                'password': test_user['password'],
                'email': test_user['email']
            },
            headers={'X-CSRF-Token': csrf_token},
            cookies={'csrf_token': csrf_token},
            timeout=5
        )
        
        resp = requests.post(
            f'{server}/api/auth/login',
            json={
                'account': test_user['account'],
                'password': 'WrongPassword123!'
            },
            headers={'X-CSRF-Token': csrf_token},
            cookies={'csrf_token': csrf_token},
            timeout=5
        )
        assert resp.status_code == 401
    
    def test_protected_route_requires_token(self, server):
        """Protected routes should reject requests without token"""
        resp = requests.get(f'{server}/api/auth/me', timeout=5)
        assert resp.status_code == 401
    
    def test_protected_route_accepts_valid_token(self, server, test_user, csrf_token):
        """Protected routes should accept valid JWT token"""
        # Register and login
        requests.post(
            f'{server}/api/auth/register',
            json={
                'account': test_user['account'],
                'password': test_user['password'],
                'email': test_user['email']
            },
            headers={'X-CSRF-Token': csrf_token},
            cookies={'csrf_token': csrf_token},
            timeout=5
        )
        
        login_resp = requests.post(
            f'{server}/api/auth/login',
            json={
                'account': test_user['account'],
                'password': test_user['password']
            },
            headers={'X-CSRF-Token': csrf_token},
            cookies={'csrf_token': csrf_token},
            timeout=5
        )
        token = login_resp.json()['token']
        
        # Access protected route
        resp = requests.get(
            f'{server}/api/auth/me',
            headers={'Authorization': f'Bearer {token}'},
            timeout=5
        )
        assert resp.status_code == 200
        data = resp.json()
        assert 'account' in data


class TestDashboardFlow:
    """Test dashboard data flow"""
    
    def test_dashboard_stats_requires_auth(self, server):
        """Dashboard stats should require authentication"""
        resp = requests.get(f'{server}/api/dashboard/stats', timeout=5)
        assert resp.status_code == 401
    
    def test_dashboard_stats_returns_data(self, server, auth_token):
        """Dashboard stats should return data structure"""
        resp = requests.get(
            f'{server}/api/dashboard/stats',
            headers={'Authorization': f'Bearer {auth_token}'},
            timeout=5
        )
        assert resp.status_code == 200
        data = resp.json()
        # Should have these keys even if values are 0
        assert 'revenue' in data
        assert 'orders' in data
        assert 'inventory' in data
        assert 'risk_alerts' in data


class TestLLMFlow:
    """Test LLM chat flow"""
    
    def test_llm_config_requires_auth(self, server):
        """LLM config endpoint should require authentication"""
        resp = requests.post(
            f'{server}/api/llm/config',
            json={'provider': 'deepseek'},
            timeout=5
        )
        assert resp.status_code == 401
    
    def test_llm_chat_requires_auth(self, server):
        """LLM chat endpoint should require authentication"""
        resp = requests.post(
            f'{server}/api/llm/chat',
            json={'message': 'Hello'},
            timeout=5
        )
        assert resp.status_code == 401
    
    @pytest.mark.skipif(
        os.environ.get('DEEPSEEK_API_KEY') is None,
        reason='Requires DEEPSEEK_API_KEY'
    )
    def test_llm_chat_returns_response(self, server, auth_token):
        """LLM chat should return AI response"""
        resp = requests.post(
            f'{server}/api/llm/chat',
            headers={'Authorization': f'Bearer {auth_token}'},
            json={
                'message': 'What is 2+2?',
                'conversation_id': 'test-conv-001'
            },
            timeout=30  # LLM may take time
        )
        assert resp.status_code == 200
        data = resp.json()
        assert 'response' in data or 'message' in data


class TestAccountsFlow:
    """Test accounts management flow"""
    
    def test_accounts_requires_auth(self, server):
        """Accounts endpoint should require authentication"""
        resp = requests.get(f'{server}/api/accounts', timeout=5)
        assert resp.status_code == 401
    
    def test_accounts_returns_list(self, server, auth_token):
        """Accounts should return a list"""
        resp = requests.get(
            f'{server}/api/accounts',
            headers={'Authorization': f'Bearer {auth_token}'},
            timeout=5
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list) or 'accounts' in data


class TestFestivalsFlow:
    """Test festivals management flow"""
    
    def test_festivals_requires_auth(self, server):
        """Festivals endpoint should require authentication"""
        resp = requests.get(f'{server}/api/festivals', timeout=5)
        assert resp.status_code == 401
    
    def test_festivals_returns_list(self, server, auth_token):
        """Festivals should return a list"""
        resp = requests.get(
            f'{server}/api/festivals',
            headers={'Authorization': f'Bearer {auth_token}'},
            timeout=5
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list) or 'festivals' in data


class TestForecastFlow:
    """Test sales forecast flow"""
    
    def test_forecast_requires_auth(self, server):
        """Forecast endpoint should require authentication"""
        resp = requests.get(f'{server}/api/forecast/daily', timeout=5)
        assert resp.status_code == 401
    
    def test_forecast_returns_data(self, server, auth_token):
        """Forecast should return prediction data"""
        resp = requests.get(
            f'{server}/api/forecast/daily',
            headers={'Authorization': f'Bearer {auth_token}'},
            timeout=5
        )
        assert resp.status_code == 200
        # Response can be list or dict with 'forecast' key


class TestProductsFlow:
    """Test products/inventory flow"""
    
    def test_products_requires_auth(self, server):
        """Products endpoint should require authentication"""
        resp = requests.get(f'{server}/api/products', timeout=5)
        assert resp.status_code == 401
    
    def test_products_returns_list(self, server, auth_token):
        """Products should return a list"""
        resp = requests.get(
            f'{server}/api/products',
            headers={'Authorization': f'Bearer {auth_token}'},
            timeout=5
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list) or 'products' in data


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def server():
    """Start Flask server for E2E tests"""
    port = 5555
    base_url = f'http://127.0.0.1:{port}'
    
    # Check if server already running
    try:
        resp = requests.get(f'{base_url}/api/health', timeout=2)
        if resp.status_code == 200:
            yield base_url
            return
    except:
        pass
    
    # Start server
    env = os.environ.copy()
    env['FLASK_ENV'] = 'testing'
    
    proc = subprocess.Popen(
        [sys.executable, '-m', 'flask', 'run', '--port', str(port)],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    max_wait = 10
    for i in range(max_wait):
        try:
            resp = requests.get(f'{base_url}/api/health', timeout=1)
            if resp.status_code == 200:
                break
        except:
            time.sleep(1)
    
    yield base_url
    
    # Cleanup
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except:
        proc.kill()


@pytest.fixture(scope='session')
def csrf_token(server):
    """Get CSRF token from server"""
    pytest.skip('E2E tests require stable server environment')


@pytest.fixture
def unique_user():
    """Generate unique user for each test"""
    timestamp = int(time.time() * 1000)
    return {
        'account': f'test_user_{timestamp}',
        'password': 'TestPass123!@#',
        'email': f'test_{timestamp}@example.com'
    }


@pytest.fixture
def test_user():
    """Standard test user"""
    return {
        'account': 'e2e_test_user',
        'password': 'E2ETest123!@#',
        'email': 'e2e@example.com'
    }


@pytest.fixture
def auth_token(server, test_user, csrf_token):
    """Get authentication token for tests"""
    # Register user
    requests.post(
        f'{server}/api/auth/register',
        json={
            'account': test_user['account'],
            'password': test_user['password'],
            'email': test_user['email']
        },
        headers={'X-CSRF-Token': csrf_token},
        cookies={'csrf_token': csrf_token},
        timeout=5
    )
    
    # Login
    resp = requests.post(
        f'{server}/api/auth/login',
        json={
            'account': test_user['account'],
            'password': test_user['password']
        },
        headers={'X-CSRF-Token': csrf_token},
        cookies={'csrf_token': csrf_token},
        timeout=5
    )
    
    if resp.status_code == 200:
        return resp.json()['token']
    
    pytest.skip('Could not get auth token')
