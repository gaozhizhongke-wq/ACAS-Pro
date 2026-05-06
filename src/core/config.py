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
    
    def __post_init__(self):
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
class AppConfig:
    """Application configuration"""
    name: str = "ACAS Pro"
    version: str = "4.0.0"
    company: str = "ACAS Technology"
    data_dir: str = ""
    log_dir: str = ""
    backup_dir: str = ""
    debug: bool = False
    
    database: DatabaseConfig = None
    security: SecurityConfig = None
    ml: MLConfig = None
    ui: UIConfig = None
    
    def __post_init__(self):
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
        
        # Ensure directories exist
        for d in [self.data_dir, self.log_dir, self.backup_dir]:
            Path(d).mkdir(parents=True, exist_ok=True)
    
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
                return cls(**data)
            except Exception:
                pass
        
        # Create default config
        config = cls()
        config.save(path)
        return config
    
    def save(self, path: Optional[str] = None) -> None:
        """Save configuration to file"""
        if path is None:
            path = str(Path.home() / ".acas-pro" / "config.json")
        
        config_path = Path(path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)


# Global config instance
config = AppConfig.load()
