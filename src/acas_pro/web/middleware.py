"""ACAS Pro Web - Middleware

Request tracking, logging, and utility middleware for production.
"""
import uuid
import time
from typing import Any
from flask import request, g, jsonify
from functools import wraps
from acas_pro.core.logging import get_logger

logger = get_logger(__name__)


# Paths that do NOT require authentication
PUBLIC_PATHS = frozenset({
    '/health',
    '/api/health',
    '/api/auth/login',
    '/api/auth/register',
    '/api/docs',
    '/api/spec',
    '/favicon.ico',
})

# Path prefixes that do NOT require authentication
PUBLIC_PREFIXES = (
    '/static/',
)


class RequestContext:
    """Request context manager for tracking, logging, and authentication"""
    
    @staticmethod
    def init_app(app) -> None:
        """Initialize request context middleware"""
        
        @app.before_request
        def before_request() -> Any:
            # Generate request ID
            g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4())[:16])
            g.start_time = time.time()
            
            # Store client info
            g.client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
            g.user_agent = request.headers.get('User-Agent', 'Unknown')[:200]
            
            # ── Authentication check ─────────────────────────────
            g.user = None  # Default: unauthenticated
            
            path = request.path
            
            # Skip auth for public paths
            if path in PUBLIC_PATHS or any(path.startswith(p) for p in PUBLIC_PREFIXES):
                return None  # Continue without auth
            
            # Skip auth for OPTIONS (CORS preflight)
            if request.method == 'OPTIONS':
                return None
            
            # Extract token from Authorization header or cookie
            token = None
            auth_header = request.headers.get('Authorization', '')
            if auth_header.startswith('Bearer '):
                token = auth_header[7:].strip()
            elif not token:
                token = request.cookies.get('access_token')
            
            if token:
                try:
                    import acas_pro.core.security as _sec
                    payload = _sec.JWTManager.verify_token(token)
                    if payload and 'sub' in payload:
                        g.user = {
                            'user_id': payload['sub'],
                            'account': payload.get('account', ''),
                        }
                except Exception as e:
                    logger.debug(f"Token verification failed: {e}")
            
            # If this is a public path (dashboard HTML page), allow without auth
            # but API endpoints and /metrics require authentication
            requires_auth = (
                path.startswith('/api/') and not path.startswith('/api/auth/')
            ) or path == '/metrics'
            if requires_auth and g.user is None:
                logger.warning(f"Unauthenticated API access: {request.method} {path}")
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Provide a valid JWT token via Authorization header',
                    'request_id': g.get('request_id')
                }), 401
            
            return None  # Continue
        
        @app.after_request
        def after_request(response) -> Any:
            # Add request ID to response headers
            response.headers['X-Request-ID'] = g.get('request_id', 'unknown')
            
            # Log request completion
            duration = (time.time() - g.get('start_time', time.time())) * 1000
            log_data = {
                'request_id': g.get('request_id'),
                'method': request.method,
                'path': request.path,
                'status': response.status_code,
                'duration_ms': round(duration, 2),
                'client_ip': g.get('client_ip'),
                'user_agent': g.get('user_agent')[:50] if g.get('user_agent') else None,
            }
            
            # Log based on status code
            if response.status_code >= 500:
                logger.error(f"Request failed: {log_data}")
            elif response.status_code >= 400:
                logger.warning(f"Request error: {log_data}")
            else:
                logger.info(f"Request completed: {log_data}")
            
            return response


class ErrorHandler:
    """Centralized error handling"""
    
    @staticmethod
    def init_app(app) -> None:
        """Initialize error handlers"""
        
        @app.errorhandler(400)
        def bad_request(error) -> Any:
            return jsonify({
                'error': 'Bad Request',
                'message': str(error.description) if hasattr(error, 'description') else 'Invalid request',
                'request_id': g.get('request_id')
            }), 400
        
        @app.errorhandler(401)
        def unauthorized(error) -> Any:
            return jsonify({
                'error': 'Unauthorized',
                'message': 'Authentication required',
                'request_id': g.get('request_id')
            }), 401
        
        @app.errorhandler(403)
        def forbidden(error) -> Any:
            return jsonify({
                'error': 'Forbidden',
                'message': 'Access denied',
                'request_id': g.get('request_id')
            }), 403
        
        @app.errorhandler(404)
        def not_found(error) -> Any:
            return jsonify({
                'error': 'Not Found',
                'message': f"Endpoint {request.path} not found",
                'request_id': g.get('request_id')
            }), 404
        
        @app.errorhandler(429)
        def rate_limit_exceeded(error) -> Any:
            return jsonify({
                'error': 'Too Many Requests',
                'message': 'Rate limit exceeded. Please try again later.',
                'request_id': g.get('request_id')
            }), 429
        
        @app.errorhandler(500)
        def internal_error(error) -> Any:
            logger.exception(f"Internal server error: {error}")
            return jsonify({
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred. Please try again later.',
                'request_id': g.get('request_id')
            }), 500


def validate_json(*required_fields) -> bool:
    """Decorator to validate JSON request body"""
    def decorator(f) -> Any:
        @wraps(f)
        def decorated_function(*args, **kwargs) -> Any:
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
            
            data = request.get_json(silent=True) or {}
            missing = [field for field in required_fields if field not in data]
            
            if missing:
                return jsonify({
                    'error': 'Missing required fields',
                    'fields': missing
                }), 400
            
            g.json_data = data
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_fields(*fields) -> Any:
    """Decorator to require specific fields in JSON body"""
    return validate_json(*fields)
