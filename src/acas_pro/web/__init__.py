"""ACAS Pro Web - Flask application factory"""
from flask import Flask
from acas_pro.core.config import config
from acas_pro.core.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def create_app():
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Validate configuration before starting
    is_valid, errors = config.validate()
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
    _secret = os.environ.get('SECRET_KEY', config.security.secret_key)
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
    if config.environment == 'production':
        logger.warning("HTTPS not enforced — configure nginx to redirect HTTP → HTTPS in production")


def _register_blueprints(app):
    """Register all route blueprints"""
    from .routes import auth, llm, dashboard
    
    app.register_blueprint(auth.bp)
    app.register_blueprint(llm.bp)
    app.register_blueprint(dashboard.bp)
