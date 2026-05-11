#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Security Module Tests
Tests for password hashing, JWT, encryption, and session management
"""

import pytest
import time
from datetime import datetime, timedelta, timezone

from acas_pro.core.security import (
    PasswordValidator,
    PasswordHasher,
    JWTManager,
    CryptoManager,
    RateLimiter
)


class TestPasswordValidator:
    """Password validation tests"""
    
    def test_valid_password(self):
        """Test valid password passes all checks"""
        is_valid, msg = PasswordValidator.validate("Test@123456")
        assert is_valid is True
        assert msg == ""
    
    def test_too_short(self):
        """Test password too short"""
        is_valid, msg = PasswordValidator.validate("Test@1")
        assert is_valid is False
        assert "at least" in msg
    
    def test_no_uppercase(self):
        """Test password without uppercase"""
        is_valid, msg = PasswordValidator.validate("test@123456")
        assert is_valid is False
        assert "uppercase" in msg
    
    def test_no_lowercase(self):
        """Test password without lowercase"""
        is_valid, msg = PasswordValidator.validate("TEST@123456")
        assert is_valid is False
        assert "lowercase" in msg
    
    def test_no_digit(self):
        """Test password without digit"""
        is_valid, msg = PasswordValidator.validate("Test@password")
        assert is_valid is False
        assert "digit" in msg
    
    def test_no_special(self):
        """Test password without special character"""
        is_valid, msg = PasswordValidator.validate("Test123456")
        assert is_valid is False
        assert "special" in msg
    
    def test_common_password(self):
        """Test common password rejected"""
        is_valid, msg = PasswordValidator.validate("Password@123")
        assert is_valid is False
        assert "common" in msg


class TestPasswordHasher:
    """Password hashing tests"""
    
    def test_hash_and_verify(self):
        """"Test password hashing and verification"""
        password = "Test@123456"  # noqa: B105
        hashed = PasswordHasher.hash(password)
        
        # Hash should be different from password
        assert hashed != password
        
        # Should verify correctly
        assert PasswordHasher.verify(password, hashed) is True
        
        # Wrong password should fail
        assert PasswordHasher.verify("Wrong@123", hashed) is False
    
    def test_unique_hashes(self):
        """Test same password produces different hashes (salt)"""
        password = "Test@123456"  # noqa: B105
        hash1 = PasswordHasher.hash(password)
        hash2 = PasswordHasher.hash(password)
        
        # Different salts = different hashes
        assert hash1 != hash2
        
        # Both should verify
        assert PasswordHasher.verify(password, hash1) is True
        assert PasswordHasher.verify(password, hash2) is True
    
    def test_hash_format(self):
        """Test hash format is correct"""
        password = "Test@123456"  # noqa: B105
        hashed = PasswordHasher.hash(password)
        
        # Format: pbkdf2:sha256:iterations$salt$hash
        parts = hashed.split('$')
        assert len(parts) == 3
        
        algo_part = parts[0]
        assert algo_part.startswith("pbkdf2:sha256:")


class TestJWTManager:
    """JWT token tests"""
    
    def test_generate_and_verify(self):
        """Test JWT generation and verification"""
        user_id = "U20240101001"
        token = JWTManager.generate_token(user_id)
        
        # Token should be string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Should verify correctly
        payload = JWTManager.verify_token(token)
        assert payload is not None
        assert payload['sub'] == user_id
        assert payload['type'] == 'access'
    
    def test_expired_token(self):
        """Test expired token is rejected"""
        import jwt
        
        # Create expired token
        now = datetime.now(timezone.utc)
        payload = {
            'sub': 'U001',
            'iat': now - timedelta(hours=2),
            'exp': now - timedelta(hours=1),
            'type': 'access'
        }
        
        from acas_pro.core.config import get_config
        token = jwt.encode(payload, get_config().security.secret_key, algorithm='HS256')
        
        # Should fail verification
        result = JWTManager.verify_token(token)
        assert result is None
    
    def test_refresh_token(self):
        """Test refresh token generation"""
        user_id = "U20240101001"
        refresh_token = JWTManager.generate_refresh_token(user_id)
        
        # Should verify as refresh token
        payload = JWTManager.verify_token(refresh_token, expected_type='refresh')
        assert payload is not None
        assert payload['sub'] == user_id
        assert payload['type'] == 'refresh'
        
        # Should NOT verify as access token
        payload = JWTManager.verify_token(refresh_token, expected_type='access')
        assert payload is None
    
    def test_refresh_access_token(self):
        """Test refreshing access token"""
        user_id = "U20240101001"
        refresh_token = JWTManager.generate_refresh_token(user_id)
        
        # Get new access token
        new_access = JWTManager.refresh_access_token(refresh_token)
        assert new_access is not None
        
        # Verify new access token
        payload = JWTManager.verify_token(new_access)
        assert payload is not None
        assert payload['sub'] == user_id


