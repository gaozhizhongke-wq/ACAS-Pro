#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 2: Core Module Tests - Coverage Sprint

Target: Improve coverage for core modules
"""

import pytest
import os
import sys
import jwt
import bcrypt
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from acas_pro.core.config import AppConfig, DatabaseConfig, SecurityConfig, LLMConfig
from acas_pro.core.security_headers import SecurityHeaders, InputValidator
from acas_pro.core.logging import setup_logging, get_logger


class TestSecurityHeaders:
    """Test security headers middleware"""
    
    @pytest.fixture
    def mock_app(self):
        app = Mock()
        app.after_request = Mock(return_value=lambda f: f)
        return app
    
    def test_security_headers_initialization(self, mock_app):
        """Test SecurityHeaders can be initialized"""
        security = SecurityHeaders(mock_app)
        assert security is not None
    
    def test_input_validator_sanitize_sql(self):
        """Test SQL sanitization"""
        # Test normal string
        result = InputValidator.sanitize_sql("hello world")
        assert result == "hello world"
        
        # Test SQL injection detection
        with pytest.raises(ValueError):
            InputValidator.sanitize_sql("SELECT * FROM users")
        
        with pytest.raises(ValueError):
            InputValidator.sanitize_sql("'; DROP TABLE users; --")
    
    def test_input_validator_sanitize_html(self):
        """Test HTML sanitization"""
        # Test normal string
        result = InputValidator.sanitize_html("hello world")
        assert result == "hello world"
        
        # Test XSS detection
        with pytest.raises(ValueError):
            InputValidator.sanitize_html("<script>alert('xss')</script>")
        
        with pytest.raises(ValueError):
            InputValidator.sanitize_html("javascript:alert('xss')")
    
    def test_input_validator_validate_email(self):
        """Test email validation"""
        # Valid email
        assert InputValidator.validate_email("user@example.com") is True
        assert InputValidator.validate_email("test.user@domain.co.uk") is True
        
        # Invalid email
        assert InputValidator.validate_email("invalid") is False
        assert InputValidator.validate_email("@example.com") is False
        assert InputValidator.validate_email("user@") is False
    
    def test_input_validator_validate_phone(self):
        """Test phone validation"""
        # Valid Chinese phone
        assert InputValidator.validate_phone("13800138000") is True
        assert InputValidator.validate_phone("15912345678") is True
        
        # Invalid phone
        assert InputValidator.validate_phone("12345678901") is False
        assert InputValidator.validate_phone("1380013800") is False
        assert InputValidator.validate_phone("abcdefg") is False


class TestConfig:
    """Test configuration management"""
    
    def test_config_default_values(self):
        """Test config has default values"""
        config = AppConfig()
        assert config is not None
    
    def test_database_config(self):
        """Test database configuration"""
        db_config = DatabaseConfig(
            host="localhost",
            port=5432,
            name="acas",
            user="admin",
            password="secret"
        )
        assert db_config.host == "localhost"
        assert db_config.port == 5432
    
    def test_security_config(self):
        """Test security configuration"""
        sec_config = SecurityConfig(
            secret_key="test-secret-key-32-chars-long!",
            jwt_algorithm="HS256",
            jwt_expiry_hours=24
        )
        assert sec_config.jwt_algorithm == "HS256"
        assert sec_config.jwt_expiry_hours == 24
    
    def test_llm_config(self):
        """Test LLM configuration"""
        llm_config = LLMConfig(
            provider="deepseek",
            api_key="test-key",
            model="deepseek-chat",
            enabled=True
        )
        assert llm_config.provider == "deepseek"
        assert llm_config.enabled is True


class TestLogging:
    """Test logging system"""
    
    def test_setup_logging(self):
        """Test logging setup"""
        # Should not raise
        setup_logging()
    
    def test_get_logger(self):
        """Test logger retrieval"""
        logger = get_logger("test_module")
        assert logger is not None
        # Logger name may include parent prefix
        assert "test_module" in logger.name


class TestJWTUtils:
    """Test JWT utilities"""
    
    @pytest.fixture
    def secret_key(self):
        return "test-secret-key-32-chars-long!"
    
    def test_jwt_encode_decode(self, secret_key):
        """Test JWT encoding and decoding"""
        payload = {
            "user_id": "123",
            "username": "testuser",
            "exp": datetime.now(timezone.utc) + timedelta(hours=24)
        }
        
        # Encode
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        assert isinstance(token, str)
        
        # Decode
        decoded = jwt.decode(token, secret_key, algorithms=["HS256"])
        assert decoded["user_id"] == "123"
        assert decoded["username"] == "testuser"
    
    def test_jwt_expired_token(self, secret_key):
        """Test expired token handling"""
        payload = {
            "user_id": "123",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1)
        }
        
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt.decode(token, secret_key, algorithms=["HS256"])
    
    def test_jwt_invalid_signature(self, secret_key):
        """Test invalid signature handling"""
        payload = {"user_id": "123"}
        token = jwt.encode(payload, secret_key, algorithm="HS256")
        
        with pytest.raises(jwt.InvalidSignatureError):
            jwt.decode(token, "wrong-secret", algorithms=["HS256"])


class TestPasswordHashing:
    """Test password hashing utilities"""
    
    def test_bcrypt_hash_verify(self):
        """Test bcrypt password hashing"""
        password = "TestPassword123!"
        
        # Hash
        hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
        assert isinstance(hashed, bytes)
        
        # Verify correct password
        assert bcrypt.checkpw(password.encode(), hashed) is True
        
        # Verify wrong password
        assert bcrypt.checkpw("WrongPassword".encode(), hashed) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
