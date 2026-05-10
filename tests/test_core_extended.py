#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Core Module Extended Tests
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from acas_pro.core.config import config
from acas_pro.core.security import CryptoManager, PasswordHasher, PasswordValidator
from acas_pro.core.database import DatabaseManager


class TestPasswordHasherExtended:
    """Extended PasswordHasher tests"""
    
    def test_hash_password_consistency(self):
        """Test password hashing is consistent"""
        password = "test_password_123"
        hash1 = PasswordHasher.hash(password)
        hash2 = PasswordHasher.hash(password)
        
        # Different hashes due to salt
        assert hash1 != hash2
        
        # But both should verify
        assert PasswordHasher.verify(password, hash1)
        assert PasswordHasher.verify(password, hash2)
    
    def test_verify_password_wrong(self):
        """Test verify with wrong password"""
        password = "correct_password"
        wrong = "wrong_password"
        
        hashed = PasswordHasher.hash(password)
        
        assert not PasswordHasher.verify(wrong, hashed)
    
    def test_password_validator_valid(self):
        """Test valid password"""
        valid, msg = PasswordValidator.validate("StrongPass123!")
        assert valid is True
        assert msg == ""
    
    def test_password_validator_too_short(self):
        """Test too short password"""
        valid, msg = PasswordValidator.validate("Short1!")
        assert valid is False
        assert "8" in msg
    
    def test_password_validator_no_uppercase(self):
        """Test password without uppercase"""
        valid, msg = PasswordValidator.validate("lowercase123!")
        assert valid is False
        assert "uppercase" in msg


class TestCryptoManagerExtended:
    """Extended CryptoManager tests"""
    
    @pytest.fixture
    def crypto(self):
        return CryptoManager()
    
    def test_encrypt_decrypt_cycle(self, crypto):
        """Test encrypt/decrypt roundtrip"""
        plaintext = "Sensitive data here"
        
        encrypted = crypto.encrypt(plaintext)
        decrypted = crypto.decrypt(encrypted)
        
        assert decrypted == plaintext
    
    def test_encrypt_different_results(self, crypto):
        """Test same plaintext encrypts differently"""
        plaintext = "test"
        
        encrypted1 = crypto.encrypt(plaintext)
        encrypted2 = crypto.encrypt(plaintext)
        
        assert encrypted1 != encrypted2


class TestConfigExtended:
    """Extended config tests"""
    
    def test_config_singleton(self):
        """Test config is singleton"""
        from acas_pro.core.config import config as config1
        from acas_pro.core.config import config as config2
        
        assert config1 is config2
    
    def test_config_has_required_sections(self):
        """Test config has required sections"""
        # Config is a dataclass with direct fields
        assert hasattr(config, 'database')
        assert hasattr(config, 'ui')
        assert hasattr(config, 'security')
    
    def test_config_app_name(self):
        """Test app name"""
        # config itself is the app config
        assert config.name == "ACAS Pro"


class TestDatabaseManagerExtended:
    """Extended DatabaseManager tests"""
    
    def test_database_singleton(self):
        """Test database is singleton"""
        from acas_pro.core.database import DatabaseManager
        
        db1 = DatabaseManager()
        db2 = DatabaseManager()
        
        assert db1 is db2
    
    def test_database_methods_exist(self):
        """Test required methods exist"""
        from acas_pro.core.database import DatabaseManager
        
        db = DatabaseManager()
        
        assert callable(db.execute)
        assert callable(db.execute_one)
        assert callable(db.transaction)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
