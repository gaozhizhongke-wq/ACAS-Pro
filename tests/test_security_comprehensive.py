"""
Comprehensive tests for security module - targeting 80% coverage
"""
import os
import sys
import json
import pytest
import base64
import secrets
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from acas_pro.core.security import (
    CryptoManager, PasswordHasher, PasswordValidator,
    JWTManager, SessionManager, RateLimiter
)
from acas_pro.core import config


class TestCryptoManager:
    """Test CryptoManager encryption/decryption"""
    
    def test_encrypt_decrypt_roundtrip(self):
        cm = CryptoManager(key="test_key_for_encryption_123456789012")
        plaintext = "sensitive data"
        encrypted = cm.encrypt(plaintext)
        decrypted = cm.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_empty_string(self):
        cm = CryptoManager(key="test_key")
        assert cm.encrypt("") == ""
    
    def test_decrypt_empty_string(self):
        cm = CryptoManager(key="test_key")
        assert cm.decrypt("") == ""
    
    def test_encrypt_different_keys_different_output(self):
        cm1 = CryptoManager(key="key_one_123456789012345678901234567890")
        cm2 = CryptoManager(key="key_two_1234567890123456780123456789012")
        plaintext = "test data"
        
        encrypted1 = cm1.encrypt(plaintext)
        encrypted2 = cm2.encrypt(plaintext)
        assert encrypted1 != encrypted2
    
    def test_decrypt_with_wrong_key_fails(self):
        cm1 = CryptoManager(key="correct_key_123456789012345678901234567890")
        cm2 = CryptoManager(key="wrong_key_12345678901234567890123456789012")
        
        encrypted = cm1.encrypt("test data")
        with pytest.raises(ValueError):
            cm2.decrypt(encrypted)
    
    def test_decrypt_tampered_data_fails(self):
        cm = CryptoManager(key="test_key_12345678901234567890123456789012")
        encrypted = cm.encrypt("test data")
        
        # Tamper with the encrypted data
        tampered = encrypted[:-5] + "XXXXX"
        with pytest.raises(ValueError):
            cm.decrypt(tampered)
    
    def test_derive_key_from_env(self):
        with patch.dict(os.environ, {'ACAS_ENCRYPTION_KEY': 'env_key_123456789012345678901234567890'}):
            cm = CryptoManager()
            encrypted = cm.encrypt("test")
            decrypted = cm.decrypt(encrypted)
            assert decrypted == "test"
    
    def test_dev_salt_persistence(self, tmp_path):
        """Test development salt is persisted to file"""
        with patch.object(Path, 'home', return_value=tmp_path):
            with patch.object(config, 'environment', 'development'):
                # First initialization creates salt file
                cm1 = CryptoManager(key="test_key_12345678901234567890123456789012")
                salt_file = tmp_path / ".acas-pro" / ".dev_encryption_salt"
                assert salt_file.exists()
                
                # Read the salt
                salt1 = salt_file.read_text().strip()
                
                # Second initialization should use same salt
                cm2 = CryptoManager(key="test_key_12345678901234567890123456789012")
                salt2 = salt_file.read_text().strip()
                assert salt1 == salt2
    
    def test_production_requires_salt_env(self):
        with patch.object(config, 'environment', 'production'):
            with patch.dict(os.environ, {}, clear=True):
                with pytest.raises(ValueError, match="ACAS_ENCRYPTION_SALT"):
                    CryptoManager()


class TestPasswordHasher:
    """Test PasswordHasher"""
    
    def test_hash_verifies_correct_password(self):
        ph = PasswordHasher()
        password = "MyP@ssw0rd!123"
        hashed = ph.hash(password)
        assert ph.verify(password, hashed) is True
    
    def test_verify_wrong_password_fails(self):
        ph = PasswordHasher()
        password = "correct_password"
        wrong = "wrong_password"
        hashed = ph.hash(password)
        assert ph.verify(wrong, hashed) is False
    
    def test_hash_is_different_each_time(self):
        ph = PasswordHasher()
        password = "same_password"
        hash1 = ph.hash(password)
        hash2 = ph.hash(password)
        assert hash1 != hash2  # Due to salt
    
    def test_hash_contains_bcrypt_identifier(self):
        ph = PasswordHasher()
        hashed = ph.hash("test")
        assert "$2b$" in hashed or "$2a$" in hashed


