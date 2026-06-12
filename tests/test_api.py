#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - API Endpoint Tests
"""

import pytest

from acas_pro.core.config import get_config
from acas_pro.core.security import jwt_manager

config = get_config()


class TestHealthEndpoints:
    """Health check endpoint tests"""
    
    def test_health_endpoint(self):
        """Test health check returns valid response"""
        assert config is not None
        assert config.version is not None


class TestAuthEndpoints:
    """Authentication endpoint tests"""
    
    def test_login_endpoint(self):
        """Test login endpoint"""
        # DIAG
        import acas_pro.core.security as _sec
        from unittest.mock import MagicMock as _MM
        _gc = _sec.__dict__.get('get_config')
        print(f'[TEST_START] sec.get_config type={type(_gc).__name__}, is_Mock={isinstance(_gc, _MM)}')
        _cfg_result = _sec._cfg()
        print(f'[TEST_START] _cfg().jwt_alg={_cfg_result.security.jwt_algorithm!r}, is_Mock={isinstance(_cfg_result.security.jwt_algorithm, _MM)}')
        token = jwt_manager.generate_token("test_user")
        assert token is not None
        assert isinstance(token, str)
    
    def test_token_verification(self):
        """Test token verification"""
        token = jwt_manager.generate_token("test_user")
        decoded = jwt_manager.verify_token(token)
        assert decoded is not None
        assert decoded["sub"] == "test_user"
    
    def test_invalid_token(self):
        """Test invalid token rejection"""
        decoded = jwt_manager.verify_token("invalid.token.here")
        assert decoded is None


class TestConfigValidation:
    """Configuration validation tests"""
    
    def test_config_loads_defaults(self):
        """Test config loads with defaults"""
        assert config.name is not None
        assert config.version is not None
    
    def test_config_security_settings(self):
        """Test security configuration"""
        assert config.security is not None
        assert hasattr(config.security, 'secret_key')
    
    def test_config_database_settings(self):
        """Test database configuration"""
        assert config.database is not None
        assert hasattr(config.database, 'type')
    
    def test_config_ml_settings(self):
        """Test ML configuration"""
        assert config.ml is not None


class TestSecurityEndpoints:
    """Security endpoint tests"""
    
    def test_encryption_roundtrip(self):
        """Test encryption and decryption"""
        from acas_pro.core.security import crypto_manager
        plaintext = "sensitive_data_123"
        encrypted = crypto_manager.encrypt(plaintext)
        decrypted = crypto_manager.decrypt(encrypted)
        assert decrypted == plaintext


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
