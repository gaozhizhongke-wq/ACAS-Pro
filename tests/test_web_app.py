#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ACAS Pro Unit Tests - Unit Tests with Flask Test Client

Uses Flask test client instead of running a real server.
"""

import pytest
import os
import time

pytestmark = [
    pytest.mark.skipif(os.environ.get('SKIP_UNIT') == '1', reason='Skip unit tests'),
]


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture(scope='session')
def app():
    """Create Flask app for testing"""
    os.environ['ENVIRONMENT'] = 'testing'
    os.environ['SKIP_COVERAGE'] = '1'

    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from web_app import app as flask_app
    return flask_app


@pytest.fixture
def client(app):
    """Flask test client"""
    return app.test_client()


@pytest.fixture
def unique_user():
    """Generate unique user for each test"""
    timestamp = int(time.time() * 1000)
    return {
        'account': f'u_{timestamp}',
        'password': 'TestPass123!@#',
        'email': f'test_{timestamp}@example.com'
    }


@pytest.fixture
def auth_token(client, unique_user):
    """Get authentication token for tests"""
    # Register user
    client.post(
        '/api/auth/register',
        json={
            'account': unique_user['account'],
            'password': unique_user['password'],
            'email': unique_user['email']
        }
    )

    # Login
    resp = client.post(
        '/api/auth/login',
        json={
            'account': unique_user['account'],
            'password': unique_user['password']
        }
    )

    if resp.status_code == 200:
        return resp.get_json()['token']
    pytest.skip('Could not get auth token')


# ── Test Classes ──────────────────────────────────────────────────────────

class TestHealthEndpoint:
    """Test health check endpoint"""

    def test_health_returns_200(self, client):
        """GET /api/health should return 200"""
        resp = client.get('/api/health')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['status'] == 'ok'

    def test_health_has_version(self, client):
        """Health response should include version"""
        resp = client.get('/api/health')
        data = resp.get_json()
        assert 'version' in data


class TestAuthFlow:
    """Test complete authentication flow"""

    def test_register_new_user(self, client, unique_user):
        """Register a new user should return 201 or 409"""
        resp = client.post(
            '/api/auth/register',
            json={
                'account': unique_user['account'],
                'password': unique_user['password'],
                'email': unique_user['email']
            }
        )
        assert resp.status_code in (200, 201, 409)

    def test_register_missing_fields(self, client):
        """Register with missing fields should return 400"""
        resp = client.post('/api/auth/register', json={})
        assert resp.status_code == 400

    def test_register_weak_password(self, client, unique_user):
        """Register with weak password should return 400"""
        resp = client.post(
            '/api/auth/register',
            json={
                'account': unique_user['account'],
                'password': '123',
                'email': unique_user['email']
            }
        )
        assert resp.status_code == 400

    def test_login_returns_token(self, client, unique_user):
        """Login should return JWT token"""
        client.post(
            '/api/auth/register',
            json={
                'account': unique_user['account'],
                'password': unique_user['password'],
                'email': unique_user['email']
            }
        )

        resp = client.post(
            '/api/auth/login',
            json={
                'account': unique_user['account'],
                'password': unique_user['password']
            }
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'token' in data
        assert len(data['token']) > 50

    def test_login_wrong_password(self, client, unique_user):
        """Login with wrong password should return 401"""
        client.post(
            '/api/auth/register',
            json={
                'account': unique_user['account'],
                'password': unique_user['password'],
                'email': unique_user['email']
            }
        )

        resp = client.post(
            '/api/auth/login',
            json={
                'account': unique_user['account'],
                'password': 'WrongPass123!'
            }
        )
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client):
        """Login with nonexistent user should return 401"""
        resp = client.post(
            '/api/auth/login',
            json={
                'account': 'nonexistent_xyz_user',
                'password': 'SomePass123!'
            }
        )
        assert resp.status_code == 401

    def test_protected_route_requires_token(self, client):
        """Protected routes should reject requests without token"""
        resp = client.get('/api/auth/me')
        assert resp.status_code == 401

    def test_protected_route_accepts_valid_token(self, client, unique_user):
        """Protected routes should accept valid JWT token"""
        client.post(
            '/api/auth/register',
            json={
                'account': unique_user['account'],
                'password': unique_user['password'],
                'email': unique_user['email']
            }
        )

        login_resp = client.post(
            '/api/auth/login',
            json={
                'account': unique_user['account'],
                'password': unique_user['password']
            }
        )
        token = login_resp.get_json()['token']

        resp = client.get(
            '/api/auth/me',
            headers={'Authorization': f'Bearer {token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'account' in data


class TestDashboardFlow:
    """Test dashboard data flow"""

    def test_dashboard_stats_requires_auth(self, client):
        """Dashboard stats should require authentication"""
        resp = client.get('/api/dashboard/stats')
        assert resp.status_code == 401

    def test_dashboard_stats_returns_data(self, client, auth_token):
        """Dashboard stats should return data structure"""
        resp = client.get(
            '/api/dashboard/stats',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'revenue' in data
        assert 'active_orders' in data
        assert 'inventory' in data


class TestLLMFlow:
    """Test LLM chat flow"""

    def test_llm_config_requires_auth(self, client):
        """LLM config endpoint should require authentication"""
        resp = client.post(
            '/api/llm/config',
            json={'provider': 'deepseek'}
        )
        assert resp.status_code == 401

    def test_llm_chat_requires_auth(self, client):
        """LLM chat endpoint should require authentication"""
        resp = client.post(
            '/api/llm/chat',
            json={'message': 'Hello'}
        )
        assert resp.status_code == 401

    def test_llm_chat_with_auth(self, client, auth_token):
        """LLM chat with valid token should return 200"""
        resp = client.post(
            '/api/llm/chat',
            headers={'Authorization': f'Bearer {auth_token}'},
            json={
                'message': 'What is 2+2?',
                'conversation_id': 'test-conv-001'
            }
        )
        assert resp.status_code == 200


class TestAccountsFlow:
    """Test accounts management flow"""

    def test_accounts_requires_auth(self, client):
        """Accounts endpoint should require authentication"""
        resp = client.get('/api/accounts')
        assert resp.status_code == 401

    def test_accounts_returns_list(self, client, auth_token):
        """Accounts should return 200 with valid token"""
        resp = client.get(
            '/api/accounts',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        assert resp.status_code == 200


class TestFestivalsFlow:
    """Test festivals management flow"""

    def test_festivals_requires_auth(self, client):
        """Festivals endpoint should require authentication"""
        resp = client.get('/api/festivals')
        assert resp.status_code == 401

    def test_festivals_returns_list(self, client, auth_token):
        """Festivals should return 200 with valid token"""
        resp = client.get(
            '/api/festivals',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        assert resp.status_code == 200


class TestForecastFlow:
    """Test sales forecast flow"""

    def test_forecast_requires_auth(self, client):
        """Forecast endpoint should require authentication"""
        resp = client.get('/api/forecast/daily')
        assert resp.status_code == 401

    def test_forecast_returns_data(self, client, auth_token):
        """Forecast should return 200 with valid token"""
        resp = client.get(
            '/api/forecast/daily',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        assert resp.status_code == 200


class TestProductsFlow:
    """Test products/inventory flow"""

    def test_products_requires_auth(self, client):
        """Products endpoint should require authentication"""
        resp = client.get('/api/products')
        assert resp.status_code == 401

    def test_products_returns_list(self, client, auth_token):
        """Products should return 200 with valid token"""
        resp = client.get(
            '/api/products',
            headers={'Authorization': f'Bearer {auth_token}'}
        )
        assert resp.status_code == 200
