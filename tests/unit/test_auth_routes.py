#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for web/routes/auth.py module."""

import sys
import pytest
from unittest.mock import MagicMock, patch


class TestGenerateToken:
    """Test generate_token function."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup mocks before each test."""
        # Clear cached modules
        for m in list(sys.modules.keys()):
            if m.startswith('acas_pro'):
                del sys.modules[m]

        # Mock acas_pro.core.security
        mock_jwt_mgr = MagicMock()
        mock_jwt_mgr.generate_token.return_value = "fake-jwt-token-123"
        mock_pv = MagicMock()
        mock_rate_limiter = MagicMock()

        mock_security = MagicMock()
        mock_security.JWTManager = mock_jwt_mgr
        mock_security.password_validator = mock_pv
        mock_security.rate_limiter = mock_rate_limiter
        sys.modules['acas_pro.core.security'] = mock_security

        # Mock acas_pro.core.config
        mock_config = MagicMock()
        mock_config_pkg = MagicMock()
        mock_config_pkg.config = mock_config
        sys.modules['acas_pro.core.config'] = mock_config_pkg

        # Mock acas_pro.services.user_service
        mock_user_svc = MagicMock()
        mock_user_svc_pkg = MagicMock()
        mock_user_svc_pkg.user_service = mock_user_svc
        sys.modules['acas_pro.services.user_service'] = mock_user_svc_pkg

        # Mock acas_pro.core.logging
        mock_logger = MagicMock()
        mock_get_logger = MagicMock(return_value=mock_logger)
        mock_logging_pkg = MagicMock()
        mock_logging_pkg.get_logger = mock_get_logger
        sys.modules['acas_pro.core.logging'] = mock_logging_pkg

        yield

        # Cleanup
        for m in list(sys.modules.keys()):
            if m.startswith('acas_pro'):
                del sys.modules[m]

    def test_generate_token(self):
        """Test generate_token returns a token."""
        from acas_pro.web.routes.auth import generate_token
        token = generate_token("user123", "testaccount")
        assert token == "fake-jwt-token-123"

    def test_generate_token_calls_jwt_manager(self):
        """Test generate_token calls JWTManager.generate_token."""
        from acas_pro.web.routes.auth import generate_token
        from acas_pro.core.security import JWTManager
        token = generate_token("user123", "testaccount")
        JWTManager.generate_token.assert_called_once_with(
            "user123", extra_claims={'account': 'testaccount'}
        )


class TestVerifyToken:
    """Test verify_token function."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup mocks before each test."""
        for m in list(sys.modules.keys()):
            if m.startswith('acas_pro'):
                del sys.modules[m]

        # Mock JWTManager
        mock_jwt_mgr = MagicMock()
        mock_jwt_mgr.verify_token.return_value = {'sub': 'user123', 'account': 'testaccount'}

        mock_security = MagicMock()
        mock_security.JWTManager = mock_jwt_mgr
        sys.modules['acas_pro.core.security'] = mock_security

        # Mock config for legacy fallback
        mock_config = MagicMock()
        mock_config.return_value.security.secret_key = "test-secret-key"
        mock_config_pkg = MagicMock()
        mock_config_pkg.config = mock_config
        sys.modules['acas_pro.core.config'] = mock_config_pkg

        # Mock jwt for legacy fallback
        mock_jwt = MagicMock()
        mock_jwt.decode.return_value = {'user_id': 'user123'}
        sys.modules['jwt'] = mock_jwt

        yield

        for m in list(sys.modules.keys()):
            if m.startswith('acas_pro'):
                del sys.modules[m]

    def test_verify_token_valid(self):
        """Test verify_token with valid token."""
        from acas_pro.web.routes.auth import verify_token
        payload = verify_token("valid-token")
        assert payload is not None
        assert payload['sub'] == 'user123'

    def test_verify_token_invalid(self):
        """Test verify_token with invalid token."""
        from acas_pro.web.routes.auth import verify_token
        from acas_pro.core.security import JWTManager
        JWTManager.verify_token.return_value = None

        # Get the mock jwt from sys.modules (set up by the fixture)
        import jwt
        # Now jwt is the MagicMock from sys.modules['jwt']
        
        # Create REAL exception classes for the except clause to catch
        class ExpiredSignatureError(Exception):
            pass
        class InvalidTokenError(Exception):
            pass
        
        jwt.ExpiredSignatureError = ExpiredSignatureError
        jwt.InvalidTokenError = InvalidTokenError
        
        # Make jwt.decode raise the correct exception TYPE (class, not instance)
        jwt.decode.side_effect = InvalidTokenError
        
        payload = verify_token("invalid-token")
        assert payload is None


class TestAuthRoutes:
    """Test auth routes using Flask test client."""

    @pytest.fixture
    def app(self):
        """Create a Flask app with auth Blueprint."""
        from flask import Flask
        app = Flask(__name__)
        from acas_pro.web.routes.auth import bp
        app.register_blueprint(bp)
        return app

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup mocks."""
        for m in list(sys.modules.keys()):
            if m.startswith('acas_pro'):
                del sys.modules[m]

        # Mock dependencies
        mock_jwt_mgr = MagicMock()
        mock_jwt_mgr.generate_token.return_value = "fake-token"

        mock_security = MagicMock()
        mock_security.JWTManager = mock_jwt_mgr
        mock_security.password_validator.validate.return_value = (True, "")
        mock_security.rate_limiter.is_allowed.return_value = True
        mock_security.rate_limiter.record_attempt = MagicMock()
        sys.modules['acas_pro.core.security'] = mock_security

        mock_user_svc = MagicMock()
        mock_user_svc.register.return_value = (True, "", MagicMock(id="user123", account="test", nickname="Test"))
        mock_user_svc.login.return_value = (True, "", MagicMock(id="user123", account="test", nickname="Test"))
        mock_user_svc_pkg = MagicMock()
        mock_user_svc_pkg.user_service = mock_user_svc
        sys.modules['acas_pro.services.user_service'] = mock_user_svc_pkg

        mock_config = MagicMock()
        mock_config_pkg = MagicMock()
        mock_config_pkg.config = mock_config
        sys.modules['acas_pro.core.config'] = mock_config_pkg

        mock_logging = MagicMock()
        mock_logging_pkg = MagicMock()
        mock_logging_pkg.get_logger = MagicMock(return_value=mock_logging)
        sys.modules['acas_pro.core.logging'] = mock_logging_pkg

        yield

        for m in list(sys.modules.keys()):
            if m.startswith('acas_pro'):
                del sys.modules[m]

    def test_register_success(self, app):
        """Test successful registration."""
        client = app.test_client()
        response = client.post('/api/auth/register', json={
            'account': 'testuser',
            'password': 'StrongPass123!'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'token' in data

    def test_register_missing_fields(self, app):
        """Test registration with missing fields."""
        client = app.test_client()
        response = client.post('/api/auth/register', json={
            'account': 'testuser'
            # missing password
        })
        assert response.status_code == 400

    def test_login_success(self, app):
        """Test successful login."""
        client = app.test_client()
        response = client.post('/api/auth/login', json={
            'account': 'testuser',
            'password': 'StrongPass123!'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'token' in data