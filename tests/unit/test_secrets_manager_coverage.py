# -*- coding: utf-8 -*-
"""Additional tests for SecretsManager to improve coverage"""
import pytest
from acas_pro.core.secrets_manager import SecretsManager, get_secrets_manager, _SECRET_ENV_MAP, _PRODUCTION_ENV_ONLY


class TestSecretsManagerCoverage:
    """Additional tests to improve SecretsManager coverage from 61% to 90%+"""
    
    def setup_method(self):
        """Reset singleton before each test"""
        global _instance
        from acas_pro.core.secrets_manager import _instance
        _instance = None  # noqa: F811
    
    def test_init_production(self):
        """Test initialization with production mode"""
        sm = SecretsManager(is_production=True)
        assert sm._is_production is True
    
    def test_init_development(self):
        """Test initialization with development mode"""
        sm = SecretsManager(is_production=False)
        assert sm._is_production is False
    
    def test_get_existing_env_var(self, monkeypatch):
        """Test getting existing environment variable"""
        monkeypatch.setenv('LLM_API_KEY', 'test-key-123')
        sm = SecretsManager()
        result = sm.get('llm_api_key')
        assert result == 'test-key-123'
    
    def test_get_with_fallback(self):
        """Test getting secret with fallback"""
        sm = SecretsManager()
        result = sm.get('nonexistent_key', fallback='default_value')
        assert result == 'default_value'
    
    def test_get_without_fallback_returns_none(self):
        """Test getting non-existent secret without fallback returns None"""
        sm = SecretsManager()
        result = sm.get('nonexistent_key')
        assert result is None
    
    def test_require_existing_secret(self, monkeypatch):
        """Test require with existing secret"""
        monkeypatch.setenv('ACAS_JWT_SECRET', 'jwt-secret-123')
        sm = SecretsManager()
        result = sm.require('jwt_secret')
        assert result == 'jwt-secret-123'
    
    def test_require_missing_secret_raises_error(self):
        """Test require with missing secret raises ValueError"""
        sm = SecretsManager()
        with pytest.raises(ValueError) as exc_info:
            sm.require('nonexistent_secret')
        assert "not found" in str(exc_info.value)
    
    def test_is_set_true(self, monkeypatch):
        """Test is_set returns True for existing secret"""
        monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-key')
        sm = SecretsManager()
        assert sm.is_set('deepseek_api_key') is True
    
    def test_is_set_false(self):
        """Test is_set returns False for non-existent secret"""
        sm = SecretsManager()
        assert sm.is_set('nonexistent_key') is False
    
    def test_mask_short_value(self):
        """Test masking short value"""
        sm = SecretsManager()
        result = sm.mask('short', visible=4)
        # 'short' is 5 chars, visible=4, so len > visible, should show masked
        # result should be: 'shor' + '...' + 'hort' = 'shor...hort'
        assert result == 'shor...hort'
    
    def test_mask_normal_value(self):
        """Test masking normal value"""
        sm = SecretsManager()
        result = sm.mask('sk-2f21abcd1234', visible=4)
        # Should be: first 4 chars + '...' + last 4 chars
        assert result == 'sk-2...1234'
    
    def test_mask_empty_value(self):
        """Test masking empty value"""
        sm = SecretsManager()
        result = sm.mask('', visible=4)
        assert result == '***'
    
    def test_mask_none_value(self):
        """Test masking None value"""
        sm = SecretsManager()
        result = sm.mask(None, visible=4)
        assert result == '***'
    
    def test_validate_production_all_set(self, monkeypatch):
        """Test validate_production when all secrets are set"""
        for env_key in _PRODUCTION_ENV_ONLY:
            monkeypatch.setenv(env_key, f'value_{env_key}')
        
        sm = SecretsManager(is_production=True)
        missing = sm.validate_production()
        assert missing == []
    
    def test_validate_production_some_missing(self, monkeypatch):
        """Test validate_production when some secrets are missing"""
        # Set only some secrets
        monkeypatch.setenv('ACAS_JWT_SECRET', 'jwt-secret')
        monkeypatch.setenv('LLM_API_KEY', 'llm-key')
        
        sm = SecretsManager(is_production=True)
        missing = sm.validate_production()
        assert len(missing) > 0
        # Check that missing contains expected format
        for item in missing:
            assert '(' in item and 'env:' in item
    
    def test_get_secrets_manager_singleton(self):
        """Test that get_secrets_manager returns singleton"""
        sm1 = get_secrets_manager(is_production=False)
        sm2 = get_secrets_manager(is_production=True)  # Should be ignored
        assert sm1 is sm2
    
    def test_get_secrets_manager_auto_detect_env(self, monkeypatch):
        """Test auto-detection of environment"""
        # Reset singleton by deleting the module-level variable
        import acas_pro.core.secrets_manager as sm_module
        sm_module._instance = None
        
        monkeypatch.setenv('ACAS_ENV', 'production')
        sm = get_secrets_manager()
        assert sm._is_production is True
    
    def test_get_secrets_manager_default_development(self, monkeypatch):
        """Test default environment is development"""
        import acas_pro.core.secrets_manager as sm_mod
        monkeypatch.delenv('ACAS_ENV', raising=False)
        monkeypatch.setattr(sm_mod, '_instance', None)
        sm = get_secrets_manager()
        assert sm._is_production is False
    
    def test_production_warning_logged(self, caplog):
        """Test that production warning is logged when using fallback"""
        import logging
        import acas_pro.core.secrets_manager as sm_mod
        sm_mod._instance = None
        sm = SecretsManager(is_production=True)
        
        with caplog.at_level(logging.WARNING):
            result = sm.get('llm_api_key', fallback='default-key')
        
        assert result == 'default-key'
        # Check that warning was logged
        assert any('insecure' in record.message.lower() or 'production' in record.message.lower() for record in caplog.records)
    
    def test_production_error_logged(self, caplog):
        """Test that production error is logged when secret not found"""
        import logging
        import acas_pro.core.secrets_manager as sm_mod
        sm_mod._instance = None
        sm = SecretsManager(is_production=True)
        
        with caplog.at_level(logging.ERROR):
            result = sm.get('llm_api_key')
        
        assert result is None
        # Check that error was logged
        assert any('critical' in record.message.lower() or 'not configured' in record.message.lower() for record in caplog.records)
    
    def test_secret_env_map_coverage(self, monkeypatch):
        """Test all mappings in _SECRET_ENV_MAP"""
        for logical_name, env_var in _SECRET_ENV_MAP.items():
            monkeypatch.setenv(env_var, f'value_for_{logical_name}')
            sm = SecretsManager()
            result = sm.get(logical_name)
            assert result == f'value_for_{logical_name}'
    
    def test_cache_behavior(self):
        """Test that secrets are cached"""
        sm = SecretsManager()
        # Access private cache
        assert hasattr(sm, '_cache')
        assert isinstance(sm._cache, dict)


