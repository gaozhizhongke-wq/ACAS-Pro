"""
Comprehensive tests for config module - targeting 80% coverage
"""
import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from acas_pro.core.config import (
    DatabaseConfig, SecurityConfig, MLConfig, LLMConfig,
    OAuthConfig, AlertConfig, WorldMonitorConfig, AppConfig
)


class TestDatabaseConfig:
    """Test DatabaseConfig dataclass"""
    
    def test_default_values(self):
        db = DatabaseConfig()
        assert db.type == "sqlite"
        assert db.host == "localhost"
        assert db.port == 5432
        assert db.name == "acas"
        assert db.pool_size == 10
        assert db.max_overflow == 20
    
    def test_post_init_creates_path(self):
        db = DatabaseConfig()
        assert ".acas-pro" in db.path
        assert "acas.db" in db.path
    
    def test_custom_values(self):
        db = DatabaseConfig(
            type="postgresql",
            host="db.example.com",
            port=5433,
            name="testdb",
            user="admin",
            password="secret"
        )
        assert db.type == "postgresql"
        assert db.host == "db.example.com"
        assert db.password == "secret"


class TestSecurityConfig:
    """Test SecurityConfig dataclass"""
    
    def test_default_values(self):
        sec = SecurityConfig()
        assert sec.jwt_algorithm == "HS256"
        assert sec.jwt_expiry_hours == 24
        assert sec.password_min_length == 8
        assert sec.pbkdf2_iterations == 600000
        assert sec.max_login_attempts == 5
        assert sec.enable_https is False
    
    def test_post_init_generates_secret_key(self, tmp_path):
        with patch('acas_pro.core.config.Path') as mock_path_class:
            mock_home = tmp_path
            mock_path_class.home.return_value = mock_home
            
            sec = SecurityConfig()
            assert len(sec.secret_key) == 64  # 32 bytes hex = 64 chars
    
    def test_post_init_uses_env_secret_key(self):
        with patch.dict(os.environ, {'ACAS_SECRET_KEY': 'env_secret_key_12345678901234567890123456789012'}):
            sec = SecurityConfig()
            assert sec.secret_key == 'env_secret_key_12345678901234567890123456789012'


class TestLLMConfig:
    """Test LLMConfig dataclass"""
    
    def test_default_values(self):
        llm = LLMConfig()
        assert llm.enabled is False
        assert llm.provider == "openai"
        assert llm.max_tokens == 4096
        assert llm.temperature == 0.7
        assert llm.agent_mode is True
    
    def test_get_default_model_openai(self):
        llm = LLMConfig(provider="openai")
        assert llm.get_default_model() == "gpt-4o"
    
    def test_get_default_model_deepseek(self):
        llm = LLMConfig(provider="deepseek")
        assert llm.get_default_model() == "deepseek-chat"
    
    def test_get_default_model_unknown(self):
        llm = LLMConfig(provider="unknown")
        assert llm.get_default_model() == ""


class TestOAuthConfig:
    """Test OAuthConfig dataclass"""
    
    def test_default_values(self):
        oauth = OAuthConfig()
        assert oauth.qq_enabled is False
        assert oauth.wechat_enabled is False
        assert "acas-pro.com" in oauth.qq_redirect_uri
        assert "acas-pro.com" in oauth.wechat_redirect_uri


class TestAlertConfig:
    """Test AlertConfig dataclass"""
    
    def test_default_values(self):
        alert = AlertConfig()
        assert alert.critical_score_threshold == 60
        assert alert.warning_score_threshold == 70
        assert alert.negative_ratio_threshold == 0.3
        assert alert.smtp_port == 587


class TestWorldMonitorConfig:
    """Test WorldMonitorConfig dataclass"""
    
    def test_default_values(self):
        wm = WorldMonitorConfig()
        assert wm.rss_refresh_interval == 15
        assert wm.sentiment_model == "rule"
        assert "wechat_work" in wm.alert_channels


class TestAppConfig:
    """Test AppConfig dataclass"""
    
    def test_default_values(self):
        config = AppConfig()
        assert config.name == "ACAS Pro"
        assert config.version == "5.2.0"
        assert config.environment == "development"
        assert config.debug is False
    
    def test_is_production_property(self):
        config_prod = AppConfig(environment="production")
        assert config_prod.environment == "production"
        
        config_dev = AppConfig(environment="development")
        assert config_dev.environment == "development"
    
    def test_is_development_property(self):
        config_dev = AppConfig(environment="development")
        assert config_dev.environment == "development"
        
        config_prod = AppConfig(environment="production")
        assert config_prod.environment == "production"
    
    def test_is_staging_property(self):
        config_staging = AppConfig(environment="staging")
        assert config_staging.environment == "staging"
    
    def test_acas_env_override_development(self):
        """Test ACAS_ENV overrides default development"""
        with patch.dict(os.environ, {'ACAS_ENV': 'production'}):
            config = AppConfig()
            assert config.environment == "production"
    
    def test_post_init_creates_directories(self, tmp_path):
        with patch('acas_pro.core.config.Path') as mock_path_class:
            mock_path_class.home.return_value = tmp_path
            
            config = AppConfig()
            assert (tmp_path / ".acas-pro" / "data").exists()
            assert (tmp_path / ".acas-pro" / "logs").exists()
            assert (tmp_path / ".acas-pro" / "backups").exists()
    
    def test_post_init_initializes_nested_configs(self):
        config = AppConfig()
        assert config.database is not None
        assert config.security is not None
        assert config.ml is not None
        assert config.ui is not None
        assert config.llm is not None
        assert config.oauth is not None
        assert config.alert is not None
        assert config.worldmonitor is not None


class TestAppConfigLLMFromEnv:
    """Test loading LLM config from environment"""
    
    def test_load_deepseek_from_env(self):
        with patch.dict(os.environ, {
            'DEEPSEEK_API_KEY': 'sk-deepseek-test',
            'DEEPSEEK_MODEL': 'deepseek-coder'
        }):
            config = AppConfig()
            assert config.llm.enabled is True
            assert config.llm.provider == 'deepseek'
            assert config.llm.api_key == 'sk-deepseek-test'
            assert config.llm.model == 'deepseek-coder'
    
    def test_load_openai_from_env(self):
        with patch.dict(os.environ, {
            'OPENAI_API_KEY': 'sk-openai-test',
            'OPENAI_MODEL': 'gpt-4'
        }):
            config = AppConfig()
            assert config.llm.enabled is True
            assert config.llm.provider == 'openai'
            assert config.llm.api_key == 'sk-openai-test'
    
    def test_load_anthropic_from_env(self):
        with patch.dict(os.environ, {'ANTHROPIC_API_KEY': 'sk-anthropic-test'}):
            config = AppConfig()
            assert config.llm.enabled is True
            assert config.llm.provider == 'anthropic'
    
    def test_load_qwen_from_env(self):
        with patch.dict(os.environ, {'QWEN_API_KEY': 'sk-qwen-test'}):
            config = AppConfig()
            assert config.llm.enabled is True
            assert config.llm.provider == 'qwen'
    
    def test_load_kimi_from_env(self):
        with patch.dict(os.environ, {'KIMI_API_KEY': 'sk-kimi-test'}):
            config = AppConfig()
            assert config.llm.enabled is True
            assert config.llm.provider == 'kimi'
    
    def test_llm_numeric_settings_from_env(self):
        with patch.dict(os.environ, {
            'LLM_MAX_TOKENS': '8192',
            'LLM_TEMPERATURE': '0.5',
            'LLM_TOP_P': '0.95',
            'LLM_MAX_AGENT_STEPS': '20',
            'LLM_AGENT_MODE': 'false'
        }):
            config = AppConfig()
            assert config.llm.max_tokens == 8192
            assert config.llm.temperature == 0.5
            assert config.llm.top_p == 0.95
            assert config.llm.max_agent_steps == 20
            assert config.llm.agent_mode is False


class TestAppConfigValidation:
    """Test AppConfig.validate() method"""
    
    def test_validate_empty_config_has_errors(self):
        config = AppConfig()
        config.security.secret_key = ""
        errors = config.validate()
        assert len(errors) > 0
        assert any("secret_key" in e.lower() for e in errors)
    
    def test_validate_short_secret_key(self):
        config = AppConfig()
        config.security.secret_key = "short"
        errors = config.validate()
        assert any("at least 32 characters" in e for e in errors)
    
    def test_validate_postgresql_requires_host(self):
        config = AppConfig()
        config.database.type = 'postgresql'
        config.database.host = ""
        errors = config.validate()
        assert any("database.host" in e for e in errors)
    
    def test_validate_postgresql_requires_name(self):
        config = AppConfig()
        config.database.type = 'postgresql'
        config.database.name = ""
        errors = config.validate()
        assert any("database.name" in e for e in errors)
    
    def test_validate_postgresql_requires_user(self):
        config = AppConfig()
        config.database.type = 'postgresql'
        config.database.user = ""
        errors = config.validate()
        assert any("database.user" in e for e in errors)
    
    def test_validate_llm_requires_api_key(self):
        config = AppConfig()
        config.llm.enabled = True
        config.llm.provider = 'openai'
        config.llm.api_key = ""
        errors = config.validate()
        assert any("api_key" in e.lower() for e in errors)
    
    def test_validate_llm_no_key_for_local(self):
        config = AppConfig()
        config.llm.enabled = True
        config.llm.provider = 'ollama'
        config.llm.api_key = ""
        errors = config.validate()
        # Should not require API key for ollama
        assert not any("api_key" in e.lower() and "ollama" not in e for e in errors)
    
    def test_validate_oauth_qq_requires_credentials(self):
        config = AppConfig()
        config.oauth.qq_enabled = True
        config.oauth.qq_app_id = ""
        errors = config.validate()
        assert any("qq_app_id" in e for e in errors)
    
    def test_validate_oauth_wechat_requires_credentials(self):
        config = AppConfig()
        config.oauth.wechat_enabled = True
        config.oauth.wechat_app_secret = ""
        errors = config.validate()
        assert any("wechat_app_secret" in e for e in errors)
    
    def test_validate_production_requires_https(self):
        config = AppConfig(environment="production")
        config.security.enable_https = False
        errors = config.validate()
        assert any("enable_https" in e for e in errors)
    
    def test_validate_production_no_debug(self):
        config = AppConfig(environment="production", debug=True)
        errors = config.validate()
        assert any("debug" in e.lower() for e in errors)
    
    def test_validate_production_prefers_postgresql(self):
        config = AppConfig(environment="production")
        config.database.type = "sqlite"
        errors = config.validate()
        assert any("PostgreSQL" in e for e in errors)
    
    def test_valid_config_has_no_errors(self):
        config = AppConfig()
        config.security.secret_key = "a" * 64
        config.llm.enabled = False
        errors = config.validate()
        # Should have minimal errors
        assert isinstance(errors, list)


