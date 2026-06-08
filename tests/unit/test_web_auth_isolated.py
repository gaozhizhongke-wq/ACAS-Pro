# -*- coding: utf-8 -*-
"""Isolated tests for web/__init__.py auth middleware."""
import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from flask import Flask


class TestAuthMiddlewareIsolated:
    """Test auth middleware with full module isolation."""

    def _create_app_with_auth(self, monkeypatch, secret_key='test-secret-32-chars-long!!!', env='development'):
        """Helper: create app with fresh mocks and auth middleware."""
        # Clear all cached modules
        for mod in list(sys.modules.keys()):
            if 'acas_pro.web' in mod or 'acas_pro.core' in mod:
                sys.modules.pop(mod, None)
        
        # Set env
        os.environ['SECRET_KEY'] = secret_key
        os.environ['ENVIRONMENT'] = env
        
        # Mock config before any import
        mock_config = MagicMock()
        mock_config.validate.return_value = (True, [])
        mock_config.security.secret_key = secret_key
        mock_config.environment = env
        mock_config.database.type = 'sqlite'
        mock_config.llm.enabled = False
        mock_config.version = '1.0.0'
        mock_config.data_dir = 'data'
        
        with patch.dict('sys.modules', {'acas_pro.core.config': MagicMock(config=mock_config)}):
            from acas_pro.web import create_app
            return create_app({'TESTING': True, 'SECRET_KEY': secret_key})

    def test_public_route_no_auth(self, monkeypatch):
        """Test public route without auth."""
        app = self._create_app_with_auth(monkeypatch)
        
        with app.test_client() as client:
            response = client.get('/api/auth/register')
            assert response.status_code != 401

    # Remove skip: auth middleware now registered in create_app
    def test_protected_route_no_auth(self, monkeypatch):
        """Test protected route without auth returns 401."""
        app = self._create_app_with_auth(monkeypatch)
        
        # Add a protected test route (not in PUBLIC_ROUTES or PUBLIC_PREFIXES)
        @app.route('/api/protected')
        def protected_route():
            from flask import jsonify
            return jsonify({'message': 'protected'}), 200
        
        with app.test_client() as client:
            response = client.get('/api/protected')
            # Should return 401 (Unauthorized) because route is protected
            assert response.status_code == 401

    # Remove skip: auth middleware now registered in create_app
    def test_protected_route_with_invalid_token(self, monkeypatch):
        """Test protected route with invalid token returns 401."""
        app = self._create_app_with_auth(monkeypatch)
        
        # Add a protected test route (not in PUBLIC_ROUTES or PUBLIC_PREFIXES)
        @app.route('/api/protected')
        def protected_route():
            from flask import jsonify
            return jsonify({'message': 'protected'}), 200
        
        with app.test_client() as client:
            response = client.get('/api/protected', headers={'Authorization': 'Bearer invalid_token'})
            # Should return 401 (Unauthorized) because token is invalid
            assert response.status_code == 401

    def test_read_only_public_path(self, monkeypatch):
        """Test read-only public path without auth."""
        app = self._create_app_with_auth(monkeypatch)
        
        with app.test_client() as client:
            response = client.get('/api/stats')
            assert response.status_code != 401


class TestBlueprintsIsolated:
    """Test blueprint registration."""

    def test_blueprints_registered(self, monkeypatch):
        """Test all blueprints are registered."""
        # Clear modules
        for mod in list(sys.modules.keys()):
            if 'acas_pro.web' in mod:
                sys.modules.pop(mod, None)
        
        os.environ['SECRET_KEY'] = 'test-secret-32-chars-long!!!'
        os.environ['ENVIRONMENT'] = 'development'
        
        mock_config = MagicMock()
        mock_config.validate.return_value = (True, [])
        mock_config.security.secret_key = 'test-secret-32-chars-long!!!'
        mock_config.environment = 'development'
        mock_config.database.type = 'sqlite'
        mock_config.llm.enabled = False
        mock_config.version = '1.0.0'
        mock_config.data_dir = 'data'
        
        with patch.dict('sys.modules', {'acas_pro.core.config': MagicMock(config=mock_config)}):
            from acas_pro.web import create_app
            app = create_app({'TESTING': True})
            
            blueprint_names = [bp.name for bp in app.blueprints.values()]
            assert 'auth' in blueprint_names
            assert 'llm' in blueprint_names
            assert 'dashboard' in blueprint_names
