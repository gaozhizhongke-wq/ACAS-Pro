# -*- coding: utf-8 -*-
"""
ACAS Pro - Security Layer
OWASP-inspired protection: SQL injection, XSS, CSRF
"""

import re
import html
from functools import wraps
from typing import Optional, Any, Callable
from flask import request, g, abort
from acas_pro.core.logging import get_logger

logger = get_logger(__name__)


# ============== SQL Injection Prevention ==============

# Dangerous SQL keywords that should not appear in user input
SQL_KEYWORDS = [
    'union', 'select', 'insert', 'delete', 'update', 'drop', 'create',
    'alter', 'exec', 'execute', 'script', 'truncate', 'into', 'load_file',
    'outfile', 'dumpfile', 'sleep', 'benchmark', 'waitfor', 'delay',
    'xp_cmdshell', 'sp_configure', 'sp_oamethod', 'sp_oacreate'
]

# SQL injection patterns
SQL_PATTERNS = [
    r"(\%27)|(\')|(\-\-)|(\%23)|(#)",  # single quote, comment
    r"((\%3D)|(=))[^\n]*((\%27)|(\')|(\-\-)|(\%3B)|(;))",  # equal + quote/comment
    r"\w*((\%27)|(\'))((\%6F)|o|(\%4F))((\%72)|r|(\%52))",  # 'or'
    r"((\%27)|(\'))union",  # 'union
    r"exec(\s|\+)+(s|x)p\w+",  # exec xp
    r"UNION\s+SELECT",  # UNION SELECT
    r";\s*DROP\s+TABLE",  # ; DROP TABLE
    r";\s*DELETE\s+FROM",  # ; DELETE FROM
]

SQL_INJECTION_RE = re.compile('|'.join(SQL_PATTERNS), re.IGNORECASE)


def sanitize_sql_input(value: str) -> str:
    """Sanitize user input for SQL queries"""
    if not value:
        return value
    
    # Check for SQL injection patterns
    if SQL_INJECTION_RE.search(value):
        logger.warning(f"SQL injection attempt detected: {value[:100]}")
        raise ValueError("Invalid input: contains SQL injection patterns")
    
    # Escape single quotes (defense in depth)
    value = value.replace("'", "''")
    
    return value


def validate_sql_param(param: Any) -> Any:
    """Validate parameter before SQL execution"""
    if isinstance(param, str):
        return sanitize_sql_input(param)
    elif isinstance(param, (int, float, bool)):
        return param
    elif param is None:
        return None
    elif isinstance(param, (list, tuple)):
        return [validate_sql_param(p) for p in param]
    else:
        return str(param)


# ============== XSS Prevention ==============

XSS_PATTERNS = [
    r"<script[^>]*>[\s\S]*?</script>",  # <script> tags
    r"javascript:",  # javascript: protocol
    r"on\w+\s*=",  # event handlers: onclick=, onload=, etc.
    r"<iframe[^>]*>",  # <iframe>
    r"<object[^>]*>",  # <object>
    r"<embed[^>]*>",  # <embed>
    r"<form[^>]*>",  # <form>
    r"<input[^>]*type\s*=\s*['\"]?hidden['\"]?",  # hidden input
]

XSS_RE = re.compile('|'.join(XSS_PATTERNS), re.IGNORECASE)


def sanitize_html(value: str) -> str:
    """Sanitize HTML content - escape all HTML tags"""
    if not value:
        return value
    return html.escape(value)


def sanitize_xss(value: str) -> str:
    """Sanitize user input for XSS prevention"""
    if not value:
        return value
    
    # Check for XSS patterns
    if XSS_RE.search(value):
        logger.warning(f"XSS attempt detected: {value[:100]}")
        # Remove/escape dangerous content
        value = re.sub(r'<script[^>]*>[\s\S]*?</script>', '', value, flags=re.IGNORECASE)
        value = re.sub(r'javascript:', '', value, flags=re.IGNORECASE)
        value = re.sub(r'on\w+\s*=', '', value, flags=re.IGNORECASE)
    
    # Escape HTML entities
    return html.escape(value)


