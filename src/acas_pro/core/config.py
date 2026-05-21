#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Enterprise Configuration
Production-grade configuration management with validation
"""

import os
import json
import secrets
import logging
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Application environment"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """Database configuration"""
    type: str = "sqlite"  # sqlite, postgresql
    path: str = ""
    host: str = "localhost"
    port: int = 5432
    name: str = "acas"
    user: str = ""
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    
    def __post_init__(self):
        if not self.path:
            self.path = str(Path.home() / ".acas-pro" / "data" / "acas.db")


@dataclass
class LLMConfig:
    """LLM configuration"""
    enabled: bool = True
    provider: str = "deepseek"  # deepseek, openai, anthropic, gemini
    api_key: str = ""
    model: str = "deepseek-chat"
    base_url: str = "https://api.deepseek.com"
    max_tokens: int = 4000
    temperature: float = 0.7

    def __post_init__(self):
        if not self.api_key:
            from ..core.secrets_manager import get_secrets_manager
            sm = get_secrets_manager()
            # Try provider-specific key first, then generic LLM_API_KEY
            provider_key = sm.get(f'{self.provider}_api_key')
            if provider_key:
                self.api_key = provider_key
            else:
                generic_key = sm.get('llm_api_key')
                if generic_key:
                    self.api_key = generic_key


@dataclass
class OAuthConfig:
    """OAuth configuration"""
    qq_app_id: str = ""
    qq_app_key: str = ""
    qq_redirect_uri: str = ""
    wechat_app_id: str = ""
    wechat_app_key: str = ""
    wechat_redirect_uri: str = ""


@dataclass
class SecurityConfig:
    """Security configuration"""
    secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    password_min_length: int = 8
    pbkdf2_iterations: int = 600000
    salt_length: int = 32
    session_timeout_minutes: int = 30
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    # HTTPS/TLS configuration
    enable_https: bool = False
    tls_cert_path: str = ""
    tls_key_path: str = ""
    # CORS configuration
    cors_allowed_origins: str = ""  # comma-separated
    
    def __post_init__(self):
        if not self.secret_key:
            # Try environment variable first via SecretsManager
            from ..core.secrets_manager import get_secrets_manager
            sm = get_secrets_manager()
            env_key = sm.get('secret_key')
            if env_key:
                self.secret_key = env_key
            else:
                key_file = Path.home() / ".acas-pro" / ".secret"
                if key_file.exists():
                    self.secret_key = key_file.read_text().strip()
                else:
                    self.secret_key = secrets.token_hex(32)
                    key_file.parent.mkdir(parents=True, exist_ok=True)
                    key_file.write_text(self.secret_key)
                    try:
                        os.chmod(key_file, 0o600)
                    except OSError:
                        pass


@dataclass
class MLConfig:
    """Machine Learning configuration"""
    timesfm_enabled: bool = True
    timesfm_context_length: int = 512
    timesfm_prediction_horizon: int = 30
    sentiment_enabled: bool = True
    news_refresh_interval_minutes: int = 15
    forecast_confidence_level: float = 0.8


@dataclass
class UIConfig:
    """UI configuration"""
    theme: str = "dark"
    language: str = "zh"
    font_family: str = "Microsoft YaHei"
    font_size: int = 10
    window_width: int = 1440
    window_height: int = 900
    sidebar_width: int = 260


@dataclass
class AppConfig:
    """Application configuration"""
    name: str = "ACAS Pro"
    version: str = "4.0.0"
    company: str = "ACAS Technology"
    data_dir: str = ""
    log_dir: str = ""
    backup_dir: str = ""
    debug: bool = False
    environment: Environment = Environment.DEVELOPMENT
    
    database: DatabaseConfig = None
    security: SecurityConfig = None
    ml: MLConfig = None
    ui: UIConfig = None
    llm: LLMConfig = None
    oauth: OAuthConfig = None
    
    def __post_init__(self):
        # ACAS_ENV always takes precedence over any other configuration
        env = os.environ.get('ACAS_ENV', '').lower()
        if env:
            try:
                self.environment = Environment(env)
                logger.info(f"Environment set from ACAS_ENV: {self.environment.value}")
            except ValueError:
                logger.warning(f"Invalid ACAS_ENV value: {env}, keeping current: {self.environment.value}")
        
        if not self.data_dir:
            self.data_dir = str(Path.home() / ".acas-pro" / "data")
        if not self.log_dir:
            self.log_dir = str(Path.home() / ".acas-pro" / "logs")
        if not self.backup_dir:
            self.backup_dir = str(Path.home() / ".acas-pro" / "backups")
        
        if self.database is None:
            self.database = DatabaseConfig()
        if self.security is None:
            self.security = SecurityConfig()
        if self.ml is None:
            self.ml = MLConfig()
        if self.ui is None:
            self.ui = UIConfig()
        if self.llm is None:
            self.llm = LLMConfig()
        if self.oauth is None:
            self.oauth = OAuthConfig()
        
        for d in [self.data_dir, self.log_dir, self.backup_dir]:
            Path(d).mkdir(parents=True, exist_ok=True)
    
    @property
    def is_production(self) -> bool:
        """Check if running in production"""
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_development(self) -> bool:
        """Check if running in development"""
        return self.environment == Environment.DEVELOPMENT
    
    @property
    def is_staging(self) -> bool:
        """Check if running in staging"""
        return self.environment == Environment.STAGING
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate configuration
        Returns (is_valid, error_messages)
        
        MUST be called at startup, especially in production
        """
        errors: List[str] = []
        
        # Production environment validations
        if self.environment == Environment.PRODUCTION:
            # Use SecretsManager to validate all required secrets
            from ..core.secrets_manager import get_secrets_manager
            sm = get_secrets_manager(is_production=True)
            missing = sm.validate_production()
            for m in missing:
                errors.append(f"Required secret not set: {m}")
            
            # Check secret key is not default/empty
            if not self.security.secret_key:
                errors.append("SECRET_KEY is not set in production")
            
            # Check JWT secret is set (via env or config)
            jwt_secret = os.environ.get('ACAS_JWT_SECRET')
            if not jwt_secret and not self.security.secret_key:
                errors.append("ACAS_JWT_SECRET environment variable is required in production")
            
            # Check encryption salt
            salt_env = os.environ.get('ACAS_ENCRYPTION_SALT')
            if not salt_env:
                errors.append("ACAS_ENCRYPTION_SALT environment variable is required in production")
            
            # Check database password for PostgreSQL
            if self.database.type == 'postgresql':
                if not self.database.password:
                    errors.append("PostgreSQL password must be set in production")
                if self.database.host == 'localhost':
                    errors.append("PostgreSQL host should not be localhost in production")
            # SQLite is not allowed in production
            if self.database.type == 'sqlite':
                errors.append("SQLite is not supported in production. Migrate to PostgreSQL and set DATABASE_URL environment variable.")


            
            # Check backup directory
            if not Path(self.backup_dir).exists():
                errors.append(f"Backup directory does not exist: {self.backup_dir}")
        
        # Development environment warnings
        if self.environment == Environment.DEVELOPMENT:
            if not self.security.secret_key:
                logger.warning("SECRET_KEY not set, using generated key (insecure for production)")
        
        # Security validations for all environments
        if self.security.password_min_length < 8:
            errors.append("Password minimum length must be at least 8")
        
        if self.security.pbkdf2_iterations < 100000:
            errors.append("PBKDF2 iterations must be at least 100,000 for security")
        
        # LLM validations
        if self.llm.enabled and not self.llm.api_key:
            if self.environment == Environment.PRODUCTION:
                errors.append("LLM API key must be configured in production")
            else:
                logger.warning("LLM enabled but no API key configured")
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    @classmethod
    def load(cls, path: Optional[str] = None) -> "AppConfig":
        """Load configuration from file"""
        if path is None:
            path = str(Path.home() / ".acas-pro" / "config.json")
        
        config_path = Path(path)
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Handle environment string from JSON
                if 'environment' in data:
                    if isinstance(data['environment'], str):
                        try:
                            data['environment'] = Environment(data['environment'])
                        except ValueError:
                            data['environment'] = Environment.DEVELOPMENT
                
                # Convert nested dicts to dataclass instances
                if 'database' in data and isinstance(data['database'], dict):
                    data['database'] = DatabaseConfig(**data['database'])
                if 'security' in data and isinstance(data['security'], dict):
                    data['security'] = SecurityConfig(**data['security'])
                if 'ml' in data and isinstance(data['ml'], dict):
                    data['ml'] = MLConfig(**data['ml'])
                if 'ui' in data and isinstance(data['ui'], dict):
                    data['ui'] = UIConfig(**data['ui'])
                if 'llm' in data and isinstance(data['llm'], dict):
                    data['llm'] = LLMConfig(**data['llm'])
                if 'oauth' in data and isinstance(data['oauth'], dict):
                    data['oauth'] = OAuthConfig(**data['oauth'])
                
                return cls(**data)
            except Exception as e:
                logger.warning(f'Config load error: {e}. Using defaults.')

        config = cls()
        config.save(path)
        return config
    
    def save(self, path: Optional[str] = None) -> None:
        """Save configuration to file"""
        if path is None:
            path = str(Path.home() / ".acas-pro" / "config.json")
        
        config_path = Path(path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = asdict(self)
        # Convert enum to string for JSON
        data['environment'] = self.environment.value
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# Lazy-loaded global config instance
_config_instance: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get global config instance (lazy-loaded)"""
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig.load()
        # Validate on load in production
        if _config_instance.is_production:
            is_valid, errors = _config_instance.validate()
            if not is_valid:
                for error in errors:
                    logger.error(f"Production config validation failed: {error}")
    return _config_instance


# Backward compatibility - deprecated, use get_config()
# LAZY initialization to avoid circular import
_config_lazy = None

def config() -> AppConfig:
    """Backward-compatible lazy config accessor"""
    global _config_lazy
    if _config_lazy is None:
        _config_lazy = get_config()
    return _config_lazy