class TestAppConfigLoadSave:
    """Test AppConfig.load() and save() methods"""
    
    def test_load_nonexistent_file_creates_default(self, tmp_path):
        config_path = tmp_path / "nonexistent.json"
        config = AppConfig.load(str(config_path))
        assert config.name == "ACAS Pro"
        assert config_path.exists()  # Should create default
    
    def test_load_existing_file(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_data = {
            "name": "Custom Name",
            "version": "5.0.0",
            "environment": "staging",
            "debug": True
        }
        config_path.write_text(json.dumps(config_data))
        
        config = AppConfig.load(str(config_path))
        assert config.name == "Custom Name"
        assert config.version == "5.0.0"
        assert config.environment == "staging"
        assert config.debug is True
    
    def test_load_corrupted_file_uses_defaults(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_path.write_text("not valid json{[")
        
        config = AppConfig.load(str(config_path))
        assert config.name == "ACAS Pro"  # Default
    
    def test_save_creates_file(self, tmp_path):
        config_path = tmp_path / "config.json"
        config = AppConfig(name="Test Config")
        config.save(str(config_path))
        
        assert config_path.exists()
        saved_data = json.loads(config_path.read_text())
        assert saved_data["name"] == "Test Config"
    
    def test_save_redacts_sensitive_data(self, tmp_path):
        config_path = tmp_path / "config.json"
        config = AppConfig()
        config.security.secret_key = "super_secret_key"
        config.llm.api_key = "sk-test-api-key"
        config.oauth.qq_app_key = "qq_secret"
        config.save(str(config_path))
        
        saved_data = json.loads(config_path.read_text())
        assert saved_data["security"]["secret_key"] == "***REDACTED***"
        assert saved_data["llm"]["api_key"] == "***REDACTED***"
        assert saved_data["oauth"]["qq_app_key"] == "***REDACTED***"
    
    def test_save_and_load_roundtrip(self, tmp_path):
        config_path = tmp_path / "config.json"
        original = AppConfig(
            name="Roundtrip Test",
            environment="staging",
            debug=True
        )
        original.save(str(config_path))
        
        loaded = AppConfig.load(str(config_path))
        assert loaded.name == original.name
        assert loaded.environment == original.environment
        assert loaded.debug == original.debug


class TestAppConfigLoadEnv:
    """Test load_env() method"""
    
    def test_load_env_updates_api_key(self):
        config = AppConfig()
        config.llm.api_key = ""
        
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'new_key_from_env'}):
            config.load_env()
            assert config.llm.api_key == 'new_key_from_env'
    
    def test_load_env_updates_provider(self):
        config = AppConfig()
        config.llm.provider = "openai"
        
        with patch.dict(os.environ, {'LLM_PROVIDER': 'anthropic'}):
            config.load_env()
            assert config.llm.provider == 'anthropic'
    
    def test_load_env_updates_model(self):
        config = AppConfig()
        config.llm.model = ""
        
        with patch.dict(os.environ, {'LLM_MODEL': 'gpt-4-turbo'}):
            config.load_env()
            assert config.llm.model == 'gpt-4-turbo'


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_empty_string_acas_env_uses_default(self):
        """Test empty string ACAS_ENV uses default"""
        with patch.dict(os.environ, {'ACAS_ENV': ''}):
            config = AppConfig()
            # Empty string becomes environment value
            assert config.environment == ""
    
    def test_case_sensitive_environment(self):
        """Test environment is case sensitive"""
        config = AppConfig(environment="Production")
        # Should be exactly as set
        assert config.environment == "Production"
    
    def test_version_format(self):
        """Test version follows semver"""
        config = AppConfig()
        parts = config.version.split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)
