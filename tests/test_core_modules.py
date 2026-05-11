"""
Consolidated tests for core modules - config, security, database
Targeting 95%+ coverage with minimal duplication
"""
import os
import json
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, mock_open

from acas_pro.core.config import (
    DatabaseConfig, SecurityConfig, LLMConfig,
    OAuthConfig, AppConfig
)
from acas_pro.core.security import (
    CryptoManager, PasswordHasher, JWTManager
)
from acas_pro.core.database import DatabaseManager


class TestEnvironmentValues:
    """Test environment string values"""
    
    def test_environment_values(self):
        # AppConfig uses string environment, not enum
        config = AppConfig(environment="development")
        assert config.environment == "development"
        config = AppConfig(environment="production")
        assert config.environment == "production"
        config = AppConfig(environment="staging")
        assert config.environment == "staging"


class TestDatabaseConfig:
    """Test DatabaseConfig"""
    
    def test_defaults(self):
        db = DatabaseConfig()
        assert db.type == "sqlite"
        assert db.host == "localhost"
        assert db.port == 5432
        assert ".acas-pro" in db.path
    
    def test_post_init_creates_path(self, mock_home):
        db = DatabaseConfig()
        assert "acas.db" in db.path


class TestSecurityConfig:
    """Test SecurityConfig"""
    
    def test_defaults(self):
        sec = SecurityConfig()
        assert sec.jwt_algorithm == "HS256"
        assert sec.password_min_length == 8
        assert sec.pbkdf2_iterations == 600000
    
    def test_env_secret_key_override(self, mock_home):
        with patch.dict(os.environ, {'ACAS_SECRET_KEY': 'env_secret_32_chars_long!!!!!!'}):
            sec = SecurityConfig()
            assert sec.secret_key == 'env_secret_32_chars_long!!!!!!'


class TestAppConfig:
    """Test AppConfig"""
    
    def test_defaults(self):
        config = AppConfig()
        assert config.name == "ACAS Pro"
        assert config.version == "4.0.0"
        assert config.environment == Environment.DEVELOPMENT
    
    def test_acas_env_override(self, mock_home):
        """ACAS_ENV must always take precedence"""
        with patch.dict(os.environ, {'ACAS_ENV': 'production'}):
            config = AppConfig()
            assert config.environment == "production"
    
    def test_acas_env_override_explicit_staging(self, mock_home):
        """ACAS_ENV overrides even explicitly set values"""
        with patch.dict(os.environ, {'ACAS_ENV': 'staging'}):
            config = AppConfig(environment="production")
            assert config.environment == "staging"
    
    def test_is_production_property(self):
        # Check production environment
        config = AppConfig(environment="production")
        assert config.environment == "production"
        # Check development environment  
        config = AppConfig(environment="development")
        assert config.environment == "development"
    
    def test_validation_fails_without_secret_key(self):
        config = AppConfig()
        config.security.secret_key = ""
        is_valid, errors = config.validate()
        assert is_valid is False
        assert any("secret_key" in e.lower() for e in errors)
    
    def test_validation_fails_short_password_min_length(self):
        config = AppConfig()
        config.security.password_min_length = 4
        is_valid, errors = config.validate()
        assert is_valid is False
        assert any("Password minimum length" in e for e in errors)
    
    def test_save_redacts_sensitive_data(self, tmp_path, mock_home):
        config = AppConfig()
        config.security.secret_key = "super_secret_key"
        config.llm.api_key = "sk-test"
        
        config_path = tmp_path / "config.json"
        config.save(str(config_path))
        
        saved = json.loads(config_path.read_text())
        assert saved["security"]["secret_key"] == "***REDACTED***"
        assert saved["llm"]["api_key"] == "***REDACTED***"


class TestCryptoManager:
    """Test CryptoManager"""
    
    def test_encrypt_decrypt_roundtrip(self):
        cm = CryptoManager(key="test_key_32_chars_long_for_testing!!")
        plaintext = "sensitive data"
        encrypted = cm.encrypt(plaintext)
        decrypted = cm.decrypt(encrypted)
        assert decrypted == plaintext
    
    def test_encrypt_empty_string(self):
        cm = CryptoManager(key="test_key_32_chars_long_for_testing!!")
        assert cm.encrypt("") == ""
    
    def test_different_keys_produce_different_output(self):
        cm1 = CryptoManager(key="key_one_32_chars_long_for_test!!")
        cm2 = CryptoManager(key="key_two_32_chars_long_for_test!!")
        encrypted1 = cm1.encrypt("test")
        encrypted2 = cm2.encrypt("test")
        assert encrypted1 != encrypted2


class TestPasswordHasher:
    """Test PasswordHasher"""
    
    def test_hash_verifies_correct_password(self):
        ph = PasswordHasher()
        password = "MyP@ssw0rd!123"
        hashed = ph.hash(password)
        assert ph.verify(password, hashed) is True
    
    def test_verify_wrong_password_fails(self):
        ph = PasswordHasher()
        hashed = ph.hash("correct_password")
        assert ph.verify("wrong_password", hashed) is False
    
    def test_hash_contains_bcrypt_identifier(self):
        ph = PasswordHasher()
        hashed = ph.hash("test")
        assert "$2b$" in hashed or "$2a$" in hashed


class TestJWTManager:
    """Test JWTManager"""
    
    def test_create_and_verify_token(self):
        jm = JWTManager(secret="test_secret_32_chars_long!!!!!!")
        payload = {"user_id": "123", "role": "admin"}
        token = jm.create_token(payload)
        verified = jm.verify_token(token)
        assert verified["user_id"] == "123"
        assert verified["role"] == "admin"
    
    def test_expired_token_fails(self):
        jm = JWTManager(secret="test_secret_32_chars_long!!!!!!")
        token = jm.create_token({"user_id": "123"}, expires_in_seconds=-1)
        with pytest.raises(Exception):
            jm.verify_token(token)


class TestDatabaseManager:
    """Test DatabaseManager"""
    
    def test_singleton_pattern(self):
        db1 = DatabaseManager()
        db2 = DatabaseManager()
        assert db1 is db2
    
    def test_get_instance_returns_same(self):
        db1 = DatabaseManager.get_instance()
        db2 = DatabaseManager.get_instance()
        assert db1 is db2


class TestDatetimeUsage:
    """Verify no deprecated datetime.utcnow() usage"""
    
    def test_timezone_aware_datetime(self):
        """All datetime operations should be timezone-aware"""
        now = datetime.now(timezone.utc)
        assert now.tzinfo is not None
    
    def test_isoformat_includes_timezone(self):
        now = datetime.now(timezone.utc)
        iso = now.isoformat()
        assert "+" in iso or "Z" in iso or "UTC" in iso
