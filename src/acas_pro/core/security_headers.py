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
    """Security headers middleware for Flask applications"""
    
    DEFAULT_CSP = (
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
                 csp: str = None,
                 hsts: bool = True,
                 hsts_max_age: int = 63072000):
        self.csp = csp or self.DEFAULT_CSP
        self.hsts = hsts
        self.hsts_max_age = hsts_max_age
        
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize security headers for Flask app"""
        
        @app.after_request
        def add_security_headers(response):
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
            response.headers['Content-Security-Policy'] = self.csp
            
            # HSTS (HTTPS Strict Transport Security)
            if self.hsts and request.is_secure:
                response.headers['Strict-Transport-Security'] = (
                    f'max-age={self.hsts_max_age}; includeSubDomains; preload'
                )
            
            # Remove server fingerprinting
            response.headers.pop('Server', None)
            
            return response


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


def require_https(f):
    """Decorator to require HTTPS for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.is_secure and request.headers.get('X-Forwarded-Proto') != 'https':
            return {'error': 'HTTPS required'}, 403
        return f(*args, **kwargs)
    return decorated_function


def rate_limit_by_ip(max_requests: int = 100, window_seconds: int = 60):
    """Simple rate limiter by IP (uses Flask g object)"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Note: This is a simple implementation
            # For production, use Redis-based rate limiting
            ip = request.remote_addr
            key = f"rate_limit:{ip}:{f.__name__}"
            
            # Check if rate limit exceeded (using simple in-memory store)
            if not hasattr(g, '_rate_limits'):
                g._rate_limits = {}
            
            import time
            now = time.time()
            
            if key not in g._rate_limits:
                g._rate_limits[key] = []
            
            # Clean old entries
            g._rate_limits[key] = [t for t in g._rate_limits[key] if now - t < window_seconds]
            
            if len(g._rate_limits[key]) >= max_requests:
                return {'error': 'Rate limit exceeded'}, 429
            
            g._rate_limits[key].append(now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator
