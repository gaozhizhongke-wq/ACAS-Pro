"""ACAS Pro Web - Flask application factory"""
from flask import Flask, jsonify, g, request
from acas_pro.core.config import config
from acas_pro.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def create_app(test_config=None):
    """Application factory pattern"""
    app = Flask(__name__)

    # Load test config
    if test_config:
        app.config.update(test_config)

    # Validate configuration before starting (skip in test mode)
    if not app.config.get('TESTING'):
        is_valid, errors = config.validate()
        if not is_valid:
            for error in errors:
                logger.error(f'Configuration validation failed: {error}')
            raise ValueError(f"Invalid configuration: {', '.join(errors)}")

    # Load configuration
    _configure_app(app)

    # Register blueprints
    _register_blueprints(app)

    # Register API documentation (OpenAPI/Swagger)
    try:
        from .api_spec import register_api_docs
        register_api_docs(app)
    except ImportError:
        logger.warning('api_spec module not available, skipping API docs registration')

    # Register error handlers
    _register_error_handlers(app)

    return app


def _configure_app(app):
    """Configure Flask app settings"""
    import os

    # SECRET_KEY consistent with config.py / security.py / secrets_manager.py
    _secret = os.environ.get('SECRET_KEY', config.security.secret_key)
    if not _secret or _secret in ('acas-pro-secret-key-change-me', 'dev-key-change-in-production'):
        env_name = os.environ.get('ACAS_ENV', os.environ.get('ENVIRONMENT', 'development'))
        if env_name in ('production', 'prod'):
            raise ValueError(
                "SECRET_KEY must be set in production! "
                "Add SECRET_KEY=<your-secret> to .env file. "
                "Generate one: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
            )
        # In non-prod: raise instead of generating ephemeral key so sessions survive restarts
        # and misconfiguration is caught early.
        logger.error(
            "SECRET_KEY not configured. Sessions will not persist across restarts. "
            "Set SECRET_KEY in .env or via secrets_manager."
        )
        raise ValueError(
            "SECRET_KEY must be configured even in development! "
            "Add SECRET_KEY=<your-secret> to .env file. "
            "Generate one: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    app.secret_key = _secret

    # HTTPS check in production
    if config.environment == 'production':
        logger.warning("HTTPS not enforced — configure nginx to redirect HTTP -> HTTPS in production")


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
    PUBLIC_PREFIXES = ('/api/auth/register', '/api/auth/login',
                       '/api/v2/auth/register', '/api/v2/auth/login', '/api/health',
                       '/api/docs', '/api/openapi.json', '/api/openapi.yaml')

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
    from .routes import auth, llm, dashboard, metrics

    app.register_blueprint(auth.bp)
    app.register_blueprint(llm.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(metrics.bp)


def _register_error_handlers(app):
    """Register global error handlers."""
    import traceback
    import logging

    logger = logging.getLogger(__name__)

    def _is_api_request():
        """Check if request expects JSON response."""
        # Check URL prefix
        if request.path.startswith('/api/'):
            return True
        # Check Accept header
        accept = request.headers.get('Accept', '')
        if 'application/json' in accept:
            return True
        return False

    def _make_error_response(status_code, message, details=None):
        """Create error response (JSON or HTML)."""
        if _is_api_request():
            error_data = {
                'error': True,
                'message': message,
                'status_code': status_code,
            }
            if details and app.debug:
                error_data['details'] = details
            resp = jsonify(error_data)
            resp.status_code = status_code
            return resp
        else:
            # HTML response
            html = f'''<!DOCTYPE html>
<html>
<head><title>Error {status_code}</title></head>
<body>
    <h1>Error {status_code}</h1>
    <p>{message}</p>
</body>
</html>'''
            return html, status_code, {'Content-Type': 'text/html'}

    @app.errorhandler(400)
    def handle_bad_request(e):
        logger.warning(f'Bad request: {request.path} - {str(e)}')
        return _make_error_response(400, 'Bad Request', str(e))

    @app.errorhandler(401)
    def handle_unauthorized(e):
        logger.warning(f'Unauthorized: {request.path}')
        return _make_error_response(401, 'Unauthorized', str(e))

    @app.errorhandler(403)
    def handle_forbidden(e):
        logger.warning(f'Forbidden: {request.path}')
        return _make_error_response(403, 'Forbidden', str(e))

    @app.errorhandler(404)
    def handle_not_found(e):
        logger.info(f'Not found: {request.path}')
        return _make_error_response(404, 'Not Found', str(e))

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        logger.warning(f'Method not allowed: {request.method} {request.path}')
        return _make_error_response(405, 'Method Not Allowed', str(e))

    @app.errorhandler(500)
    def handle_internal_error(e):
        logger.error(f'Internal server error: {request.path}', exc_info=True)
        details = traceback.format_exc() if app.debug else None
        return _make_error_response(500, 'Internal Server Error', details)

    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        logger.error(f'Unhandled exception: {request.path}', exc_info=True)
        details = traceback.format_exc() if app.debug else None
        return _make_error_response(500, 'Internal Server Error', details)