class TestPasswordValidator:
    """Test PasswordValidator"""
    
    def test_valid_password(self):
        pv = PasswordValidator(min_length=8)
        is_valid, message = pv.validate("ValidP@ss1")
        assert is_valid is True
        assert message == "Password is valid"
    
    def test_too_short(self):
        pv = PasswordValidator(min_length=8)
        is_valid, message = pv.validate("Short1!")
        assert is_valid is False
        assert "at least 8 characters" in message
    
    def test_no_uppercase(self):
        pv = PasswordValidator(min_length=8)
        is_valid, message = pv.validate("lowercase1!")
        assert is_valid is False
        assert "uppercase" in message
    
    def test_no_lowercase(self):
        pv = PasswordValidator(min_length=8)
        is_valid, message = pv.validate("UPPERCASE1!")
        assert is_valid is False
        assert "lowercase" in message
    
    def test_no_digit(self):
        pv = PasswordValidator(min_length=8)
        is_valid, message = pv.validate("NoDigits!")
        assert is_valid is False
        assert "digit" in message
    
    def test_no_special_char(self):
        pv = PasswordValidator(min_length=8)
        is_valid, message = pv.validate("NoSpecial1")
        assert is_valid is False
        assert "special character" in message
    
    def test_common_password_rejected(self):
        pv = PasswordValidator(min_length=8)
        is_valid, message = pv.validate("Password1!")
        assert is_valid is False
        assert "common" in message.lower()
    
    def test_custom_min_length(self):
        pv = PasswordValidator(min_length=12)
        is_valid, message = pv.validate("Short1!")
        assert is_valid is False
        assert "at least 12 characters" in message


class TestJWTManager:
    """Test JWTManager"""
    
    def test_create_and_verify_token(self):
        jm = JWTManager(secret="test_secret_123456789012345678901234567890")
        payload = {"user_id": "123", "role": "admin"}
        token = jm.create_token(payload)
        
        verified = jm.verify_token(token)
        assert verified["user_id"] == "123"
        assert verified["role"] == "admin"
    
    def test_token_expires(self):
        jm = JWTManager(secret="test_secret_123456789012345678901234567890")
        payload = {"user_id": "123"}
        token = jm.create_token(payload, expires_in_seconds=-1)  # Already expired
        
        with pytest.raises(Exception):
            jm.verify_token(token)
    
    def test_verify_invalid_token_fails(self):
        jm = JWTManager(secret="test_secret_123456789012345678901234567890")
        with pytest.raises(Exception):
            jm.verify_token("invalid.token.here")
    
    def test_verify_tampered_token_fails(self):
        jm = JWTManager(secret="test_secret_123456789012345678901234567890")
        payload = {"user_id": "123"}
        token = jm.create_token(payload)
        
        # Tamper with token
        tampered = token[:-10] + "XXXXXXXXXX"
        with pytest.raises(Exception):
            jm.verify_token(tampered)
    
    def test_different_secrets_fail(self):
        jm1 = JWTManager(secret="secret_one_12345678901234567890123456789012")
        jm2 = JWTManager(secret="secret_two_12345678901234567890123456789012")
        
        token = jm1.create_token({"user_id": "123"})
        with pytest.raises(Exception):
            jm2.verify_token(token)