def sanitize_json_value(value: Any) -> Any:
    """Recursively sanitize values in JSON data"""
    if isinstance(value, str):
        return sanitize_xss(value)
    elif isinstance(value, dict):
        return {k: sanitize_json_value(v) for k, v in value.items()}
    elif isinstance(value, list):
        return [sanitize_json_value(v) for v in value]
    return value


# ============== CSRF Protection ==============

class CSRFProtection:
    """CSRF token protection"""
    
    @staticmethod
    def generate_token() -> str:
        """Generate CSRF token"""
        import secrets
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def validate_token(request_token: str, session_token: str) -> bool:
        """Validate CSRF token"""
        if not request_token or not session_token:
            return False
        return secrets.compare_digest(request_token, session_token)


# ============== Security Decorators ==============

def require_csrf_token(f: Callable) -> Callable:
    """Decorator to require CSRF token for POST/PUT/DELETE requests"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method in ('POST', 'PUT', 'DELETE', 'PATCH'):
            token = request.headers.get('X-CSRF-Token') or request.form.get('csrf_token')
            session_token = g.get('csrf_token')
            
            if not token or not session_token:
                logger.warning("CSRF token missing")
                abort(403, "CSRF token required")
            
            if not CSRFProtection.validate_token(token, session_token):
                logger.warning("CSRF token invalid")
                abort(403, "Invalid CSRF token")
        
        return f(*args, **kwargs)
    return decorated_function


def sanitize_input(*fields: str) -> Callable:
    """Decorator to sanitize specific input fields"""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.is_json:
                data = request.get_json(silent=True) or {}
                for field in fields:
                    if field in data and isinstance(data[field], str):
                        data[field] = sanitize_xss(data[field])
                g.sanitized_data = data
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def prevent_sql_injection(f: Callable) -> Callable:
    """Decorator to check request for SQL injection patterns"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check query parameters
        for key, value in request.args.items():
            if isinstance(value, str) and SQL_INJECTION_RE.search(value):
                logger.warning(f"SQL injection in query param: {key}")
                abort(400, "Invalid input detected")
        
        # Check JSON body
        if request.is_json:
            data = request.get_json(silent=True) or {}
            _check_sql_injection_recursive(data)
        
        return f(*args, **kwargs)
    return decorated_function


def _check_sql_injection_recursive(data: Any, path: str = ""):
    """Recursively check for SQL injection in data"""
    if isinstance(data, str):
        if SQL_INJECTION_RE.search(data):
            logger.warning(f"SQL injection at path: {path}")
            abort(400, "Invalid input detected")
    elif isinstance(data, dict):
        for key, value in data.items():
            _check_sql_injection_recursive(value, f"{path}.{key}")
    elif isinstance(data, list):
        for i, item in enumerate(data):
            _check_sql_injection_recursive(item, f"{path}[{i}]")


# ============== Security Headers ==============

SECURITY_HEADERS = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'DENY',
    'X-XSS-Protection': '1; mode=block',
    'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
    'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'",
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Permissions-Policy': 'geolocation=(), microphone=(), camera=()',
}


def add_security_headers(response) -> Any:
    """Add security headers to response"""
    for header, value in SECURITY_HEADERS.items():
        response.headers[header] = value
    return response


# ============== Rate Limiting Enhancement ==============

class RateLimiter:
    """Enhanced rate limiter with IP tracking"""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests = {}  # {key: [(timestamp, count)]}
    
    def is_allowed(self, key: str) -> bool:
        """Check if request is allowed"""
        import time
        now = time.time()
        
        # Clean old entries
        if key in self._requests:
            self._requests[key] = [
                (ts, cnt) for ts, cnt in self._requests[key]
                if now - ts < self.window_seconds
            ]
        
        # Count requests in window
        if key not in self._requests:
            self._requests[key] = []
        
        total = sum(cnt for ts, cnt in self._requests[key])
        
        if total >= self.max_requests:
            logger.warning(f"Rate limit exceeded for: {key}")
            return False
        
        # Record request
        self._requests[key].append((now, 1))
        return True
    
    def get_remaining(self, key: str) -> int:
        """Get remaining requests"""
        import time
        now = time.time()
        
        if key not in self._requests:
            return self.max_requests
        
        total = sum(cnt for ts, cnt in self._requests[key] if now - ts < self.window_seconds)
        return max(0, self.max_requests - total)


# Global rate limiter instance
rate_limiter = RateLimiter()
