"""Authentication tests for ACAS Pro"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from acas_pro.core.security import (
    RateLimiter,
    password_validator as pv,
    jwt_manager,
)
from acas_pro.core.config import get_config

config = get_config()


class TestPasswordValidator:
    """Test password validation rules"""
    
    def test_valid_password(self):
        """Test a valid strong password"""
        is_valid, error = pv.validate("StrongP@ss123")
        assert is_valid is True
        assert error == ""
    
    def test_password_too_short(self):
        """Test password minimum length"""
        is_valid, error = pv.validate("Short1!")
        assert is_valid is False
        assert "8 characters" in error
    
    def test_password_no_uppercase(self):
        """Test password requires uppercase"""
        is_valid, error = pv.validate("lowercase123!")
        assert is_valid is False
        assert "uppercase" in error
    
    def test_password_no_lowercase(self):
        """Test password requires lowercase"""
        is_valid, error = pv.validate("UPPERCASE123!")
        assert is_valid is False
        assert "lowercase" in error
    
    def test_password_no_digit(self):
        """Test password requires digit"""
        is_valid, error = pv.validate("NoDigitsHere!")
        assert is_valid is False
        assert "digit" in error
    
    def test_password_no_special(self):
        """Test password requires special character"""
        is_valid, error = pv.validate("NoSpecial123")
        assert is_valid is False
        assert "special" in error
    
    def test_password_common(self):
        """Test password against common passwords"""
        is_valid, error = pv.validate("Password123!")
        assert is_valid is False
        assert "common" in error.lower()


class TestJWTManager:
    """Test JWT token management"""
    
    def test_create_access_token(self):
        """Test creating access token"""
        token = jwt_manager.generate_token("123")
        assert token is not None
        assert isinstance(token, str)
    
    def test_verify_access_token(self):
        """Test verifying valid access token"""
        token = jwt_manager.generate_token("123")
        decoded = jwt_manager.verify_token(token)
        assert decoded is not None
        assert decoded["sub"] == "123"
    
    def test_invalid_token(self):
        """Test verifying invalid token"""
        decoded = jwt_manager.verify_token("invalid.token.here")
        assert decoded is None


class TestRateLimiter:
    """Test rate limiting functionality"""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter can be initialized"""
        limiter = RateLimiter()
        assert limiter is not None
    
    def test_rate_limit_check(self):
        """Test rate limit check"""
        limiter = RateLimiter()
        
        # First request should be allowed
        result = limiter.is_allowed("test_key", max_attempts=10, window_seconds=60)
        assert result is True


class TestConfig:
    """Test configuration management"""
    
    def test_config_loads(self):
        """Test configuration loads without errors"""
        assert config is not None
        assert config.version is not None
    
    def test_security_config(self):
        """Test security configuration exists"""
        assert config.security is not None
        assert hasattr(config.security, 'secret_key')
    
    def test_database_config(self):
        """Test database configuration"""
        assert config.database is not None
        assert hasattr(config.database, 'type')


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
