#!/usr/bin/env python3
"""
ACAS Pro — Domain Exception Hierarchy

All custom exceptions for the ACAS system, providing granular error
classification for structured error handling across modules.
"""

from __future__ import annotations


# ── Root ─────────────────────────────────────────────────────────────────


class ACASError(Exception):
    """Base for all ACAS-specific exceptions."""


class ACASDatabaseError(ACASError):
    """Database layer failure (connection, constraint, schema mismatch)."""


class ACASValidationError(ACASError):
    """Input validation failure (bad data, invalid state)."""


class ACASAuthError(ACASError):
    """Authentication / authorisation failure."""


class ACASConfigError(ACASError):
    """Configuration error (missing required env, invalid config)."""


class ACASNotFoundError(ACASError):
    """Requested resource not found."""


class ACASPlatformError(ACASError):
    """External platform API error."""


class ACASRateLimitError(ACASError):
    """Rate limit exceeded."""