class TestSecretsManagerEdgeCases:
    """Edge case tests for SecretsManager"""
    
    def setup_method(self):
        """Reset singleton before each test"""
        global _instance
        from acas_pro.core.secrets_manager import _instance
        _instance = None  # noqa: F811
    
    def test_get_with_empty_string_env(self, monkeypatch):
        """Test getting secret when env var is empty string"""
        monkeypatch.setenv('LLM_API_KEY', '')
        sm = SecretsManager()
        # Empty string is falsy, so should fall through to fallback
        result = sm.get('llm_api_key', fallback='default')
        assert result == 'default'
    
    def test_mask_with_custom_visible(self):
        """Test mask with custom visible length"""
        sm = SecretsManager()
        result = sm.mask('sk-abcdefghijklmnop', visible=6)
        # visible=6: first 6 chars + '...' + last 6 chars
        # 'sk-abc' + '...' + 'klmnop'
        assert result == 'sk-abc...klmnop'
        assert result.count('...') == 1
        assert len(result) == 6 + 3 + 6  # 15 chars
    
    def test_require_with_env_var_name(self, monkeypatch):
        """Test require using direct env var name"""
        monkeypatch.setenv('CUSTOM_SECRET', 'custom-value')
        sm = SecretsManager()
        result = sm.require('CUSTOM_SECRET')
        assert result == 'custom-value'
    
    def test_get_secrets_manager_twice(self):
        """Test calling get_secrets_manager twice returns same instance"""
        sm1 = get_secrets_manager(is_production=False)
        sm2 = get_secrets_manager()
        assert sm1 is sm2
