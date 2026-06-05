#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ACAS Pro Web - Production-grade Web Dashboard

Phase 1: LLM chat pipeline (bridge config → LLMClient, /api/llm/chat)
Phase 2: JWT auth middleware, login/register
"""

import os
import sys
import json
import time
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from functools import wraps

# ── Load .env ──────────────────────────────────────────────────────────────
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(env_path):
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")

# ── Load keys from .keys/ directory (replaces ${KEYS_DIR} references) ────────
try:
    from security.key_loader import load_keys_to_env
    _loaded_keys = load_keys_to_env(os.path.dirname(os.path.abspath(__file__)))
    if _loaded_keys:
        print(f'[key_loader] Loaded {len(_loaded_keys)} keys: {_loaded_keys}')
except ImportError:
    pass  # key_loader not available, keys must be in env already

src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from flask import Flask, render_template_string, request, jsonify, g, make_response, render_template
import jwt

from acas_pro.core.security import password_validator as pv, JWTManager, rate_limiter, create_csrf_cookie, generate_csrf_token, require_csrf, set_jwt_cookie, clear_jwt_cookie, get_jwt_from_cookie
from acas_pro.core.config import config
from acas_pro.core.logging import setup_logging, get_logger
from acas_pro.services.user_service import user_service
from acas_pro.llm.llm_client import (
    LLMClient,
    LLMConfig as ClientLLMConfig,
    LLMProvider,
    LLMMessage,
)
from acas_pro.core.database import DatabaseManager
from acas_pro.core.security_headers import SecurityHeaders, InputValidator

# New production middleware
from acas_pro.web.middleware import RequestContext, ErrorHandler
from acas_pro.web.health import health_checker
from acas_pro.web.api_spec import register_api_docs

setup_logging()
logger = get_logger(__name__)

# ── HTTPS Enforcement (Production) ──────────────────────────────────────────
if config().environment == 'production':
    from flask import request
    if not request.is_secure:
        logger.warning("HTTPS not enforced — configure your reverse proxy (nginx) to redirect HTTP → HTTPS in production")

# ── Flask App ──────────────────────────────────────────────────────────────
app = Flask(__name__)

# SECRET_KEY — required for Flask sessions/flash/CSRF
_secret = os.environ.get('SECRET_KEY', config().security.secret_key)
if not _secret or _secret in ('acas-pro-secret-key-change-me', 'dev-key-change-in-production'):
    _env = os.environ.get('ACAS_ENV', os.environ.get('ENVIRONMENT', 'development'))
    if _env in ('production', 'prod'):
        raise ValueError("SECRET_KEY must be set in production! Add SECRET_KEY=<your-secret> to .env file.")
    raise ValueError(
        "SECRET_KEY must be configured! Add SECRET_KEY=<your-secret> to .env file. "
        "Generate one: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
    )
app.secret_key = _secret

# Initialize security headers
security = SecurityHeaders(app)

# Initialize production middleware
RequestContext.init_app(app)
ErrorHandler.init_app(app)
logger.info("Production middleware initialized")

from acas_pro.web.routes import auth_bp, llm_bp, dashboard_bp

app.register_blueprint(auth_bp)
app.register_blueprint(llm_bp)
app.register_blueprint(dashboard_bp)

logger.info("Blueprints registered: auth, llm, dashboard")



@app.route('/')
def index():
    llm_provider = config().llm.provider if config().llm.enabled else 'not configured'
    key_val = config().llm.api_key
    llm_key_mask = ('*' * 20) + key_val[-4:] if key_val else 'not set'
    return render_template(
        'dashboard.html',
        llm_provider=llm_provider,
        llm_key_mask=llm_key_mask,
        llm_enabled=config().llm.enabled,
    )


# ── CORS ───────────────────────────────────────────────────────────────────
@app.after_request
def add_cors_headers(response):
    """Production-grade CORS with security controls"""
    origins = config().security.cors_allowed_origins
    
    if config().environment == 'production':
        # Production: strict origin validation
        if not origins or origins == '*':
            logger.error("[SECURITY] CORS allowed origins not configured in production. "
                        "Set CORS_ALLOWED_ORIGINS in .env (e.g., https://yourdomain.com)")
            # Do NOT send CORS headers when not configured
            return response
        
        # Validate origin against whitelist
        request_origin = request.headers.get('Origin', '')
        allowed_list = [o.strip() for o in origins.split(',') if o.strip()]
        
        if request_origin and request_origin in allowed_list:
            response.headers['Access-Control-Allow-Origin'] = request_origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
        else:
            # Origin not in whitelist - don't expose CORS headers
            logger.warning(f"[SECURITY] Blocked CORS request from origin: {request_origin}")
    else:
        # Development: allow localhost with credentials
        request_origin = request.headers.get('Origin', '')
        if request_origin and request_origin.startswith('http://localhost'):
            response.headers['Access-Control-Allow-Origin'] = request_origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
        elif origins:
            origin = origins.split(',')[0].strip()
            if origin and origin != '*':
                response.headers['Access-Control-Allow-Origin'] = origin
                response.headers['Access-Control-Allow-Credentials'] = 'true'
            else:
                response.headers['Access-Control-Allow-Origin'] = '*'
        else:
            response.headers['Access-Control-Allow-Origin'] = '*'
    
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response
