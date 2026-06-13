"""ACAS Pro Web - Flask application factory

This module implements the Flask application factory pattern,
providing a centralized way to create and configure the Flask app.
"""

from flask import Flask, jsonify, g, request
from typing import Optional, Dict, Any
from acas_pro.core.config import config
from acas_pro.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def create_app(test_config: Optional[Dict[str, Any]] = None) -> Flask:
    """Application factory pattern.

    Args:
        test_config: Optional configuration dictionary for testing.
            If provided, overrides default configuration.

    Returns:
        Flask: Configured Flask application instance.

    Raises:
        ValueError: If configuration is invalid or SECRET_KEY is not set.
    """
    app = Flask(__name__)

    # Load test config
    if test_config:
        app.config.update(test_config)

    # Validate configuration before starting (skip in test mode)
    if not app.config.get("TESTING"):
        is_valid, errors = config.validate()
        if not is_valid:
            for error in errors:
                logger.error(f"Configuration validation failed: {error}")
            raise ValueError(f"Invalid configuration: {', '.join(errors)}")

    # Load configuration
    _configure_app(app)

    # CORS — strict origin policy in production
    _configure_cors(app)

    # Register blueprints
    _register_blueprints(app)

    # Register authentication middleware (MUST be before other handlers)
    _register_auth_middleware(app)

    # Register API documentation (OpenAPI/Swagger)
    try:
        from .api_spec import register_api_docs

        register_api_docs(app)
    except ImportError:
        logger.warning("api_spec module not available, skipping API docs registration")

    # Register error handlers
    _register_error_handlers(app)

    return app


def _configure_app(app) -> None:
    """Configure Flask app settings"""
    import os

    # SECRET_KEY consistent with config.py / security.py / secrets_manager.py
    _secret = os.environ.get("SECRET_KEY", config.security.secret_key)
    if not _secret or _secret in (
        "acas-pro-secret-key-change-me",
        "dev-key-change-in-production",
    ):
        env_name = os.environ.get(
            "ACAS_ENV", os.environ.get("ENVIRONMENT", "development")
        )
        if env_name in ("production", "prod"):
            raise ValueError(
                "SECRET_KEY must be set in production! "
                "Set the SECRET_KEY environment variable in your deployment config."
            )
        # In non-prod: raise instead of generating ephemeral key so sessions survive restarts
        # and misconfiguration is caught early.
        logger.error(
            "SECRET_KEY not configured. Sessions will not persist across restarts. "
            "Set SECRET_KEY in .env or via secrets_manager."
        )
        raise ValueError(
            "SECRET_KEY must be configured even in development! "
            "Set the SECRET_KEY environment variable in your deployment config."
        )
    app.secret_key = _secret

    # HTTPS check in production
    if config.is_production():
        if (
            getattr(config, "enable_https", False) is True
            and config.tls_cert_path
            and config.tls_key_path
        ):
            import ssl
            from pathlib import Path

            cert_path = Path(config.tls_cert_path)
            key_path = Path(config.tls_key_path)
            if not cert_path.exists():
                logger.error(f"TLS certificate not found: {config.tls_cert_path}")
                if config.is_production():
                    raise FileNotFoundError(
                        f"TLS certificate required in production but not found: {config.tls_cert_path}"
                    )
            if not key_path.exists():
                logger.error(f"TLS private key not found: {config.tls_key_path}")
                if config.is_production():
                    raise FileNotFoundError(
                        f"TLS private key required in production but not found: {config.tls_key_path}"
                    )
            if cert_path.exists() and key_path.exists():
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(str(cert_path), str(key_path))
                app.config["SSL_CONTEXT"] = context
                logger.info("HTTPS enforced with TLS")
        else:
            logger.warning(
                "HTTPS not enforced in production! "
                "Set enable_https=true in config and provide tls_cert_path/tls_key_path, "
                "or configure a reverse-proxy (nginx) to handle TLS termination."
            )


def _configure_cors(app) -> None:
    """Configure Cross-Origin Resource Sharing (CORS).

    In production, CORS is configured to only allow known origins.
    In development, it allows localhost for convenience.
    """
    from flask_cors import CORS

    if config.is_production():
        raw_origins = config.cors_allowed_origins or ""
        allowed_origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
        if not allowed_origins:
            logger.warning(
                "No CORS origins configured for production. "
                "Set cors_allowed_origins to a comma-separated list of allowed domains."
            )
        CORS(
            app,
            resources={
                r"/api/*": {
                    "origins": allowed_origins,
                    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                    "allow_headers": ["Content-Type", "Authorization"],
                    "supports_credentials": True,
                    "max_age": 3600,
                }
            },
        )
        logger.info(f"CORS configured for origins: {allowed_origins}")
    else:
        CORS(
            app,
            resources={
                r"/api/*": {
                    "origins": [
                        "http://localhost:3000",
                        "http://localhost:5173",
                        "http://127.0.0.1:3000",
                    ],
                    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                    "allow_headers": ["Content-Type", "Authorization"],
                    "supports_credentials": True,
                    "max_age": 600,
                }
            },
        )
        logger.info("CORS configured for development origins")


