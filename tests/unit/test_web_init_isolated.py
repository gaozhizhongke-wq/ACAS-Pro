# -*- coding: utf-8 -*-
"""Isolated tests for web/__init__.py using module reload."""
import pytest
import os
import sys
from unittest.mock import MagicMock, patch
from flask import Flask


class TestCreateAppIsolated:
    """Test create_app with full module isolation."""

    def _reload_and_test(self, test_config, env_vars=None, mock_config=None):
        """Helper: reload web module with fresh mocks."""
        # Clear cached modules
        modules_to_clear = [
            'acas_pro.web', 'acas_pro.web.routes', 
            'acas_pro.web.routes.auth', 'acas_pro.web.routes.llm', 'acas_pro.web.routes.dashboard'
        ]
        for mod in modules_to_clear:
            sys.modules.pop(mod, None)
        
        # Set env vars
        if env_vars:
            for key, val in env_vars.items():
                if val is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = val
        
        # Mock config before import
        with patch('acas_pro.web.config', mock_config or MagicMock()):
            from acas_pro.web import create_app
            return create_app(test_config)

    def test_create_app_with_test_config(self):
        """Test create_app with test config."""
        mock_config = MagicMock()
        mock_config.validate.return_value = (True, [])
        mock_config.security.secret_key = 'test-secret-key-32-chars-long!!!'
        mock_config.environment = 'development'
        mock_config.database.type = 'sqlite'
        mock_config.llm.enabled = False
        
        app = self._reload_and_test(
            {'TESTING': True, 'SECRET_KEY': 'test'},
            env_vars={'SECRET_KEY': 'test-secret-key-32-chars-long!!!'},
            mock_config=mock_config
        )
        assert isinstance(app, Flask)
        assert app.config['TESTING'] is True

    def test_create_app_skips_validation_in_testing(self):
        """Test validation skipped in testing mode."""
        mock_config = MagicMock()
        mock_config.validate.return_value = (False, ['LLM API key required'])
        
        app = self._reload_and_test(
            {'TESTING': True},
            env_vars={'SECRET_KEY': 'test-secret-key-32-chars-long!!!'},
            mock_config=mock_config
        )
        assert app.config['TESTING'] is True

    def test_create_app_validates_in_non_testing(self):
        """Test validation runs in non-testing mode."""
        mock_config = MagicMock()
        mock_config.validate.return_value = (False, ['LLM API key required'])
        mock_config.security.secret_key = 'test-secret-key-32-chars-long!!!'
        mock_config.environment = 'development'
        
        with pytest.raises(ValueError, match='Invalid configuration'):
            self._reload_and_test(
                {},
                env_vars={'SECRET_KEY': 'test-secret-key-32-chars-long!!!'},
                mock_config=mock_config
            )


class TestConfigureAppIsolated:
    """Test _configure_app with isolation."""

    def test_secret_key_from_env(self):
        """Test SECRET_KEY from environment variable."""
        mock_config = MagicMock()
        mock_config.security.secret_key = 'config-secret'
        mock_config.environment = 'development'
        mock_config.database.type = 'sqlite'
        mock_config.llm.enabled = False
        
        app = TestCreateAppIsolated()._reload_and_test(
            {'TESTING': True},
            env_vars={'SECRET_KEY': 'env-secret-key-32-chars-long!!!'},
            mock_config=mock_config
        )
        assert app.secret_key == 'env-secret-key-32-chars-long!!!'

    def test_weak_secret_key_in_dev(self):
        """Test weak secret key generates ephemeral key."""
        mock_config = MagicMock()
        mock_config.security.secret_key = 'acas-pro-secret-key-change-me'
        mock_config.environment = 'development'
        mock_config.database.type = 'sqlite'
        mock_config.llm.enabled = False
        
        app = TestCreateAppIsolated()._reload_and_test(
            {'TESTING': True},
            env_vars={'ENVIRONMENT': 'development'},
            mock_config=mock_config
        )
        assert app.secret_key is not None
        assert len(app.secret_key) > 20

    def test_production_missing_secret_key_raises(self):
        """Test production with missing SECRET_KEY raises ValueError."""
        mock_config = MagicMock()
        mock_config.security.secret_key = 'acas-pro-secret-key-change-me'
        mock_config.environment = 'production'
        mock_config.database.type = 'sqlite'
        mock_config.llm.enabled = False
        
        with pytest.raises(ValueError, match='SECRET_KEY must be set in production'):
            TestCreateAppIsolated()._reload_and_test(
                {'TESTING': True},
                env_vars={'ENVIRONMENT': 'production', 'SECRET_KEY': ''},
                mock_config=mock_config
            )


class TestBlueprintsIsolated:
    """Test blueprint registration."""

    def test_blueprints_registered(self):
        """Test all blueprints are registered."""
        mock_config = MagicMock()
        mock_config.validate.return_value = (True, [])
        mock_config.security.secret_key = 'test-secret-key-32-chars-long!!!'
        mock_config.environment = 'development'
        mock_config.database.type = 'sqlite'
        mock_config.llm.enabled = False
        
        app = TestCreateAppIsolated()._reload_and_test(
            {'TESTING': True},
            env_vars={'SECRET_KEY': 'test-secret-key-32-chars-long!!!'},
            mock_config=mock_config
        )
        
        blueprint_names = [bp.name for bp in app.blueprints.values()]
        assert 'auth' in blueprint_names
        assert 'llm' in blueprint_names
        assert 'dashboard' in blueprint_names
