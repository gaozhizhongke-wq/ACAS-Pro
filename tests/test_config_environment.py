"""Tests for config environment override logic"""
import os
import pytest
from acas_pro.core.config import AppConfig


class TestConfigEnvironment:
    """Test environment variable override behavior"""
    
    def test_env_override_explicit_staging(self):
        """ACAS_ENV=production should override explicit staging"""
        os.environ['ACAS_ENV'] = 'production'
        config = AppConfig(environment='staging')
        assert config.environment == 'production', \
            f"Expected 'production', got '{config.environment}'"
    
    def test_env_override_explicit_development(self):
        """ACAS_ENV=production should override explicit development"""
        os.environ['ACAS_ENV'] = 'production'
        config = AppConfig(environment='development')
        assert config.environment == 'production'
    
    def test_no_env_uses_default(self):
        """Without ACAS_ENV, should use provided value"""
        if 'ACAS_ENV' in os.environ:
            del os.environ['ACAS_ENV']
        config = AppConfig(environment='staging')
        assert config.environment == 'staging'
    
    def test_no_env_no_explicit_uses_development(self):
        """Without ACAS_ENV and no explicit value, uses development"""
        if 'ACAS_ENV' in os.environ:
            del os.environ['ACAS_ENV']
        config = AppConfig()
        assert config.environment == 'development'
    
    def test_env_staging_override(self):
        """ACAS_ENV=staging should work"""
        os.environ['ACAS_ENV'] = 'staging'
        config = AppConfig(environment='production')
        assert config.environment == 'staging'
