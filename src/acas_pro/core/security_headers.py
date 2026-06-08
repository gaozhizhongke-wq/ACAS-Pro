#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Security Headers Middleware
Production-grade security headers for Flask
"""

from flask import Flask, request, g
from functools import wraps
import re


class SecurityHeaders:
    """Security headers middleware for Flask applications.
    
    Generates a per-request nonce for CSP, replacing unsafe-inline with nonce-based policy.
    """
    
    # Base CSP template (no unsafe-inline or unsafe-eval)
    BASE_CSP = (
        "default-src 'self'; "
        "script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net; "
        "style-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https: blob:; "
        "connect-src 'self' https://api.deepseek.com https://api.openai.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    
    # Legacy CSP for templates that cannot use nonce (gradually migrate)
    LEGACY_CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https: blob:; "
        "connect-src 'self' https://api.deepseek.com https://api.openai.com; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )
    
    def __init__(self, app: Flask = None, 
                 use_nonce: bool = True,
                 hsts: bool = True,
                 hsts_max_age: int = 63072000):
        self.use_nonce = use_nonce
        self.hsts = hsts
        self.hsts_max_age = hsts_max_age
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask) -> None:
        """Initialize security headers for Flask app"""
        import secrets
        
        @app.after_request
        def add_security_headers(response) -> None:
            # Prevent MIME type sniffing
            response.headers['X-Content-Type-Options'] = 'nosniff'
            
            # Prevent clickjacking
            response.headers['X-Frame-Options'] = 'DENY'
            
            # XSS Protection (legacy but still useful)
            response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # Referrer Policy
            response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # Permissions Policy
            response.headers['Permissions-Policy'] = (
                'accelerometer=(), camera=(), geolocation=(), gyroscope=(), '
                'magnetometer=(), microphone=(), payment=(), usb=()'
            )
            
            # Content Security Policy
            if self.use_nonce:
                nonce = secrets.token_urlsafe(16)
                csp = self.BASE_CSP.format(nonce=nonce)
                response.headers['Content-Security-Policy'] = csp
            else:
                response.headers['Content-Security-Policy'] = self.LEGACY_CSP
            
            # HSTS (HTTPS Strict Transport Security)
            if self.hsts and request.is_secure:
                response.headers['Strict-Transport-Security'] = (
                    f'max-age={self.hsts_max_age}; includeSubDomains; preload'
                )
            
            # Remove server fingerprinting
            response.headers.pop('Server', None)
            
            return response
    
    _current_nonce: str = ''
    
    @classmethod
    def set_nonce(cls, nonce: str) -> None:
        cls._current_nonce = nonce
    
    @classmethod
    def get_nonce(cls) -> str:
        return cls._current_nonce


class InputValidator:
    """Input validation utilities"""
    
    # SQL injection patterns
    SQL_PATTERNS = [
        r'(--|#|//|/\*)',  # Comments
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',  # SQL keywords
        r'(\b(OR|AND)\b\s+\d+\s*=\s*\d+)',  # Boolean-based
        r'(;\s*\w+)',  # Stacked queries
    ]
    
    # XSS patterns
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',
        r'<iframe',
        r'<object',
        r'<embed',
    ]
    
    @classmethod
    def sanitize_sql(cls, value: str) -> str:
        """Basic SQL injection sanitization"""
        if not isinstance(value, str):
            return value
        
        # Remove null bytes
        value = value.replace('\x00', '')
        
        # Check for SQL patterns
        for pattern in cls.SQL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"Potential SQL injection detected: {value[:50]}")
        
        return value
    
    @classmethod
    def sanitize_html(cls, value: str) -> str:
        """Basic XSS sanitization"""
        if not isinstance(value, str):
            return value
        
        for pattern in cls.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                raise ValueError(f"Potential XSS detected: {value[:50]}")
        
        return value
    
    @classmethod
    def validate_email(cls, email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @classmethod
    def validate_phone(cls, phone: str) -> bool:
        """Validate Chinese phone number"""
        pattern = r'^1[3-9]\d{9}$'
        return bool(re.match(pattern, phone))


def require_https(f) -> None:
    """Decorator to require HTTPS for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs) -> None:
        if not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
            return {'error': 'HTTPS required'}, 403
        return f(*args, **kwargs)
    return decorated_function


def rate_limit_by_ip(max_requests: int = 100, window_seconds: int = 60) -> None:
    """Rate limiter by IP using module-level storage with auto-cleanup."""
    import time as _time
    _rate_store: dict = {}
    _last_cleanup = 0.0

    def decorator(f) -> None:
        @wraps(f)
        def decorated_function(*args, **kwargs) -> None:
            nonlocal _last_cleanup
            now = _time.time()
            
            # Auto-cleanup old entries every 60s
            if now - _last_cleanup > 60:
                _rate_store.clear()
                _last_cleanup = now
            
            ip = request.remote_addr
            key = f"rate_limit:{ip}:{f.__name__}"
            
            if key not in _rate_store:
                _rate_store[key] = []
            
            # Clean expired entries for this key
            _rate_store[key] = [t for t in _rate_store[key] if now - t < window_seconds]
            
            if len(_rate_store[key]) >= max_requests:
                return {'error': 'Rate limit exceeded'}, 429
            
            _rate_store[key].append(now)
            return f(*args, **kwargs)
        return decorated_function
    return decorator
