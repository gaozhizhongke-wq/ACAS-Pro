#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Secrets Manager
Centralized secret management with environment variable precedence.

Production: ALL secrets MUST come from environment variables.
Development: Falls back to .env file or config.json (with warnings).
"""

import os
from acas_pro.core.logging import get_logger
from typing import Optional

logger = get_logger(__name__)

# Secrets that must NEVER be stored in config.json or .env in production
_PRODUCTION_ENV_ONLY = {
    "ACAS_JWT_SECRET",
    "ACAS_ENCRYPTION_SALT",
    "LLM_API_KEY",
    "DEEPSEEK_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "DATABASE_PASSWORD",
    "SECRET_KEY",
}

# Map: logical secret name → environment variable name
_SECRET_ENV_MAP = {
    "jwt_secret": "ACAS_JWT_SECRET",
    "encryption_salt": "ACAS_ENCRYPTION_SALT",
    "llm_api_key": "LLM_API_KEY",
    "deepseek_api_key": "DEEPSEEK_API_KEY",
    "anthropic_api_key": "ANTHROPIC_API_KEY",
    "google_api_key": "GOOGLE_API_KEY",
    "database_password": "DATABASE_PASSWORD",
    "secret_key": "SECRET_KEY",
}


class SecretsManager:
    """
    Centralized secrets accessor with environment variable precedence.

    Resolution order:
      1. Environment variable (always wins)
      2. Explicitly passed fallback value
      3. None (secret not found)
    """

    def __init__(self, is_production: bool = False):
        self._is_production = is_production
        self._cache: dict = {}

    def get(self, name: str, fallback: Optional[str] = None) -> Optional[str]:
        """
        Retrieve a secret value.

        Args:
            name: Logical secret name (e.g. 'llm_api_key') or env var name
            fallback: Value to return if secret not found in env
        """
        # Resolve env var name
        env_key = _SECRET_ENV_MAP.get(name, name)

        # 1. Environment variable takes precedence
        value = os.environ.get(env_key)
        if value:
            return value

        # 2. Fallback value
        if fallback is not None:
            if self._is_production and env_key in _PRODUCTION_ENV_ONLY:
                logger.warning(
                    f"Secret '{name}' not set via env var {env_key} in production. "
                    f"Using fallback — this is insecure!"
                )
            return fallback

        # 3. Not found
        if self._is_production and env_key in _PRODUCTION_ENV_ONLY:
            logger.error(
                f"CRITICAL: Secret '{name}' ({env_key}) not configured in production!"
            )
        return None

    def require(self, name: str) -> str:
        """Get a secret or raise ValueError if missing."""
        value = self.get(name)
        if value is None:
            env_key = _SECRET_ENV_MAP.get(name, name)
            raise ValueError(
                f"Required secret '{name}' not found. "
                f"Set environment variable {env_key}."
            )
        return value

    def is_set(self, name: str) -> bool:
        """Check if a secret is configured."""
        return self.get(name) is not None

    def mask(self, value: str, visible: int = 4) -> str:
        """Mask a secret value for logging: sk-2f21...xxxx"""
        if not value or len(value) <= visible:
            return "***"
        return f"{value[:visible]}...{value[-visible:]}"

    def validate_production(self) -> list:
        """Return list of missing required secrets in production."""
        missing = []
        for name, env_key in _SECRET_ENV_MAP.items():
            if not os.environ.get(env_key):
                missing.append(f"{name} (env: {env_key})")
        return missing


# Lazy singleton
_instance: Optional[SecretsManager] = None


def get_secrets_manager(is_production: Optional[bool] = None) -> SecretsManager:
    """Get or create the global SecretsManager instance."""
    global _instance
    if _instance is None:
        if is_production is None:
            env = os.environ.get("ACAS_ENV", "development").lower()
            is_production = env == "production"
        _instance = SecretsManager(is_production=is_production)
    return _instance
