"""ACAS Pro Web - Flask application factory"""
from flask import Flask, jsonify, g
from acas_pro.core.config import config
from acas_pro.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Validate configuration before starting
    is_valid, errors = config().validate()
    if not is_valid:
        for error in errors:
            logger.error(f"Configuration validation failed: {error}")
        raise ValueError(f"Invalid configuration: {', '.join(errors)}")
    
    # Load configuration
    _configure_app(app)
    
    # Register blueprints
    _register_blueprints(app)
    
    return app


def _configure_app(app):
    """Configure Flask app settings"""
    import os
    import uuid
    import hashlib
    
    # SECRET_KEY
    _secret = os.environ.get('SECRET_KEY', config().security.secret_key)
    if not _secret or _secret in ('acas-pro-secret-key-change-me', 'dev-key-change-in-production'):
        env_name = os.environ.get('ENVIRONMENT', os.environ.get('FLASK_ENV', 'development'))
        if env_name in ('production', 'prod'):
            raise ValueError(
                "SECRET_KEY must be set in production! "
                "Add SECRET_KEY=<your-secret> to .env file. "
                "Generate one: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        _secret = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
        logger.warning("SECRET_KEY not properly set — generated ephemeral key.")
    app.secret_key = _secret
    
    # HTTPS check in production
    if config().environment == 'production':
        logger.warning("HTTPS not enforced — configure nginx to redirect HTTP → HTTPS in production")


def _register_auth_middleware(app):
    """Register before_request middleware for JWT authentication"""
    from flask import g, request
    from .routes.auth import verify_token
    
    # Routes that do NOT require authentication at all
    PUBLIC_ROUTES = {
        'auth.auth_register', 'auth.auth_login', 'auth_v2.register', 'auth_v2.login',
        'dashboard.index',
        'static',
    }
    PUBLIC_PREFIXES = ('/api/auth/register', '/api/auth/login', '/api/v2/auth/register', '/api/v2/auth/login', '/api/health')
    
    # Routes that are accessible without auth but don't expose sensitive data
    READ_ONLY_PUBLIC_PATHS = ('/', '/api/stats', '/api/activity')
    
    @app.before_request
    def authenticate():
        """Extract user from JWT token; reject unauthenticated access to protected routes."""
        endpoint = request.endpoint or ''
        path = request.path or ''
        
        # 1. Fully public routes — no auth needed
        if endpoint in PUBLIC_ROUTES or any(path.startswith(p) for p in PUBLIC_PREFIXES):
            return None
        
        # 2. Read-only public paths (dashboard stats, activity feed)
        if path in READ_ONLY_PUBLIC_PATHS:
            # Still parse token if present so g.user is available
            _extract_user_from_token(request)
            return None
        
        # 3. All other routes REQUIRE authentication
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
        
        token = auth_header[7:]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
        
        user_id = payload.get('sub') or payload.get('user_id')
        account = payload.get('account', '')
        g.user = {'user_id': user_id, 'account': account}
        return None
    
    def _extract_user_from_token(req):
        """Best-effort: parse JWT from request and set g.user if valid."""
        auth_header = req.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return
        token = auth_header[7:]
        payload = verify_token(token)
        if payload:
            user_id = payload.get('sub') or payload.get('user_id')
            account = payload.get('account', '')
            g.user = {'user_id': user_id, 'account': account}


def _register_blueprints(app):
    """Register all route blueprints"""
    from .routes import auth, llm, dashboard
    
    app.register_blueprint(auth.bp)
    app.register_blueprint(llm.bp)
    app.register_blueprint(dashboard.bp)
    
    # Register authentication middleware
    _register_auth_middleware(app)
