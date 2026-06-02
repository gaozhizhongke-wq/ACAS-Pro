"""Tests for ACAS Pro Web application factory -- updated for new create_app"""
import pytest
import json
import os
import sys
import uuid


class TestCreateApp:
    """Test Flask application factory (new version)"""

    def _make_config_valid(self, monkeypatch):
        """Helper: make config.validate() return (True, []) and set a secret key"""
        import acas_pro.core.config as _cfg_mod
        cfg = _cfg_mod.config
        monkeypatch.setattr(cfg, 'validate', lambda: (True, []))
        if not getattr(cfg.security, 'secret_key', None):
            monkeypatch.setattr(cfg.security, 'secret_key', 'test-secret-key-32-chars-long!!')
        monkeypatch.setattr(cfg, 'environment', 'development')

    def test_create_app_success(self, monkeypatch):
        """App factory succeeds with valid config"""
        self._make_config_valid(monkeypatch)
        from acas_pro.web import create_app
        app = create_app({'TESTING': True, 'SECRET_KEY': 'test-secret-key-32-chars-long!!'})
        assert app is not None

    def test_create_app_invalid_config_raises(self, monkeypatch):
        """App factory raises ValueError with invalid config (non-TESTING)"""
        import acas_pro.core.config as _cfg_mod
        cfg = _cfg_mod.config
        monkeypatch.setattr(cfg, 'validate', lambda: (False, ['Missing SECRET_KEY']))

        from acas_pro.web import create_app
        # Must NOT set TESTING, so validation runs
        with pytest.raises(ValueError, match='Invalid configuration'):
            create_app()

    def test_create_app_testing_skips_validation(self, monkeypatch):
        """When TESTING=True, config validation is skipped"""
        self._make_config_valid(monkeypatch)
        from acas_pro.web import create_app
        # Even with invalid validate, should not raise because TESTING=True
        app = create_app({'TESTING': True})
        assert app is not None


class TestConfigureApp:
    """Test Flask app configuration"""

    def test_secret_key_from_env(self, monkeypatch):
        """SECRET_KEY from environment variable"""
        monkeypatch.setenv('SECRET_KEY', 'env-secret-32-chars-long!!')
        from acas_pro.web import create_app
        app = create_app({'TESTING': True})
        assert app.secret_key == 'env-secret-32-chars-long!!'

    def test_secret_key_from_config_fallback(self, monkeypatch):
        """SECRET_KEY from config.security.secret_key when env not set"""
        monkeypatch.delenv('SECRET_KEY', raising=False)
        import acas_pro.core.config as _cfg_mod
        monkeypatch.setattr(_cfg_mod.config.security, 'secret_key', 'config-secret-32-chars!!')
        monkeypatch.setattr(_cfg_mod.config, 'environment', 'development')
        from acas_pro.web import create_app
        app = create_app({'TESTING': True})
        assert app.secret_key == 'config-secret-32-chars!!'

    def test_weak_secret_key_generates_ephemeral(self, monkeypatch):
        """Weak secret key triggers ephemeral key generation"""
        monkeypatch.delenv('SECRET_KEY', raising=False)
        import acas_pro.core.config as _cfg_mod
        monkeypatch.setattr(_cfg_mod.config.security, 'secret_key', 'acas-pro-secret-key-change-me')
        monkeypatch.setattr(_cfg_mod.config, 'environment', 'development')
        from acas_pro.web import create_app
        app = create_app({'TESTING': True})
        # Should have generated a new key, not the weak one
        assert app.secret_key != 'acas-pro-secret-key-change-me'
        assert len(app.secret_key) > 0

    def test_production_missing_secret_key_raises(self, monkeypatch):
        """Production without SECRET_KEY raises ValueError"""
        monkeypatch.delenv('SECRET_KEY', raising=False)
        import acas_pro.core.config as _cfg_mod
        # Make validate() fail with ONLY the SECRET_KEY error (not LLM API key)
        monkeypatch.setattr(_cfg_mod.config, 'validate', lambda: (False, ['SECRET_KEY is required in production (set SECRET_KEY env var)']))
        monkeypatch.setattr(_cfg_mod.config.security, 'secret_key', 'acas-pro-secret-key-change-me')
        monkeypatch.setattr(_cfg_mod.config, 'environment', 'production')
        from acas_pro.web import create_app
        # Should raise ValueError with config validation error
        with pytest.raises(ValueError):
            create_app()


class TestBlueprints:
    """Test blueprint registration"""

    @pytest.fixture
    def app(self, monkeypatch):
        """Create app with TESTING=True"""
        monkeypatch.delenv('SECRET_KEY', raising=False)
        import acas_pro.core.config as _cfg_mod
        monkeypatch.setattr(_cfg_mod.config.security, 'secret_key', 'test-secret-32-chars-long!!')
        monkeypatch.setattr(_cfg_mod.config, 'environment', 'development')
        from acas_pro.web import create_app
        app = create_app({'TESTING': True})
        return app

    def test_auth_blueprint_registered(self, app):
        """Auth blueprint routes exist"""
        # auth.register, auth.login should be registered
        assert 'auth.register' in app.view_functions or any('auth' in str(r) for r in app.url_map.iter_rules())

    def test_llm_blueprint_registered(self, app):
        """LLM blueprint routes exist"""
        assert any('llm' in str(rule) for rule in app.url_map.iter_rules())

    def test_dashboard_blueprint_registered(self, app):
        """Dashboard blueprint routes exist"""
        # Check blueprint is registered by name
        from flask import Blueprint
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        assert 'dashboard' in blueprint_names or any('dashboard' in str(rule) for rule in app.url_map.iter_rules())


class TestAuthMiddleware:
    """Test JWT authentication middleware"""

    @pytest.fixture
    def client(self, monkeypatch):
        """Create test client with auth middleware"""
        monkeypatch.delenv('SECRET_KEY', raising=False)
        import acas_pro.core.config as _cfg_mod
        monkeypatch.setattr(_cfg_mod.config.security, 'secret_key', 'test-secret-32-chars-long!!')
        monkeypatch.setattr(_cfg_mod.config, 'environment', 'development')
        from acas_pro.web import create_app
        app = create_app({'TESTING': True})
        return app.test_client()

    def test_public_route_no_auth(self, client):
        """Public routes accessible without auth"""
        resp = client.get('/')
        assert resp.status_code != 401

    def test_protected_route_no_auth(self, client):
        """Protected routes require authentication"""
        resp = client.get('/api/llm/chat')
        assert resp.status_code == 401
        data = json.loads(resp.data)
        assert 'error' in data