class TestSessionManager:
    """Test SessionManager"""
    
    def test_create_session(self):
        sm = SessionManager()
        session = sm.create_session("user_123", {"role": "admin"})
        
        assert session["user_id"] == "user_123"
        assert session["data"]["role"] == "admin"
        assert "created_at" in session
        assert "expires_at" in session
    
    def test_get_session_valid(self):
        sm = SessionManager()
        session = sm.create_session("user_123")
        session_id = session["session_id"]
        
        retrieved = sm.get_session(session_id)
        assert retrieved["user_id"] == "user_123"
    
    def test_get_session_invalid(self):
        sm = SessionManager()
        retrieved = sm.get_session("nonexistent_session")
        assert retrieved is None
    
    def test_delete_session(self):
        sm = SessionManager()
        session = sm.create_session("user_123")
        session_id = session["session_id"]
        
        sm.delete_session(session_id)
        retrieved = sm.get_session(session_id)
        assert retrieved is None
    
    def test_session_expires(self):
        sm = SessionManager()
        session = sm.create_session("user_123")
        session_id = session["session_id"]
        
        # Manually expire the session
        sm._sessions[session_id]["expires_at"] = 0
        
        retrieved = sm.get_session(session_id)
        assert retrieved is None
    
    def test_cleanup_expired_sessions(self):
        sm = SessionManager()
        
        # Create sessions
        s1 = sm.create_session("user_1")
        s2 = sm.create_session("user_2")
        
        # Expire one
        sm._sessions[s1["session_id"]]["expires_at"] = 0
        
        # Cleanup
        sm.cleanup_expired()
        
        assert sm.get_session(s1["session_id"]) is None
        assert sm.get_session(s2["session_id"]) is not None


class TestRateLimiter:
    """Test RateLimiter"""
    
    def test_is_allowed_within_limit(self):
        rl = RateLimiter()
        key = "test_key"
        
        # First 5 requests should be allowed
        for _ in range(5):
            assert rl.is_allowed(key, max_requests=5, window_seconds=60) is True
    
    def test_is_allowed_exceeds_limit(self):
        rl = RateLimiter()
        key = "test_key"
        
        # Make 5 requests
        for _ in range(5):
            rl.is_allowed(key, max_requests=5, window_seconds=60)
        
        # 6th request should be blocked
        assert rl.is_allowed(key, max_requests=5, window_seconds=60) is False
    
    def test_different_keys_independent(self):
        rl = RateLimiter()
        
        # Exhaust limit for key1
        for _ in range(5):
            rl.is_allowed("key1", max_requests=5, window_seconds=60)
        
        # key2 should still be allowed
        assert rl.is_allowed("key2", max_requests=5, window_seconds=60) is True
    
    def test_window_resets_after_time(self):
        rl = RateLimiter()
        key = "test_key"
        
        # Exhaust limit
        for _ in range(5):
            rl.is_allowed(key, max_requests=5, window_seconds=1)
        
        assert rl.is_allowed(key, max_requests=5, window_seconds=1) is False
        
        # Wait for window to reset
        import time
        time.sleep(1.1)
        
        assert rl.is_allowed(key, max_requests=5, window_seconds=1) is True
    
    def test_get_remaining_requests(self):
        rl = RateLimiter()
        key = "test_key"
        
        assert rl.get_remaining(key, max_requests=5) == 5
        
        rl.is_allowed(key, max_requests=5)
        assert rl.get_remaining(key, max_requests=5) == 4
        
        for _ in range(4):
            rl.is_allowed(key, max_requests=5)
        assert rl.get_remaining(key, max_requests=5) == 0


class TestSecurityEdgeCases:
    """Test edge cases"""
    
    def test_crypto_unicode_handling(self):
        cm = CryptoManager(key="test_key_12345678901234567890123456789012")
        plaintext = "Unicode: 中文 🎉 émojis"
        encrypted = cm.encrypt(plaintext)
        decrypted = cm.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_crypto_large_data(self):
        cm = CryptoManager(key="test_key_12345678901234567890123456789012")
        plaintext = "x" * 10000
        encrypted = cm.encrypt(plaintext)
        decrypted = cm.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_jwt_unicode_payload(self):
        jm = JWTManager(secret="test_secret_123456789012345678901234567890")
        payload = {"name": "中文测试", "emoji": "🎉"}
        token = jm.create_token(payload)
        verified = jm.verify_token(token)
        assert verified["name"] == "中文测试"
        assert verified["emoji"] == "🎉"
    
    def test_rate_limiter_zero_window(self):
        rl = RateLimiter()
        # Should handle edge case gracefully
        result = rl.is_allowed("test", max_requests=1, window_seconds=0)
        # Implementation dependent, but shouldn't crash
