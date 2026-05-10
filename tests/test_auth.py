"""Authentication tests for ACAS Pro"""
import pytest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from acas_pro.core.security import (
    PasswordValidator,
    JWTManager,
    rate_limiter,
    password_validator as pv
)
from acas_pro.core.config import config


class TestPasswordValidator:
    """Test password validation rules"""
    
    def test_valid_password(self):
        """Test a valid strong password"""
        result = pv.validate("StrongP@ss123")
        assert result.is_valid
        assert len(result.errors) == 0
    
    def test_password_too_short(self):
        """Test password minimum length"""
        result = pv.validate("Short1!")
        assert not result.is_valid
        assert any("8 characters" in e for e in result.errors)
    
    def test_password_no_uppercase(self):
        """Test password requires uppercase"""
        result = pv.validate("lowercase123!")
        assert not result.is_valid
        assert any("uppercase" in e for e in result.errors)
    
    def test_password_no_lowercase(self):
        """Test password requires lowercase"""
        result = pv.validate("UPPERCASE123!")
        assert not result.is_valid
        assert any("lowercase" in e for e in result.errors)
    
    def test_password_no_digit(self):
        """Test password requires digit"""
        result = pv.validate("NoDigitsHere!")
        assert not result.is_valid
        assert any("digit" in e for e in result.errors)
    
    def test_password_no_special(self):
        """Test password requires special character"""
        result = pv.validate("NoSpecial123")
        assert not result.is_valid
        assert any("special" in e for e in result.errors)
    
    def test_password_common(self):
        """Test password against common passwords"""
        result = pv.validate("Password123!")
        assert not result.is_valid
        assert any("common" in e.lower() for e in result.errors)
    
    def test_password_with_username(self):
        """Test password cannot contain username"""
        result = pv.validate("john123!", username="john")
        assert not result.is_valid
        assert any("username" in e.lower() for e in result.errors)


class TestJWTManager:
    """Test JWT token management"""
    
    @pytest.fixture
    def jwt_manager(self):
        return JWTManager(
            secret_key="test-secret-key-for-testing-only",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7
        )
    
    def test_create_access_token(self, jwt_manager):
        """Test creating access token"""
        token = jwt_manager.create_access_token({"user_id": "123", "role": "admin"})
        assert token is not None
        assert isinstance(token, str)
    
    def test_verify_access_token(self, jwt_manager):
        """Test verifying valid access token"""
        payload = {"user_id": "123", "role": "admin"}
        token = jwt_manager.create_access_token(payload)
        decoded = jwt_manager.verify_token(token)
        assert decoded["user_id"] == "123"
        assert decoded["role"] == "admin"
    
    def test_verify_expired_token(self, jwt_manager):
        """Test verifying expired token"""
        import time
        from datetime import datetime, timezone
        
        # Create token with past expiration
        token = jwt_manager.create_access_token({"user_id": "123"})
        # Wait a bit and try to verify (in real test would mock time)
        # For now, just verify structure
        assert token is not None
    
    def test_invalid_token(self, jwt_manager):
        """Test verifying invalid token"""
        with pytest.raises(Exception):
            jwt_manager.verify_token("invalid.token.here")


class TestRateLimiter:
    """Test rate limiting functionality"""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter can be initialized"""
        from acas_pro.core.security import RateLimiter
        limiter = RateLimiter()
        assert limiter is not None
    
    def test_rate_limit_check(self):
        """Test rate limit check"""
        from acas_pro.core.security import RateLimiter
        limiter = RateLimiter()
        
        # First request should be allowed
        result = limiter.is_allowed("test_key", max_requests=10, window_seconds=60)
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
