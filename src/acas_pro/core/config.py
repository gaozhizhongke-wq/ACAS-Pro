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
from typing import Dict, List, Optional, Tuple, Any
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
    name: str = "acas_pro"  # database name
    path: str = ""
    host: str = "localhost"
    port: int = 5432
    user: str = ""  # username
    username: str = ""  # alias for user
    password: str = ""
    database: str = "acas_pro"
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    pool_recycle: int = 3600
    echo: bool = False
    
    def __post_init__(self) -> Any:
        if not self.path:
            self.path = str(Path.home() / ".acas-pro" / "data" / "acas_pro.db")
        # Ensure username and user are synced
        if self.user and not self.username:
            self.username = self.user
        elif self.username and not self.user:
            self.user = self.username


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
    
    def __post_init__(self) -> Any:
        if not self.secret_key:
            from ..core.secrets_manager import get_secrets_manager
            sm = get_secrets_manager()
            env_key = sm.get('secret_key')
            if env_key:
                self.secret_key = env_key
            else:
                key_file = Path.home() / ".acas-pro" / ".secret"
                if key_file.exists():
                    self.secret_key = key_file.read_text().strip()
                # NOTE: intentionally NO random fallback in production —
                # JWTManager._get_secret_key() raises ValueError instead,
                # forcing operator to provide ACAS_JWT_SECRET env var or _cfg().security.secret_key.
                # This prevents silent degraded security on misconfiguration.


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
    agent_mode: bool = True
    max_agent_steps: int = 10
    
    def __post_init__(self) -> Any:
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
    
    def __post_init__(self) -> Any:
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
        
        # Validate production secrets
        if self.environment == Environment.PRODUCTION:
            self._validate_production_secrets()
    
    def _validate_production_secrets(self) -> Any:
        """Production secrets validation - prevents startup with missing secrets"""
        missing = []
        
        # Check SECRET_KEY
        if not self.security.secret_key or len(self.security.secret_key) < 32:
            missing.append("SECRET_KEY (must be >= 32 chars)")
        
        # Check JWT_SECRET
        jwt_secret = os.environ.get('ACAS_JWT_SECRET', '')
        if not jwt_secret or len(jwt_secret) < 32:
            missing.append("ACAS_JWT_SECRET (must be >= 32 chars)")
        
        if missing:
            logger.error(f"Production secrets missing: {', '.join(missing)}")
            raise RuntimeError(f"Production secrets missing: {', '.join(missing)}")
    
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT
    
    def is_staging(self) -> bool:
        return self.environment == Environment.STAGING
    
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate configuration"""
        errors = []
        
        # Validate database
        if self.database.type not in ['sqlite', 'postgresql']:
            errors.append(f"Invalid database type: {self.database.type}")
        
        # Validate security
        if not self.security.secret_key:
            errors.append("SECRET_KEY is required")
        
        # Validate LLM
        if self.llm.enabled and not self.llm.api_key:
            errors.append("LLM API key is required when LLM is enabled")
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['environment'] = self.environment.value
        return data
    
    def save(self, path: Optional[str] = None) -> None:
        """Save configuration to file"""
        if path is None:
            path = str(Path.home() / ".acas-pro" / "config.json")
        
        config_path = Path(path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = self.to_dict()
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, path: Optional[str] = None) -> 'AppConfig':
        """Load configuration from file"""
        if path is None:
            path = str(Path.home() / ".acas-pro" / "config.json")
        
        config_path = Path(path)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            # Convert environment string back to enum
            if 'environment' in data:
                data['environment'] = Environment(data['environment'])
            
            # Convert nested dicts back to dataclasses
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
        
        return cls()


# Lazy-loaded global config instance
_config_instance: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get global config instance (lazy-loaded, DI-aware)"""
    global _config_instance
    if _config_instance is None:
        # Try DI container first
        from .di_container import get_container, DIContainer
        container = get_container()
        if container.is_registered(AppConfig):
            _config_instance = container.resolve(AppConfig)
        else:
            _config_instance = AppConfig.load()
            # Validate on load in production
            if _config_instance.is_production():
                is_valid, errors = _config_instance.validate()
                if not is_valid:
                    for error in errors:
                        logger.error(f"Production config validation failed: {error}")
    return _config_instance


def reset_config() -> None:
    """Reset the global config singleton (for testing)"""
    global _config_instance
    _config_instance = None


# Global singleton instance - use this directly
# Implemented as a module-level lazy accessor via __getattr__
# to avoid import-time side effects while maintaining backward compatibility.

def __getattr__(name) -> None:
    if name == 'config':
        return get_config()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Backward compatibility - config() function still works
def config_func() -> AppConfig:
    """Backward-compatible lazy config accessor - returns global singleton"""
    return get_config()