class TestCryptoManager:
    """Encryption tests"""
    
    def test_encrypt_decrypt(self):
        """Test Fernet encryption and decryption"""
        crypto = CryptoManager(key="test_encryption_key_32_characters_")
        
        plaintext = "This is a secret message"
        ciphertext = crypto.encrypt(plaintext)
        
        # Ciphertext should be different
        assert ciphertext != plaintext
        
        # Should decrypt correctly
        decrypted = crypto.decrypt(ciphertext)
        assert decrypted == plaintext
    
    def test_empty_string(self):
        """Test empty string handling"""
        crypto = CryptoManager(key="test_encryption_key_32_characters_")
        
        assert crypto.encrypt("") == ""
        assert crypto.decrypt("") == ""
    
    def test_unicode(self):
        """Test Unicode string encryption"""
        crypto = CryptoManager(key="test_encryption_key_32_characters_")
        
        plaintext = "中文测试 🎉 émojis"
        ciphertext = crypto.encrypt(plaintext)
        decrypted = crypto.decrypt(ciphertext)
        
        assert decrypted == plaintext
    
    def test_tamper_detection(self):
        """Test tampered ciphertext is rejected"""
        crypto = CryptoManager(key="test_encryption_key_32_characters_")
        
        plaintext = "Secret data"
        ciphertext = crypto.encrypt(plaintext)
        
        # Tamper with ciphertext
        tampered = ciphertext[:-5] + "XXXXX"
        
        # Should raise error
        with pytest.raises(ValueError):
            crypto.decrypt(tampered)


class TestRateLimiter:
    """Rate limiter tests"""
    
    def test_allows_under_limit(self):
        """Test requests under limit are allowed"""
        limiter = RateLimiter()
        key = "test_key"
        
        for _ in range(5):
            assert limiter.is_allowed(key, max_attempts=5) is True
            limiter.record_attempt(key)
    
    def test_blocks_over_limit(self):
        """Test requests over limit are blocked"""
        limiter = RateLimiter()
        key = "test_key"
        
        # Record 5 attempts
        for _ in range(5):
            limiter.record_attempt(key)
        
        # Should be blocked
        assert limiter.is_allowed(key, max_attempts=5) is False
    
    def test_window_expiry(self):
        """Test rate limit window expires"""
        limiter = RateLimiter()
        key = "test_key"
        
        # Record attempts
        for _ in range(5):
            limiter.record_attempt(key)
        
        # Should be blocked
        assert limiter.is_allowed(key, max_attempts=5, window_seconds=1) is False
        
        # Wait for window to expire
        time.sleep(1.1)
        
        # Should be allowed again
        assert limiter.is_allowed(key, max_attempts=5, window_seconds=1) is True
    
    def test_reset(self):
        """Test rate limit reset"""
        limiter = RateLimiter()
        key = "test_key"
        
        # Record attempts
        for _ in range(5):
            limiter.record_attempt(key)
        
        # Reset
        limiter.reset(key)
        
        # Should be allowed
        assert limiter.is_allowed(key, max_attempts=5) is True
