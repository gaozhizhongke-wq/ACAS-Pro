"""
ACAS Pro - Configuration v2
Pure dataclass with no side effects
"""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple
from enum import Enum


class Environment(str, Enum):
    """Application environment"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """Database configuration"""
    type: str = "sqlite"
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
    jwt_secret: str = ""
    encryption_salt: str = ""
    password_min_length: int = 8
    pbkdf2_iterations: int = 100000
    session_timeout: int = 3600
    max_login_attempts: int = 5
    lockout_duration: int = 900


@dataclass
class LLMConfig:
    """LLM configuration"""
    enabled: bool = True
    provider: str = "deepseek"
    api_key: str = ""
    model: str = "deepseek-chat"
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout: int = 30


@dataclass
class AppConfig:
    """Application configuration - pure dataclass, no side effects"""
    
    # Environment
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = True
    version: str = "2.0.0"
    
    # Paths
    data_dir: str = field(default_factory=lambda: str(Path.home() / ".acas-pro" / "data"))
    log_dir: str = field(default_factory=lambda: str(Path.home() / ".acas-pro" / "logs"))
    backup_dir: str = field(default_factory=lambda: str(Path.home() / ".acas-pro" / "backups"))
    
    # Sub-configs
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    
    # Features
    features: Dict[str, bool] = field(default_factory=dict)
    
    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate configuration"""
        errors = []
        
        if self.is_production:
            if not self.security.secret_key:
                errors.append("SECRET_KEY required in production")
            if not self.security.jwt_secret:
                errors.append("JWT_SECRET required in production")
        
        if self.security.password_min_length < 8:
            errors.append("Password min length must be >= 8")
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['environment'] = self.environment.value
        return data
    
    @classmethod
    def load(cls, path: Optional[str] = None) -> "AppConfig":
        """Load from file or environment"""
        # Load from environment
        env = os.environ.get('ACAS_ENV', 'development')
        try:
            environment = Environment(env)
        except ValueError:
            environment = Environment.DEVELOPMENT
        
        config = cls(environment=environment)
        
        # Load from file if exists
        if path is None:
            path = str(Path.home() / ".acas-pro" / "config.json")
        
        config_path = Path(path)
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                # Update from file data
                if 'environment' in data:
                    config.environment = Environment(data['environment'])
                
                return config
            except Exception as e:
                import logging; logging.getLogger(__name__).error("Unhandled exception: " + str(e))
                import logging
                logging.getLogger(__name__).warning(f"Failed to load config from {config_path}: {e}")
        
        return config
    
    def save(self, path: Optional[str] = None) -> None:
        """Save to file"""
        if path is None:
            path = str(Path.home() / ".acas-pro" / "config.json")
        
        config_path = Path(path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = self.to_dict()
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


# Factory function for DI container
def create_config() -> AppConfig:
    """Create configuration instance"""
    return AppConfig.load()
