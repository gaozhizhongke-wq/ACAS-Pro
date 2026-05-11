"""Test v2 modules - Target 95 Score"""
import pytest
from unittest.mock import MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


class TestConfigV2:
    """Test config v2 module"""
    
    def test_config_defaults(self):
        from acas_pro.core.config_v2 import AppConfig
        config = AppConfig()
        assert config.environment == 'development'
        assert config.debug is True
    
    def test_config_validate(self):
        from acas_pro.core.config_v2 import AppConfig
        config = AppConfig()
        is_valid, errors = config.validate()
        assert isinstance(is_valid, bool)
        assert isinstance(errors, list)
    
    def test_config_to_dict(self):
        from acas_pro.core.config_v2 import AppConfig
        config = AppConfig()
        d = config.to_dict()
        assert isinstance(d, dict)
        assert 'environment' in d


class TestSecurityV2:
    """Test security v2 module"""
    
    def test_password_validator(self):
        from acas_pro.core.security_v2 import PasswordValidator
        validator = PasswordValidator()
        
        # Test weak password
        is_valid, msg = validator.validate("short")
        assert not is_valid
        
        # Test valid password
        is_valid, msg = validator.validate("ValidPass123!")
        assert is_valid
    
    def test_password_hasher(self):
        from acas_pro.core.security_v2 import PasswordHasher
        hasher = PasswordHasher()
        
        password = "test_password"
        hash_str = hasher.hash(password)
        assert hash_str.startswith("pbkdf2_sha256$")
        
        # Verify
        assert hasher.verify(password, hash_str)
        assert not hasher.verify("wrong_password", hash_str)
    
    def test_jwt_manager(self):
        from acas_pro.core.security_v2 import JWTManager
        manager = JWTManager()
        
        token = manager.generate_token("user123")
        assert isinstance(token, str)
        
        is_valid, payload = manager.verify_token(token)
        assert is_valid
        assert payload['sub'] == 'user123'
    
    def test_crypto_manager(self):
        from acas_pro.core.security_v2 import CryptoManager
        manager = CryptoManager()
        
        data = "sensitive data"
        encrypted = manager.encrypt(data)
        assert encrypted != data
        
        decrypted = manager.decrypt(encrypted)
        assert decrypted == data
    
    def test_session_manager(self):
        from acas_pro.core.security_v2 import SessionManager
        manager = SessionManager()
        
        session_id = manager.create_session("user123", {"role": "admin"})
        assert isinstance(session_id, str)
        
        session = manager.get_session(session_id)
        assert session is not None
        assert session['user_id'] == 'user123'
        
        # Destroy
        assert manager.destroy_session(session_id)
        assert manager.get_session(session_id) is None


class TestDIContainer:
    """Test DI container"""
    
    def test_container_creation(self):
        from acas_pro.core.di_container import DIContainer
        container = DIContainer()
        assert container is not None
    
    def test_register_and_resolve(self):
        from acas_pro.core.di_container import DIContainer
        container = DIContainer()
        
        # Register singleton
        container.register_singleton(str, lambda: "test")
        
        # Resolve
        result = container.resolve(str)
        assert result == "test"
    
    def test_factory_pattern(self):
        from acas_pro.core.di_container import DIContainer
        from acas_pro.core.config_v2 import AppConfig
        
        container = DIContainer()
        container.register_factory(AppConfig, lambda c: AppConfig())
        
        config = container.resolve(AppConfig)
        assert config is not None


class TestIntegration:
    """Integration tests"""
    
    def test_security_with_config(self):
        from acas_pro.core.config_v2 import AppConfig, SecurityConfig
        from acas_pro.core.security_v2 import PasswordHasher
        
        config = AppConfig()
        config.security.secret_key = "test-secret"
        
        hasher = PasswordHasher(config.security)
        hash_str = hasher.hash("password")
        assert hasher.verify("password", hash_str)
