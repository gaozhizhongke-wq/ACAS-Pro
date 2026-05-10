#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Enterprise Configuration
Production-grade configuration management
"""

import os
import json
import secrets
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional


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
        # Priority: environment variable > file > generate
        env_secret = os.environ.get('ACAS_SECRET_KEY')
        if env_secret:
            self.secret_key = env_secret
            return
            
        if not self.secret_key:
            # Generate or load from secure storage
            key_file = Path.home() / ".acas-pro" / ".secret"
            if key_file.exists():
                self.secret_key = key_file.read_text().strip()
            else:
                self.secret_key = secrets.token_hex(32)
                key_file.parent.mkdir(parents=True, exist_ok=True)
                key_file.write_text(self.secret_key)
                os.chmod(key_file, 0o600)


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
class LLMConfig:
    """LLM (Large Language Model) configuration"""
    enabled: bool = False
    provider: str = "openai"  # openai, anthropic, kimi, deepseek, qwen, lmstudio, ollama, custom
    api_key: str = ""
    api_base: str = ""  # Custom API endpoint
    model: str = ""  # Model name
    max_tokens: int = 4096
    temperature: float = 0.7
    top_p: float = 0.9
    agent_mode: bool = True  # Enable autonomous agent mode
    max_agent_steps: int = 10
    context_window: int = 8192
    
    def get_default_model(self) -> str:
        """Get default model for provider"""
        defaults = {
            "openai": "gpt-4o",
            "anthropic": "claude-sonnet-4-20250514",
            "kimi": "moonshot-v1-128k",
            "deepseek": "deepseek-chat",
            "qwen": "qwen-max",
            "lmstudio": "local-model",
            "ollama": "llama3",
            "custom": ""
        }
        return defaults.get(self.provider, "")


@dataclass
class OAuthConfig:
    """OAuth Third-party Login Configuration"""
    # QQ 互联
    qq_enabled: bool = False
    qq_app_id: str = ""
    qq_app_key: str = ""
    qq_redirect_uri: str = "https://acas-pro.com/oauth/callback/qq"
    # 微信开放平台
    wechat_enabled: bool = False
    wechat_app_id: str = ""
    wechat_app_secret: str = ""
    wechat_redirect_uri: str = "https://acas-pro.com/oauth/callback/wechat"


@dataclass
class AlertConfig:
    """Alert Notification Configuration"""
    # WeChat Work (企业微信)
    wechat_work_webhook: str = ""
    # DingTalk (钉钉)
    dingtalk_webhook: str = ""
    # Feishu (飞书)
    feishu_webhook: str = ""
    # Email SMTP
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_email_recipients: str = ""  # comma-separated
    # Custom webhook
    alert_webhook_url: str = ""
    # Thresholds
    critical_score_threshold: int = 60
    warning_score_threshold: int = 70
    negative_ratio_threshold: float = 0.3


@dataclass
class WorldMonitorConfig:
    """WorldMonitor (舆情监测) Configuration"""
    # RSS refresh interval (minutes)
    rss_refresh_interval: int = 15
    # Weibo API
    weibo_app_key: str = ""
    weibo_access_token: str = ""
    # Sentiment analysis
    sentiment_model: str = "rule"  # rule, bert, gpt
    # Alert channels
    alert_channels: str = "wechat_work"  # comma-separated: wechat_work,dingtalk,feishu,email
    # Keywords to monitor
    monitor_keywords: str = ""  # comma-separated

@dataclass
class AppConfig:
    """Application configuration"""
    name: str = "ACAS Pro"
    version: str = "5.2.0"
    company: str = "ACAS Technology"
    # Environment: development, staging, production
    environment: str = "development"
    data_dir: str = ""
    log_dir: str = ""
    backup_dir: str = ""
    debug: bool = False
    
    database: DatabaseConfig = None
    security: SecurityConfig = None
    ml: MLConfig = None
    ui: UIConfig = None
    llm: LLMConfig = None
    oauth: OAuthConfig = None
    alert: AlertConfig = None
    worldmonitor: WorldMonitorConfig = None
    
    def __post_init__(self):
        # Load environment from ACAS_ENV
        env = os.environ.get('ACAS_ENV', 'development')
        if self.environment == 'development':  # Only override if not explicitly set
            self.environment = env
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
        if self.alert is None:
            self.alert = AlertConfig()
        if self.worldmonitor is None:
            self.worldmonitor = WorldMonitorConfig()
        
        # Load LLM configuration from environment variables
        self._load_llm_from_env()
        
        # Ensure directories exist
        for d in [self.data_dir, self.log_dir, self.backup_dir]:
            Path(d).mkdir(parents=True, exist_ok=True)
    
    def _load_llm_from_env(self):
        """Load LLM configuration from environment variables"""
        # Check for DeepSeek
        deepseek_key = os.environ.get('DEEPSEEK_API_KEY')
        if deepseek_key:
            self.llm.enabled = True
            self.llm.provider = 'deepseek'
            self.llm.api_key = deepseek_key
            self.llm.api_base = os.environ.get('DEEPSEEK_API_BASE', 'https://api.deepseek.com/v1')
            self.llm.model = os.environ.get('DEEPSEEK_MODEL', 'deepseek-chat')
            return
        
        # Check for OpenAI
        openai_key = os.environ.get('OPENAI_API_KEY')
        if openai_key:
            self.llm.enabled = True
            self.llm.provider = 'openai'
            self.llm.api_key = openai_key
            self.llm.api_base = os.environ.get('OPENAI_API_BASE', 'https://api.openai.com/v1')
            self.llm.model = os.environ.get('OPENAI_MODEL', 'gpt-4o-mini')
            return
        
        # Check for Anthropic
        anthropic_key = os.environ.get('ANTHROPIC_API_KEY')
        if anthropic_key:
            self.llm.enabled = True
            self.llm.provider = 'anthropic'
            self.llm.api_key = anthropic_key
            self.llm.api_base = os.environ.get('ANTHROPIC_API_BASE', 'https://api.anthropic.com/v1')
            self.llm.model = os.environ.get('ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
            return
        
        # Check for Qwen
        qwen_key = os.environ.get('QWEN_API_KEY')
        if qwen_key:
            self.llm.enabled = True
            self.llm.provider = 'qwen'
            self.llm.api_key = qwen_key
            self.llm.api_base = os.environ.get('QWEN_API_BASE', 'https://dashscope.aliyuncs.com/compatible-mode/v1')
            self.llm.model = os.environ.get('QWEN_MODEL', 'qwen-max')
            return
        
        # Check for Kimi
        kimi_key = os.environ.get('KIMI_API_KEY')
        if kimi_key:
            self.llm.enabled = True
            self.llm.provider = 'kimi'
            self.llm.api_key = kimi_key
            self.llm.api_base = os.environ.get('KIMI_API_BASE', 'https://api.moonshot.cn/v1')
            self.llm.model = os.environ.get('KIMI_MODEL', 'moonshot-v1-128k')
            return
        
        # Check for LLM_PROVIDER override
        llm_provider = os.environ.get('LLM_PROVIDER')
        if llm_provider:
            self.llm.provider = llm_provider
            self.llm.enabled = True
        
        # Load other LLM settings from env
        if os.environ.get('LLM_MAX_TOKENS'):
            self.llm.max_tokens = int(os.environ.get('LLM_MAX_TOKENS'))
        if os.environ.get('LLM_TEMPERATURE'):
            self.llm.temperature = float(os.environ.get('LLM_TEMPERATURE'))
        if os.environ.get('LLM_TOP_P'):
            self.llm.top_p = float(os.environ.get('LLM_TOP_P'))
        if os.environ.get('LLM_AGENT_MODE'):
            self.llm.agent_mode = os.environ.get('LLM_AGENT_MODE').lower() == 'true'
        if os.environ.get('LLM_MAX_AGENT_STEPS'):
            self.llm.max_agent_steps = int(os.environ.get('LLM_MAX_AGENT_STEPS'))
    
    def validate(self) -> List[str]:
        """
        Validate configuration
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Security validation
        if not self.security.secret_key:
            errors.append("security.secret_key is required")
        elif len(self.security.secret_key) < 32:
            errors.append("security.secret_key must be at least 32 characters")
        
        
        # Database validation
        if self.database.type == 'postgresql':
            if not self.database.host:
                errors.append("database.host is required for PostgreSQL")
            if not self.database.name:
                errors.append("database.name is required for PostgreSQL")
            if not self.database.user:
                errors.append("database.user is required for PostgreSQL")
        
        
        # LLM validation (if enabled)
        if self.llm.enabled:
            if not self.llm.provider:
                errors.append("llm.provider is required when LLM is enabled")
            if not self.llm.api_key and self.llm.provider not in ['ollama', 'lmstudio']:
                errors.append(f"llm.api_key is required for provider '{self.llm.provider}'")
        
        
        # OAuth validation (if enabled)
        if self.oauth.qq_enabled:
            if not self.oauth.qq_app_id or not self.oauth.qq_app_key:
                errors.append("oauth.qq_app_id and qq_app_key are required when QQ OAuth is enabled")
        if self.oauth.wechat_enabled:
            if not self.oauth.wechat_app_id or not self.oauth.wechat_app_secret:
                errors.append("oauth.wechat_app_id and wechat_app_secret are required when WeChat OAuth is enabled")
        
        
        # Production-specific validations
        if self.environment == 'production':
            if not self.security.enable_https:
                errors.append("[PRODUCTION] security.enable_https must be True")
            if self.debug:
                errors.append("[PRODUCTION] debug must be False")
            if self.database.type == 'sqlite':
                errors.append("[PRODUCTION] PostgreSQL is recommended over SQLite")
        
        
        return errors
    
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
                # Reconstruct nested dataclasses
                return cls(
                    name=data.get('name', 'ACAS Pro'),
                    version=data.get('version', '4.0.0'),
                    company=data.get('company', 'ACAS Technology'),
                    data_dir=data.get('data_dir', ''),
                    log_dir=data.get('log_dir', ''),
                    backup_dir=data.get('backup_dir', ''),
                    debug=data.get('debug', False),
                    database=DatabaseConfig(**data.get('database', {})),
                    security=SecurityConfig(**data.get('security', {})),
                    ml=MLConfig(**data.get('ml', {})),
                    ui=UIConfig(**data.get('ui', {})),
                    llm=LLMConfig(**data.get('llm', {})),
                    oauth=OAuthConfig(**data.get('oauth', {})),
                    alert=AlertConfig(**data.get('alert', {})),
                    worldmonitor=WorldMonitorConfig(**data.get('worldmonitor', {}))
                )
            except Exception as e:
                import logging
                logging.warning(f'Failed to load config from {path}: {e}. Using defaults.')

        # Create default config
        config = cls()
        config.save(path)
        return config

    def save(self, path: Optional[str] = None) -> None:
        """Save configuration to file — sensitive fields are redacted."""
        if path is None:
            path = str(Path.home() / ".acas-pro" / "config.json")

        config_path = Path(path)
        config_path.parent.mkdir(parents=True, exist_ok=True)

        def _redact(obj):
            """Recursively redact sensitive values (field names containing key/secret/token/password/uri)."""
            if isinstance(obj, dict):
                result = {}
                for k, v in obj.items():
                    if any(p in k.lower() for p in ('key', 'secret', 'token', 'password', 'uri')):
                        result[k] = '***REDACTED***'
                    else:
                        result[k] = _redact(v)
                return result
            elif isinstance(obj, list):
                return [_redact(item) for item in obj]
            else:
                return obj

        data = _redact(asdict(self))
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def load_env(self) -> "AppConfig":
        """Reload LLM/security keys from environment variables (secrets never written to disk)."""
        # Re-read env vars so running processes pick up .env changes
        for key in ('OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'KIMI_API_KEY',
                    'DEEPSEEK_API_KEY', 'DASHSCOPE_API_KEY', 'GOOGLE_API_KEY',
                    'LLM_API_KEY', 'LLM_PROVIDER', 'LLM_MODEL'):
            val = os.environ.get(key)
            if val:
                if 'KEY' in key:
                    self.llm.api_key = val
                if 'PROVIDER' in key:
                    self.llm.provider = val
                if 'MODEL' in key:
                    self.llm.model = val
        return self


# Global config instance
config = AppConfig.load()
