"""
Tests for secrets_manager and other low-coverage modules.
"""
import os
import pytest
from unittest.mock import patch, MagicMock


class TestSecretsManager:
    def test_import(self):
        from acas_pro.core.secrets_manager import SecretsManager, get_secrets_manager

    def test_init(self):
        from acas_pro.core.secrets_manager import SecretsManager
        sm = SecretsManager()
        assert sm is not None
        assert not sm._is_production

    def test_init_production(self):
        from acas_pro.core.secrets_manager import SecretsManager
        sm = SecretsManager(is_production=True)
        assert sm._is_production

    def test_get_env_var(self):
        from acas_pro.core.secrets_manager import SecretsManager
        sm = SecretsManager()
        with patch.dict(os.environ, {'TEST_KEY': 'test_val'}):
            val = sm.get('TEST_KEY')
            assert val == 'test_val'

    def test_get_logical_name(self):
        from acas_pro.core.secrets_manager import SecretsManager
        sm = SecretsManager()
        with patch.dict(os.environ, {'DEEPSEEK_API_KEY': 'sk-123'}):
            val = sm.get('deepseek_api_key')
            assert val == 'sk-123'

    def test_get_fallback(self):
        from acas_pro.core.secrets_manager import SecretsManager
        sm = SecretsManager()
        val = sm.get('NONEXISTENT_12345', fallback='default')
        assert val == 'default'

    def test_get_missing_returns_none(self):
        from acas_pro.core.secrets_manager import SecretsManager
        sm = SecretsManager()
        val = sm.get('NONEXISTENT_12345')
        assert val is None

    def test_require_present(self):
        from acas_pro.core.secrets_manager import SecretsManager
        sm = SecretsManager()
        with patch.dict(os.environ, {'REQ_KEY': 'val'}):
            val = sm.require('REQ_KEY')
            assert val == 'val'

    def test_require_missing_raises(self):
        from acas_pro.core.secrets_manager import SecretsManager
        sm = SecretsManager()
        with pytest.raises(ValueError):
            sm.require('NONEXISTENT_REQ_KEY_12345')

    def test_is_set(self):
        from acas_pro.core.secrets_manager import SecretsManager
        sm = SecretsManager()
        with patch.dict(os.environ, {'SET_KEY': 'v'}):
            assert sm.is_set('SET_KEY') is True
        assert sm.is_set('NOT_SET_9999') is False

    def test_mask(self):
        from acas_pro.core.secrets_manager import SecretsManager
        sm = SecretsManager()
        assert sm.mask('sk-1234567890abcdef') == 'sk-1...cdef'
        assert sm.mask('ab') == '***'
        assert sm.mask('') == '***'

    def test_validate_production(self):
        from acas_pro.core.secrets_manager import SecretsManager
        sm = SecretsManager(is_production=True)
        missing = sm.validate_production()
        # Should list missing secrets
        assert isinstance(missing, list)

    def test_validate_production_all_set(self):
        from acas_pro.core.secrets_manager import SecretsManager
        sm = SecretsManager(is_production=True)
        env_vars = {
            'ACAS_JWT_SECRET': 'v', 'ACAS_ENCRYPTION_SALT': 'v',
            'LLM_API_KEY': 'v', 'DEEPSEEK_API_KEY': 'v',
            'ANTHROPIC_API_KEY': 'v', 'GOOGLE_API_KEY': 'v',
            'DATABASE_PASSWORD': 'v', 'SECRET_KEY': 'v',
        }
        with patch.dict(os.environ, env_vars):
            missing = sm.validate_production()
            assert missing == []

    def test_singleton(self):
        from acas_pro.core.secrets_manager import get_secrets_manager
        # Reset singleton
        import acas_pro.core.secrets_manager as mod
        mod._instance = None
        sm1 = get_secrets_manager()
        sm2 = get_secrets_manager()
        assert sm1 is sm2
        mod._instance = None  # cleanup

    def test_production_fallback_warning(self):
        from acas_pro.core.secrets_manager import SecretsManager
        sm = SecretsManager(is_production=True)
        # Should return fallback but log warning
        val = sm.get('deepseek_api_key', fallback='insecure')
        assert val == 'insecure'