def _register_auth_middleware(app) -> None:
    """Register before_request middleware for JWT authentication"""
    from flask import request
    from .routes.auth import verify_token

    # Routes that do NOT require authentication at all
    PUBLIC_ROUTES = {
        "auth.auth_register",
        "auth.auth_login",
        "dashboard.index",
        "static",
        "health.health_check",
    }
    PUBLIC_PREFIXES = (
        "/api/auth/register",
        "/api/auth/login",
        "/api/health",
        "/api/docs",
        "/api/openapi.json",
        "/api/openapi.yaml",
    )

    # Routes that are accessible without auth but don't expose sensitive data
    READ_ONLY_PUBLIC_PATHS = ("/", "/api/stats", "/api/activity")

    @app.before_request
    def authenticate() -> None:
        """Extract user from JWT token; reject unauthenticated access to protected routes."""
        endpoint = request.endpoint or ""
        path = request.path or ""

        # If route doesn't exist, let Flask return 404 (don't require auth for 404)
        if not endpoint:
            return None

        # 1. Fully public routes — no auth needed
        if endpoint in PUBLIC_ROUTES or any(
            path.startswith(p) for p in PUBLIC_PREFIXES
        ):
            return None

        # 2. Read-only public paths (dashboard stats, activity feed)
        if path in READ_ONLY_PUBLIC_PATHS:
            # Still parse token if present so g.user is available
            _extract_user_from_token(request)
            return None

        # 3. All other routes REQUIRE authentication
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
        else:
            # Also check cookie (set by login flow)
            token = request.cookies.get("access_token", "")

        if not token:
            return jsonify({"error": "Authentication required"}), 401
        payload = verify_token(token)
        if not payload:
            return jsonify({"error": "Invalid or expired token"}), 401

        user_id = payload.get("sub") or payload.get("user_id")
        account = payload.get("account", "")
        g.user = {"user_id": user_id, "account": account}
        return None

    def _extract_user_from_token(req) -> None:
        """Best-effort: parse JWT from request and set g.user if valid."""
        auth_header = req.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return
        token = auth_header[7:]
        payload = verify_token(token)
        if payload:
            user_id = payload.get("sub") or payload.get("user_id")
            account = payload.get("account", "")
            g.user = {"user_id": user_id, "account": account}


def _register_blueprints(app) -> None:
    """Register all route blueprints"""
    from .routes import auth, llm, dashboard, metrics, health, dashboard_stats

    app.register_blueprint(auth.bp)
    app.register_blueprint(llm.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(dashboard_stats.bp)
    app.register_blueprint(metrics.bp)
    app.register_blueprint(health.bp)


def _register_error_handlers(app: Flask) -> None:
    """Register global error handlers for the Flask application.

    Registers error handlers for common HTTP errors:
    - 400 Bad Request
    - 401 Unauthorized
    - 403 Forbidden
    - 404 Not Found
    - 405 Method Not Allowed
    - 500 Internal Server Error
    - Generic exceptions

    Error responses are format based on request type:
    - API requests (URL starts with /api/ or Accept: application/json) → JSON
    - Browser requests → HTML

    Args:
        app: Flask application instance.
    """
    import traceback
    import logging

    logger = logging.getLogger(__name__)

    def _is_api_request() -> None:
        """Check if request expects JSON response."""
        # Check URL prefix
        if request.path.startswith("/api/"):
            return True
        # Check Accept header
        accept = request.headers.get("Accept", "")
        if "application/json" in accept:
            return True
        return False

    def _make_error_response(status_code, message, details=None) -> None:
        """Create error response (JSON or HTML)."""
        if _is_api_request():
            error_data = {
                "error": True,
                "message": message,
                "status_code": status_code,
            }
            if details and app.debug:
                error_data["details"] = details
            resp = jsonify(error_data)
            resp.status_code = status_code
            return resp
        else:
            # HTML response
            html = f"""<!DOCTYPE html>
<html>
<head><title>Error {status_code}</title></head>
<body>
    <h1>Error {status_code}</h1>
    <p>{message}</p>
</body>
</html>"""
            return html, status_code, {"Content-Type": "text/html"}

    @app.errorhandler(400)
    def handle_bad_request(e) -> None:
        logger.warning(f"Bad request: {request.path} - {str(e)}")
        return _make_error_response(400, "Bad Request", str(e))

    @app.errorhandler(401)
    def handle_unauthorized(e) -> None:
        logger.warning(f"Unauthorized: {request.path}")
        return _make_error_response(401, "Unauthorized", str(e))

    @app.errorhandler(403)
    def handle_forbidden(e) -> None:
        logger.warning(f"Forbidden: {request.path}")
        return _make_error_response(403, "Forbidden", str(e))

    @app.errorhandler(404)
    def handle_not_found(e) -> None:
        logger.info(f"Not found: {request.path}")
        return _make_error_response(404, "Not Found", str(e))

    @app.errorhandler(405)
    def handle_method_not_allowed(e) -> None:
        logger.warning(f"Method not allowed: {request.method} {request.path}")
        return _make_error_response(405, "Method Not Allowed", str(e))

    @app.errorhandler(500)
    def handle_internal_error(e) -> None:
        logger.error(f"Internal server error: {request.path}", exc_info=True)
        details = traceback.format_exc() if app.debug else None
        return _make_error_response(500, "Internal Server Error", details)

    @app.errorhandler(Exception)
    def handle_generic_exception(e) -> None:
        logger.error(f"Unhandled exception: {request.path}", exc_info=True)
        details = traceback.format_exc() if app.debug else None
        return _make_error_response(500, "Internal Server Error", details)
