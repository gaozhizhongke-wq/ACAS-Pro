#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Enterprise Logging
Structured logging with rotation and PII protection
"""

import sys
import json
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps

from .config import get_config

# Lazy-loaded config
def _get_config():
    return get_config()


class PIIRedactor:
    """PII (Personally Identifiable Information) redactor"""
    
    SENSITIVE_FIELDS = {
        'password', 'password_hash', 'secret', 'token', 'api_key',
        'credit_card', 'ssn', 'phone', 'email', 'address'
    }
    
    @classmethod
    def redact(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Redact sensitive fields from dict"""
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
    """JSON structured log formatter with request ID support"""
    
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
        
        # Add request ID for distributed tracing
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(PIIRedactor.redact(record.extra))
        
        # Add exception info
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            log_data["exception_type"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        
        return json.dumps(log_data, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter"""
    
    COLORS = {
        "DEBUG": "\033[36m",    # Cyan
        "INFO": "\033[32m",     # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",    # Red
        "CRITICAL": "\033[35m", # Magenta
        "RESET": "\033[0m"
    }
    
    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, self.COLORS["RESET"])
        reset = self.COLORS["RESET"]
        
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        return f"{color}[{timestamp}] [{record.levelname}] {record.name}: {record.getMessage()}{reset}"


def setup_logging():
    """Setup application logging"""
    
    # Create logger
    config = _get_config()
    logger = logging.getLogger("acas_pro")
    logger.setLevel(logging.DEBUG if config.debug else logging.INFO)
    
    # Remove existing handlers
    logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if config.debug else logging.INFO)
    console_handler.setFormatter(ConsoleFormatter())
    logger.addHandler(console_handler)
    
    # File handler with rotation
    log_file = Path(config.log_dir) / "acas.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(StructuredFormatter())
    logger.addHandler(file_handler)
    
    # Error file handler
    error_file = Path(config.log_dir) / "error.log"
    error_handler = logging.handlers.RotatingFileHandler(
        error_file,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(StructuredFormatter())
    logger.addHandler(error_handler)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """Get logger instance"""
    return logging.getLogger(f"acas_pro.{name}")


class AuditLogger:
    """Security audit logger"""
    
    def __init__(self):
        self.logger = get_logger("audit")
        self.db = None  # Will be set after import
    
    def log(self, event_type: str, user_id: str, details: Dict[str, Any], 
            ip_address: str = None, severity: str = "info"):
        """Log audit event"""
        
        # Log to file
        self.logger.info(
            f"AUDIT: {event_type}",
            extra={
                "extra": {
                    "event_type": event_type,
                    "user_id": user_id,
                    "details": PIIRedactor.redact(details),
                    "ip_address": ip_address,
                    "severity": severity
                }
            }
        )
        
        # Log to database
        try:
            if self.db is None:
                from .database import get_db
                self.db = get_db()
            
            self.db.execute("""
                INSERT INTO audit_log (timestamp, event_type, user_id, ip_address, details, severity)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(timezone.utc).isoformat(),
                event_type,
                user_id,
                ip_address,
                json.dumps(details, ensure_ascii=False),
                severity
            ))
        except Exception as e:
            self.logger.error(f"Failed to write audit log: {e}")


# Global instances
audit_logger = AuditLogger()

# Default logger (setup later by setup_logging, available for import)
logger = logging.getLogger("acas_pro")
