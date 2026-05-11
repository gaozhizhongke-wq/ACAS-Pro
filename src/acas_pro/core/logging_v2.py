"""
ACAS Pro - Logging v2
Testable logging with dependency injection
"""

import sys
import json
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from .config_v2 import AppConfig


class PIIRedactor:
    """PII redactor"""
    
    SENSITIVE_FIELDS = {
        'password', 'password_hash', 'secret', 'token', 'api_key',
        'credit_card', 'ssn', 'phone', 'email', 'address'
    }
    
    @classmethod
    def redact(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive fields"""
        if not isinstance(data, dict):
            return data
        
        result = {}
        for key, value in data.items():
            key_lower = key.lower()
            if any(sf in key_lower for sf in cls.SENSITIVE_FIELDS):
                result[key] = "***REDACTED***"
            elif isinstance(value, dict):
                result[key] = cls.redact(value)
            elif isinstance(value, list):
                result[key] = [cls.redact(item) if isinstance(item, dict) else item for item in value]
            else:
                result[key] = value
        return result


class StructuredFormatter(logging.Formatter):
    """JSON structured formatter"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if hasattr(record, "extra"):
            log_data.update(PIIRedactor.redact(record.extra))
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Console formatter with colors"""
    
    COLORS = {
        "DEBUG": "\033[36m",
        "INFO": "\033[32m",
        "WARNING": "\033[33m",
        "ERROR": "\033[31m",
        "CRITICAL": "\033[35m",
        "RESET": "\033[0m"
    }
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        return f"{color}[{timestamp}] [{record.levelname}] {record.name}: {record.getMessage()}{reset}"


class LoggerFactory:
    """Logger factory with DI"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load()
        self._setup = False
    
    def setup(self) -> logging.Logger:
        """Setup logging"""
        if self._setup:
            return logging.getLogger("acas_pro")
        
        logger = logging.getLogger("acas_pro")
        logger.setLevel(logging.DEBUG if self.config.debug else logging.INFO)
        logger.handlers = []
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG if self.config.debug else logging.INFO)
        console_handler.setFormatter(ConsoleFormatter())
        logger.addHandler(console_handler)
        
        # File handler
        log_file = Path(self.config.log_dir) / "acas.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=10, encoding="utf-8"
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(StructuredFormatter())
        logger.addHandler(file_handler)
        
        self._setup = True
        return logger
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get named logger"""
        self.setup()
        return logging.getLogger(f"acas_pro.{name}")


# Factory function
def create_logger_factory(config: Optional[AppConfig] = None) -> LoggerFactory:
    return LoggerFactory(config)


def get_logger(name: str, config: Optional[AppConfig] = None) -> logging.Logger:
    """Get logger"""
    factory = create_logger_factory(config)
    return factory.get_logger(name)
