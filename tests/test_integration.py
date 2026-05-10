"""Integration tests for ACAS Pro API

Tests the full API stack including authentication, database, and endpoints.
"""
import pytest
import sys
import os
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Set test environment before importing app
os.environ['ACAS_ENV'] = 'testing'
os.environ['SECRET_KEY'] = 'test-secret-key-for-integration-tests-only'
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from web_app import app


@pytest.fixture
def client():
    """Create a test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def auth_headers(client):
    """Get authentication headers for testing"""
    # Register a test user
    response = client.post('/api/auth/register', 
                          json={'account': 'testuser', 'password': 'TestP@ss123'})
    
    # Login to get token
    response = client.post('/api/auth/login',
                          json={'account': 'testuser', 'password': 'TestP@ss123'})
    
    data = response.get_json()
    token = data.get('token')
    
    return {'Authorization': f'Bearer {token}'}


class TestHealthEndpoint:
    """Test health check endpoint"""
    
    def test_health_check(self, client):
        """Test health check returns correct structure"""
        response = client.get('/api/health')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'status' in data
        assert 'timestamp' in data
        assert 'version' in data
        assert 'checks' in data
        assert isinstance(data['checks'], list)


class TestAuthEndpoints:
    """Test authentication endpoints"""
    
    def test_register_success(self, client):
        """Test successful user registration"""
        response = client.post('/api/auth/register',
                              json={'account': 'newuser', 'password': 'StrongP@ss123'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'token' in data
        assert 'user' in data
    
    def test_register_weak_password(self, client):
        """Test registration with weak password fails"""
        response = client.post('/api/auth/register',
                              json={'account': 'weakuser', 'password': '123'})
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_register_duplicate_account(self, client):
        """Test registration with duplicate account fails"""
        # First registration
        client.post('/api/auth/register',
                   json={'account': 'dupuser', 'password': 'StrongP@ss123'})
        
        # Duplicate registration
        response = client.post('/api/auth/register',
                              json={'account': 'dupuser', 'password': 'StrongP@ss123'})
        
        assert response.status_code == 409
    
    def test_login_success(self, client):
        """Test successful login"""
        # Register first
        client.post('/api/auth/register',
                   json={'account': 'loginuser', 'password': 'StrongP@ss123'})
        
        # Login
        response = client.post('/api/auth/login',
                              json={'account': 'loginuser', 'password': 'StrongP@ss123'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'token' in data
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post('/api/auth/login',
                              json={'account': 'nonexistent', 'password': 'WrongP@ss123'})
        
        assert response.status_code == 401
    
    def test_me_endpoint(self, client, auth_headers):
        """Test /api/auth/me endpoint"""
        response = client.get('/api/auth/me', headers=auth_headers)
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'user_id' in data
        assert 'account' in data


class TestLLMEndpoints:
    """Test LLM endpoints"""
    
    def test_llm_config_requires_auth(self, client):
        """Test LLM config requires authentication"""
        response = client.post('/api/llm/config', json={'provider': 'openai'})
        assert response.status_code == 401
    
    def test_llm_chat_requires_auth(self, client):
        """Test LLM chat requires authentication"""
        response = client.post('/api/llm/chat', json={'messages': []})
        assert response.status_code == 401


class TestSecurityHeaders:
    """Test security headers are present"""
    
    def test_security_headers_present(self, client):
        """Test that security headers are in responses"""
        response = client.get('/api/health')
        
        assert 'X-Content-Type-Options' in response.headers
        assert 'X-Frame-Options' in response.headers
        assert 'Content-Security-Policy' in response.headers


class TestRequestTracking:
    """Test request ID tracking"""
    
    def test_request_id_header(self, client):
        """Test that responses include X-Request-ID header"""
        response = client.get('/api/health')
        
        assert 'X-Request-ID' in response.headers
        assert len(response.headers['X-Request-ID']) > 0
    
    def test_custom_request_id(self, client):
        """Test that custom request ID is preserved"""
        custom_id = 'custom-request-id-123'
        response = client.get('/api/health', headers={'X-Request-ID': custom_id})
        
        assert response.headers['X-Request-ID'] == custom_id


class TestErrorHandling:
    """Test error handling"""
    
    def test_404_error(self, client):
        """Test 404 error response"""
        response = client.get('/api/nonexistent')
        
        assert response.status_code == 404
        data = response.get_json()
        assert 'error' in data
        assert 'request_id' in data
    
    def test_400_error(self, client):
        """Test 400 error for invalid JSON"""
        response = client.post('/api/auth/login',
                              data='not json',
                              content_type='application/json')
        
        assert response.status_code == 400


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
