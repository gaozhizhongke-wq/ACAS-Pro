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

src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from flask import Flask, render_template_string, request, jsonify, g, make_response
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

# Initialize security headers
security = SecurityHeaders(app)

# Initialize production middleware
RequestContext.init_app(app)
ErrorHandler.init_app(app)
logger.info("Production middleware initialized")

# Register API documentation
register_api_docs(app)
logger.info("API documentation registered at /api/docs")

# SECRET_KEY: 生产环境强制要求
_secret = os.environ.get('SECRET_KEY', config().security.secret_key)
if not _secret or _secret in ('acas-pro-secret-key-change-me', 'dev-key-change-in-production'):
    # 生产环境必须设置 SECRET_KEY
    env_name = os.environ.get('ENVIRONMENT', os.environ.get('FLASK_ENV', 'development'))
    if env_name in ('production', 'prod'):
        raise ValueError(
            "SECRET_KEY must be set in production! "
            "Add SECRET_KEY=<your-secret> to .env file. "
            "Generate one: python -c \"import secrets; print(secrets.token_urlsafe(48))\""
        )
    _secret = hashlib.sha256(uuid.uuid4().bytes).hexdigest()
    logger.warning("SECRET_KEY not properly set — generated ephemeral key. Set SECRET_KEY in .env for production.")
app.secret_key = _secret
JWT_SECRET = _secret
JWT_ALGORITHM = 'HS256'
JWT_EXPIRY_HOURS = 24


# ── LLM Bridge ────────────────────────────────────────────────────────────
_PROVIDER_MAP = {
    'openai': LLMProvider.OPENAI,
    'anthropic': LLMProvider.ANTHROPIC,
    'kimi': LLMProvider.KIMI,
    'deepseek': LLMProvider.DEEPSEEK,
    'qwen': LLMProvider.QWEN,
    'lmstudio': LLMProvider.LMSTUDIO,
    'ollama': LLMProvider.OLLAMA,
}


def create_llm_client() -> LLMClient:
    """Bridge: config().py LLMConfig → llm_client.LLMConfig → LLMClient"""
    llm = config().llm
    if not llm.enabled or not llm.api_key:
        raise RuntimeError("LLM not configured. Set DEEPSEEK_API_KEY in .env or configure via Settings page.")
    provider_enum = _PROVIDER_MAP.get(llm.provider, LLMProvider.OPENAI)
    client_cfg = ClientLLMConfig(
        provider=provider_enum,
        api_key=llm.api_key,
        api_base=llm.api_base or '',
        model=llm.model or '',
        max_tokens=llm.max_tokens,
        temperature=llm.temperature,
        top_p=llm.top_p,
    )
    return LLMClient(client_cfg)


# ── JWT Auth Helpers (unified with security.py JWTManager) ───────────────────────
# NOTE: JWTManager issues short-lived tokens (15 min). Old 24h tokens are still
# accepted for backward compatibility via the dual-claim check in verify_token().


def generate_token(user_id: str, account: str) -> str:
    """Generate JWT using JWTManager (unified auth system)."""
    return JWTManager.generate_token(user_id, extra_claims={'account': account})


def verify_token(token: str) -> dict | None:
    """
    Verify JWT using JWTManager. Supports both:
    - New tokens (JWTManager, claim='sub')
    - Old tokens (legacy, claim='user_id') for backward compatibility
    """
    payload = JWTManager.verify_token(token, expected_type='access')
    if payload:
        return payload
    # Fallback: try legacy format (user_id claim, 24h expiry)
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get('user_id'):
            return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        pass
    return None


# ── Startup Cleanup ─────────────────────────────────────────────────────────
# Run once on first request: clean stale guest accounts + warn about in-memory rate limiter
_cleanup_done = False


@app.before_request
def _startup_cleanup():
    """Execute one-time startup tasks on first request."""
    global _cleanup_done
    if _cleanup_done:
        return None
    _cleanup_done = True

    # Warn about in-memory rate limiter (not safe for multi-process deployments)
    if config().environment == 'production':
        logger.warning(
            "SECURITY: Using in-memory RateLimiter. "
            "In multi-process deployments (gunicorn -w N, N>1), rate limits are per-process "
            "and can be bypassed. Use a database-backed rate limiter (Redis) for production."
        )

    # Clean stale guest accounts (older than 24 hours)
    try:
        from datetime import timedelta as td
        cutoff = (datetime.now(timezone.utc) - td(hours=24)).isoformat()
        db = DatabaseManager()
        deleted = db.db.execute(
            "DELETE FROM users WHERE account_type='guest' AND created_at < ?", (cutoff,)
        ).rowcount
        if deleted > 0:
            logger.info(f"Startup cleanup: removed {deleted} stale guest account(s)")
    except Exception as e:
        logger.warning(f"Guest account cleanup failed (non-fatal): {e}")


# ── Auth Middleware ────────────────────────────────────────────────────────
_PUBLIC_PATHS = {'/api/health', '/api/auth/login', '/api/auth/register', '/'}
_PUBLIC_PREFIXES = ('/static/',)


@app.before_request
def check_auth():
    """JWT auth middleware — public paths exempted"""
    path = request.path

    # Skip OPTIONS (CORS preflight)
    if request.method == 'OPTIONS':
        return None

    # Public paths
    if path in _PUBLIC_PATHS or any(path.startswith(p) for p in _PUBLIC_PREFIXES):
        return None

    # Extract token: Authorization header (preferred), fallback to httpOnly cookie
    auth_header = request.headers.get('Authorization', '')
    token = auth_header.removeprefix('Bearer ').strip() if auth_header.startswith('Bearer ') else ''

    # Fallback: read JWT from httpOnly cookie (XSS-safe storage)
    if not token:
        token = get_jwt_from_cookie(request)

    if not token:
        return jsonify({'error': 'Authentication required', 'code': 'AUTH_REQUIRED'}), 401

    payload = verify_token(token)
    if not payload:
        return jsonify({'error': 'Invalid or expired token', 'code': 'AUTH_INVALID'}), 401

    g.user = payload


# ── CORS ───────────────────────────────────────────────────────────────────
@app.after_request
def add_cors_headers(response):
    origins = config().security.cors_allowed_origins
    if origins:
        # Strip trailing commas/whitespace
        origin = origins.split(',')[0].strip()
        if not origin or origin == '*':
            # No specific origin: don't send credentials with wildcard
            response.headers['Access-Control-Allow-Origin'] = '*'
            # Do NOT send Credentials: true with wildcard — browser rejects it
        else:
            # Specific origin + credentials
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
    else:
        response.headers['Access-Control-Allow-Origin'] = '*'
        # No Credentials header when using wildcard
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response


# ── Health Check ──────────────────────────────────────────────────────────
@app.route('/api/health', methods=['GET'])
def health_check():
    """Comprehensive health check endpoint for load balancers and monitoring"""
    result = health_checker.check_all()
    
    # Return appropriate status code
    status_code = 200 if result['status'] == 'healthy' else \
                  200 if result['status'] == 'degraded' else 503
    
    return jsonify(result), status_code


# ── Auth Routes ────────────────────────────────────────────────────────────
@app.route('/api/auth/register', methods=['POST'])
@require_csrf
def auth_register():
    from acas_pro.core.security import rate_limiter
    
    data = request.json or {}
    account = data.get('account', '').strip()
    password = data.get('password', '').strip()
    nickname = data.get('nickname', '').strip()

    if not account or not password:
        return jsonify({'error': 'account and password are required'}), 400
    
    # Enforce strong password policy (not just length — use validator)
    is_valid, pw_msg = pv.validate(password)
    if not is_valid:
        return jsonify({'error': pw_msg}), 400
    
    # Rate limit registration (10 per 10 minutes per account)
    rate_key = f"register:{account}"
    if not rate_limiter.is_allowed(rate_key, max_attempts=10, window_seconds=600):
        return jsonify({'error': 'Too many registration attempts. Please try again later.'}), 429
    rate_limiter.record_attempt(rate_key)

    ok, msg, profile = user_service.register(account=account, password=password, nickname=nickname or account)
    if not ok:
        return jsonify({'error': msg}), 409

    token = generate_token(profile.id, account)
    resp = jsonify({
        'success': True,
        'token': token,
        'user': {'user_id': profile.id, 'account': profile.account, 'nickname': profile.nickname}
    })
    create_csrf_cookie(resp)
    set_jwt_cookie(resp, token)
    return resp


@app.route('/api/auth/login', methods=['POST'])
@require_csrf
def auth_login():
    data = request.json or {}
    account = data.get('account', '').strip()
    password = data.get('password', '').strip()

    if not account or not password:
        return jsonify({'error': 'account and password are required'}), 400

    # Rate limit login attempts: 20 per 10 minutes per account (brute-force protection)
    rate_key = f"login:{account}"
    if not rate_limiter.is_allowed(rate_key, max_attempts=20, window_seconds=600):
        return jsonify({'error': 'Too many login attempts. Please try again later.'}), 429
    rate_limiter.record_attempt(rate_key)

    ok, msg, profile = user_service.login(account=account, password=password)
    if not ok:
        return jsonify({'error': msg}), 401

    token = generate_token(profile.id, account)
    resp = jsonify({
        'success': True,
        'token': token,
        'user': {'user_id': profile.id, 'account': profile.account, 'nickname': profile.nickname}
    })
    create_csrf_cookie(resp)
    set_jwt_cookie(resp, token)
    return resp


@app.route('/api/auth/me', methods=['GET'])
def auth_me():
    user = g.user
    return jsonify({'user_id': user['user_id'], 'account': user['account']})


# ── LLM Routes ────────────────────────────────────────────────────────────
@app.route('/api/llm/config', methods=['POST'])
@require_csrf
def save_llm_config():
    data = request.json or {}
    provider = data.get('provider', 'openai')
    api_key = data.get('api_key', '')
    api_base = data.get('api_base') or None
    model = data.get('model') or None

    # Update config
    config().llm.provider = provider
    if api_key:
        config().llm.api_key = api_key
    if api_base:
        config().llm.api_base = api_base
    if model:
        config().llm.model = model
    config().llm.enabled = True

    # Also set environment variables for persistence
    env_key = f'{provider.upper()}_API_KEY'
    os.environ[env_key] = api_key
    os.environ['LLM_PROVIDER'] = provider

    config().save()
    logger.info(f"LLM config updated: provider={provider}")

    return jsonify({'success': True, 'provider': provider})


@app.route('/api/llm/test')
def test_llm():
    try:
        client = create_llm_client()
        resp = client.quick_chat('Hello, reply with one word: OK')
        return jsonify({'success': True, 'message': resp[:200]})
    except Exception as e:
        logger.error(f"LLM test failed: {e}")
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/llm/chat', methods=['POST'])
def chat_llm():
    """Chat endpoint — accepts message + optional history"""
    data = request.json or {}
    message = data.get('message', '').strip()
    system_prompt = data.get('system', 'You are a helpful assistant for ACAS Pro business users.')
    history = data.get('history', [])  # [{role, content}, ...]

    if not message:
        return jsonify({'error': 'message is required'}), 400

    try:
        client = create_llm_client()

        # Build message list
        messages = [LLMMessage(role="system", content=system_prompt)]
        for h in history[-20:]:  # Keep last 20 messages for context
            messages.append(LLMMessage(role=h.get('role', 'user'), content=h.get('content', '')))
        messages.append(LLMMessage(role="user", content=message))

        start = time.time()
        response = client.chat(messages)
        latency = int((time.time() - start) * 1000)

        return jsonify({
            'success': True,
            'content': response.content,
            'model': response.model,
            'usage': response.usage,
            'latency_ms': latency,
        })
    except Exception as e:
        logger.error(f"LLM chat failed: {e}")
        return jsonify({'success': False, 'error': str(e)})


# ── Dashboard Stats ───────────────────────────────────────────────────────
@app.route('/api/dashboard/stats')
def dashboard_stats():
    """Real dashboard data from database — fixed 5-layer bug"""
    import logging
    logger = logging.getLogger(__name__)
    try:
        db = DatabaseManager()
        stats = {}

        # Revenue: transactions table, total_amount, last 30 days
        try:
            result = db.fetchone(
                "SELECT COALESCE(SUM(amount), 0) AS total "
                "FROM transactions "
                "WHERE created_at >= datetime('now', '-30 days') "
                "  AND status IN ('completed', 'settled')"
            )
            stats['revenue'] = result['total'] if result else 0
        except Exception as e:
            logger.error(f'revenue query failed: {e}')
            stats['revenue'] = 0

        # Active orders: orders table (0 rows — use transactions as proxy)
        try:
            result = db.fetchone(
                "SELECT COUNT(*) AS cnt "
                "FROM orders "
                "WHERE status IN ('pending', 'processing', 'shipped')"
            )
            stats['active_orders'] = result['cnt'] if result else 0
        except Exception as e:
            logger.error(f'active_orders query failed: {e}')
            # Fallback: count recent transactions
            try:
                result = db.fetchone(
                    "SELECT COUNT(*) AS cnt FROM transactions "
                    "WHERE created_at >= datetime('now', '-7 days')"
                )
                stats['active_orders'] = result['cnt'] if result else 0
            except Exception:
                stats['active_orders'] = 0

        # Inventory: products.stock_quantity > 0
        try:
            result = db.fetchone(
                "SELECT COUNT(*) AS cnt FROM products WHERE stock_quantity > 0"
            )
            stats['inventory'] = result['cnt'] if result else 0
        except Exception as e:
            logger.error(f'inventory query failed: {e}')
            stats['inventory'] = 0

        # Low stock: stock_quantity <= reorder_point
        try:
            result = db.fetchone(
                "SELECT COUNT(*) AS cnt "
                "FROM products "
                "WHERE stock_quantity > 0 AND stock_quantity <= reorder_point"
            )
            stats['low_stock'] = result['cnt'] if result else 0
        except Exception as e:
            logger.error(f'low_stock query failed: {e}')
            stats['low_stock'] = 0

        # Risk alerts: data_alerts table, unacknowledged
        try:
            result = db.fetchone(
                "SELECT COUNT(*) AS cnt FROM data_alerts WHERE acknowledged = 0"
            )
            stats['risk_alerts'] = result['cnt'] if result else 0
        except Exception as e:
            logger.error(f'risk_alerts query failed: {e}')
            stats['risk_alerts'] = 0

        stats['llm_enabled'] = config().llm.enabled
        stats['llm_provider'] = config().llm.provider if config().llm.enabled else 'disabled'
        return jsonify(stats)
    except Exception as e:
        logger.error(f'dashboard_stats outer exception: {e}')
        return jsonify({
            'revenue': 0,
            'active_orders': 0,
            'inventory': 0,
            'low_stock': 0,
            'risk_alerts': 0,
            'llm_enabled': config().llm.enabled,
            'llm_provider': config().llm.provider if config().llm.enabled else 'disabled',
        })


# ── Health ─────────────────────────────────────────────────────────────────
# NOTE: /api/health is registered at line ~163 (health_check).
# The duplicate definition below is removed — Flask only uses the first.

@app.route('/api/festivals', methods=['GET'])
def list_festivals():
    db = DatabaseManager()
    try:
        rows = db.fetchall(
            "SELECT id, name, festival_type, importance, month, day, "
            "       duration_days, themes, keywords, is_active "
            "FROM festivals ORDER BY month, day"
        )
        return jsonify({'success': True, 'festivals': rows})
    except Exception as e:
        logger.error(f'festivals query failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/products', methods=['GET'])
def list_products():
    db = DatabaseManager()
    try:
        rows = db.fetchall(
            "SELECT id, name, category, price, stock_quantity, reorder_point, status "
            "FROM products ORDER BY name LIMIT 200"
        )
        return jsonify({'success': True, 'products': rows})
    except Exception as e:
        logger.error(f'products query failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/products/low-stock', methods=['GET'])
def low_stock_products():
    db = DatabaseManager()
    try:
        rows = db.fetchall(
            "SELECT id, name, category, price, stock_quantity, reorder_point, "
            "       (reorder_point - stock_quantity) AS deficit "
            "FROM products "
            "WHERE stock_quantity > 0 AND stock_quantity <= reorder_point "
            "ORDER BY deficit DESC"
        )
        return jsonify({'success': True, 'products': rows})
    except Exception as e:
        logger.error(f'low-stock query failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/accounts', methods=['GET'])
def list_accounts():
    db = DatabaseManager()
    try:
        rows = db.fetchall(
            "SELECT id, platform, account_name, followers, content_count, "
            "       total_views, total_likes, status, phase, last_login_at "
            "FROM platform_accounts ORDER BY platform LIMIT 100"
        )
        return jsonify({'success': True, 'accounts': rows})
    except Exception as e:
        logger.error(f'accounts query failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/forecast/daily', methods=['GET'])
def forecast_daily():
    db = DatabaseManager()
    try:
        rows = db.fetchall(
            "SELECT date, platform, SUM(revenue) AS revenue, "
            "       SUM(orders) AS orders, SUM(views) AS views "
            "FROM daily_metrics "
            "WHERE date >= date('now', '-30 days') "
            "GROUP BY date, platform "
            "ORDER BY date ASC LIMIT 90"
        )
        return jsonify({'success': True, 'data': rows})
    except Exception as e:
        logger.error(f'daily_metrics query failed: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500


# ── HTML Template ─────────────────────────────────────────────────────────
DASHBOARD_HTML = r'''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ACAS Pro</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0d1117; color: #c9d1d9; min-height: 100vh; }
        .sidebar { position: fixed; left: 0; top: 0; width: 240px; height: 100vh; background: #161b22; border-right: 1px solid #30363d; padding: 20px 0; display: flex; flex-direction: column; }
        .logo { padding: 0 20px 20px; font-size: 20px; font-weight: bold; color: #58a6ff; border-bottom: 1px solid #30363d; margin-bottom: 16px; }
        .nav-item { display: block; padding: 12px 20px; color: #8b949e; text-decoration: none; transition: all 0.2s; cursor: pointer; }
        .nav-item:hover, .nav-item.active { color: #58a6ff; background: #21262d; }
        .nav-spacer { flex: 1; }
        .nav-user { padding: 12px 20px; color: #8b949e; font-size: 12px; border-top: 1px solid #30363d; }
        .main { margin-left: 240px; padding: 28px; }
        .header { margin-bottom: 24px; }
        .header h1 { font-size: 28px; margin-bottom: 8px; }
        .header p { color: #8b949e; }
        .cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 16px; margin-bottom: 24px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; }
        .card-title { color: #8b949e; font-size: 13px; margin-bottom: 8px; }
        .card-value { font-size: 28px; font-weight: bold; margin-bottom: 4px; }
        .card-sub { font-size: 12px; }
        .success { color: #3fb950; }
        .accent { color: #58a6ff; }
        .warning { color: #d29922; }
        .danger { color: #f85149; }
        .section-title { font-size: 16px; font-weight: bold; margin: 24px 0 16px; }
        .btn { display: inline-block; padding: 10px 20px; background: #21262d; border: 1px solid #30363d; border-radius: 8px; color: #c9d1d9; cursor: pointer; transition: all 0.2s; font-size: 14px; }
        .btn:hover { background: #58a6ff; color: white; border-color: #58a6ff; }
        .btn-primary { background: #238636; border-color: #238636; color: white; }
        .btn-primary:hover { background: #2ea043; }
        .btn-danger { background: #da3633; border-color: #da3633; color: white; }
        .content-area { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; min-height: 300px; }
        .form-group { margin-bottom: 16px; }
        .form-group label { display: block; margin-bottom: 8px; color: #8b949e; font-size: 13px; }
        .form-group input, .form-group select, .form-group textarea { width: 100%; max-width: 500px; padding: 10px 14px; background: #21262d; border: 1px solid #30363d; border-radius: 8px; color: #c9d1d9; font-size: 14px; }
        .form-group input:focus, .form-group select:focus, .form-group textarea:focus { outline: none; border-color: #58a6ff; }
        .status-badge { display: inline-block; padding: 4px 12px; border-radius: 12px; font-size: 12px; }
        .status-ok { background: #238636; color: white; }
        .status-err { background: #da3633; color: white; }
        .status-warn { background: #9e6a03; color: white; }

        /* Chat UI */
        .chat-container { display: flex; flex-direction: column; height: 500px; }
        .chat-messages { flex: 1; overflow-y: auto; padding: 16px 0; border-bottom: 1px solid #30363d; margin-bottom: 16px; }
        .chat-msg { margin-bottom: 12px; padding: 10px 14px; border-radius: 10px; max-width: 80%; white-space: pre-wrap; word-break: break-word; line-height: 1.5; }
        .chat-msg.user { background: #1f6feb; color: white; margin-left: auto; text-align: right; }
        .chat-msg.assistant { background: #21262d; border: 1px solid #30363d; }
        .chat-msg .role-label { font-size: 11px; color: #8b949e; margin-bottom: 4px; }
        .chat-input-row { display: flex; gap: 8px; }
        .chat-input-row input { flex: 1; }
        .typing { color: #8b949e; font-style: italic; }

        /* Login overlay */
        .overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.8); display: flex; align-items: center; justify-content: center; z-index: 1000; }
        .overlay.hidden { display: none; }
        .auth-box { background: #161b22; border: 1px solid #30363d; border-radius: 16px; padding: 32px; width: 380px; }
        .auth-box h2 { margin-bottom: 24px; text-align: center; }
        .auth-box .form-group input { max-width: 100%; }
        .auth-toggle { text-align: center; margin-top: 16px; color: #8b949e; font-size: 13px; }
        .auth-toggle a { color: #58a6ff; cursor: pointer; text-decoration: underline; }

        /* Fade-in animation */
        .page { animation: fadeIn 0.2s ease; }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    </style>
</head>
<body>
    <!-- Auth Overlay -->
    <div id="auth-overlay" class="overlay hidden">
        <div class="auth-box">
            <h2 id="auth-title">登录 ACAS Pro</h2>
            <div id="auth-register-fields" style="display:none">
                <div class="form-group">
                    <label>昵称</label>
                    <input type="text" id="auth-nickname" placeholder="你的昵称">
                </div>
            </div>
            <div class="form-group">
                <label>账号</label>
                <input type="text" id="auth-account" placeholder="账号或邮箱">
            </div>
            <div class="form-group">
                <label>密码</label>
                <input type="password" id="auth-password" placeholder="至少 8 位">
            </div>
            <button class="btn btn-primary" style="width:100%; margin-top: 8px;" onclick="doAuth()">确认</button>
            <div class="auth-toggle">
                <span id="auth-switch-text">没有账号？</span>
                <a id="auth-switch-link" onclick="toggleAuthMode()">注册</a>
            </div>
        </div>
    </div>

    <div class="sidebar">
        <div class="logo">ACAS Pro</div>
        <a class="nav-item active" data-page="dashboard" onclick="showPage('dashboard', this)">📊 仪表盘</a>
        <a class="nav-item" data-page="llm" onclick="showPage('llm', this)">🤖 AI 助手</a>
        <a class="nav-item" data-page="content" onclick="showPage('content', this)">✍️ 内容创作</a>
        <a class="nav-item" data-page="accounts" onclick="showPage('accounts', this)">👥 账号矩阵</a>
        <a class="nav-item" data-page="festival" onclick="showPage('festival', this)">🎉 节日营销</a>
        <a class="nav-item" data-page="forecast" onclick="showPage('forecast', this)">📈 销售预测</a>
        <a class="nav-item" data-page="inventory" onclick="showPage('inventory', this)">📦 库存管理</a>
        <a class="nav-item" data-page="settings" onclick="showPage('settings', this)">⚙️ 系统设置</a>
        <div class="nav-spacer"></div>
        <div class="nav-user" id="nav-user">未登录</div>
    </div>

    <div class="main">
        <!-- Dashboard -->
        <div id="page-dashboard" class="page">
            <div class="header">
                <h1>欢迎回来 👋</h1>
                <p>以下是您的业务概览</p>
            </div>
            <div class="cards" id="dashboard-cards">
                <div class="card"><div class="card-title">总营收</div><div class="card-value success" id="stat-revenue">--</div><div class="card-sub" id="stat-revenue-sub">加载中...</div></div>
                <div class="card"><div class="card-title">活跃订单</div><div class="card-value accent" id="stat-orders">--</div><div class="card-sub" id="stat-orders-sub">&nbsp;</div></div>
                <div class="card"><div class="card-title">库存商品</div><div class="card-value warning" id="stat-inventory">--</div><div class="card-sub" id="stat-inventory-sub">&nbsp;</div></div>
                <div class="card"><div class="card-title">风险预警</div><div class="card-value danger" id="stat-alerts">--</div><div class="card-sub" id="stat-alerts-sub">&nbsp;</div></div>
            </div>
            <div class="section-title">快速操作</div>
            <a class="btn" onclick="showPage('forecast', document.querySelector('[data-page=forecast]'))">📈 查看预测</a>
            <a class="btn" onclick="showPage('inventory', document.querySelector('[data-page=inventory]'))">📦 库存检查</a>
            <a class="btn" onclick="showPage('llm', document.querySelector('[data-page=llm]'))">🤖 AI 助手</a>
            <a class="btn" onclick="showPage('settings', document.querySelector('[data-page=settings]'))">⚙️ 系统设置</a>
        </div>

        <!-- AI Chat -->
        <div id="page-llm" class="page" style="display:none">
            <div class="header">
                <h1>AI 助手</h1>
                <p>与 ACAS Pro AI 对话，获取商业洞察</p>
            </div>
            <div class="content-area">
                <div id="llm-status" style="margin-bottom:16px;"></div>
                <div class="chat-container">
                    <div class="chat-messages" id="chat-messages">
                        <div class="chat-msg assistant">你好！我是 ACAS Pro AI 助手，有什么可以帮你的？</div>
                    </div>
                    <div class="chat-input-row">
                        <input type="text" id="chat-input" placeholder="输入消息..." onkeydown="if(event.key==='Enter')sendChat()">
                        <button class="btn btn-primary" onclick="sendChat()">发送</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Content Creation -->
        <div id="page-content" class="page" style="display:none">
            <div class="header"><h1>内容创作</h1><p>AI 驱动的内容生成引擎</p></div>
            <div class="content-area">
                <div class="form-group">
                    <label>创作平台</label>
                    <select id="content-platform"><option value="xiaohongshu">小红书</option><option value="douyin">抖音</option><option value="weibo">微博</option><option value="wechat">微信公众号</option></select>
                </div>
                <div class="form-group">
                    <label>主题 / 关键词</label>
                    <input type="text" id="content-topic" placeholder="例如：618 大促、新品发布、夏日穿搭">
                </div>
                <div class="form-group">
                    <label>内容风格</label>
                    <select id="content-style"><option value="professional">专业</option><option value="casual">轻松</option><option value="humorous">幽默</option><option value="emotional">走心</option></select>
                </div>
                <button class="btn btn-primary" onclick="generateContent()">✨ AI 生成文案</button>
                <div id="content-result" style="margin-top: 16px;"></div>
            </div>
        </div>

        <!-- Account Matrix -->
        <div id="page-accounts" class="page" style="display:none">
            <div class="header"><h1>账号矩阵</h1><p>多平台账号管理</p></div>
            <div class="content-area">
                <div style="margin-bottom:12px"><button class="btn btn-primary" onclick="loadAccounts()">🔄 刷新</button></div>
                <table id="accounts-table" style="width:100%;border-collapse:collapse;font-size:13px">
                    <thead><tr style="border-bottom:1px solid #30363d">
                        <th style="text-align:left;padding:8px 12px;color:#8b949e">平台</th>
                        <th style="text-align:left;padding:8px 12px;color:#8b949e">账号</th>
                        <th style="text-align:right;padding:8px 12px;color:#8b949e">粉丝</th>
                        <th style="text-align:right;padding:8px 12px;color:#8b949e">内容数</th>
                        <th style="text-align:right;padding:8px 12px;color:#8b949e">总浏览</th>
                        <th style="text-align:center;padding:8px 12px;color:#8b949e">状态</th>
                    </tr></thead>
                    <tbody id="accounts-tbody"><tr><td colspan="6" style="padding:20px;text-align:center;color:#8b949e">加载中...</td></tr></tbody>
                </table>
            </div>
        </div>

        <!-- Festival Marketing -->
        <div id="page-festival" class="page" style="display:none">
            <div class="header"><h1>节日营销</h1><p>节日日历与营销计划</p></div>
            <div class="content-area">
                <div style="margin-bottom:12px"><button class="btn btn-primary" onclick="loadFestivals()">🔄 刷新节日</button> <button class="btn" onclick="askFestival()">🤖 AI 营销建议</button></div>
                <table id="festivals-table" style="width:100%;border-collapse:collapse;font-size:13px">
                    <thead><tr style="border-bottom:1px solid #30363d">
                        <th style="text-align:left;padding:8px 12px;color:#8b949e">节日</th>
                        <th style="text-align:center;padding:8px 12px;color:#8b949e">日期</th>
                        <th style="text-align:center;padding:8px 12px;color:#8b949e">类型</th>
                        <th style="text-align:center;padding:8px 12px;color:#8b949e">重要性</th>
                        <th style="text-align:center;padding:8px 12px;color:#8b949e">持续</th>
                        <th style="text-align:left;padding:8px 12px;color:#8b949e">主题</th>
                    </tr></thead>
                    <tbody id="festivals-tbody"><tr><td colspan="6" style="padding:20px;text-align:center;color:#8b949e">加载中...</td></tr></tbody>
                </table>
                <div id="festival-result" style="margin-top:16px"></div>
            </div>
        </div>

        <!-- Sales Forecast -->
        <div id="page-forecast" class="page" style="display:none">
            <div class="header"><h1>销售预测</h1><p>AI 驱动的销售趋势预测</p></div>
            <div class="content-area">
                <div style="margin-bottom:12px"><button class="btn btn-primary" onclick="loadForecast()">🔄 刷新数据</button> <button class="btn" onclick="askForecast()">🤖 AI 预测</button></div>
                <div id="forecast-chart" style="margin-bottom:16px;font-size:13px;color:#8b949e">加载中...</div>
                <table id="forecast-table" style="width:100%;border-collapse:collapse;font-size:13px">
                    <thead><tr style="border-bottom:1px solid #30363d">
                        <th style="text-align:left;padding:8px 12px;color:#8b949e">日期</th>
                        <th style="text-align:left;padding:8px 12px;color:#8b949e">平台</th>
                        <th style="text-align:right;padding:8px 12px;color:#8b949e">营收</th>
                        <th style="text-align:right;padding:8px 12px;color:#8b949e">订单</th>
                        <th style="text-align:right;padding:8px 12px;color:#8b949e">浏览</th>
                    </tr></thead>
                    <tbody id="forecast-tbody"><tr><td colspan="5" style="padding:20px;text-align:center;color:#8b949e">加载中...</td></tr></tbody>
                </table>
                <div id="forecast-result" style="margin-top:16px"></div>
            </div>
        </div>

        <!-- Inventory -->
        <div id="page-inventory" class="page" style="display:none">
            <div class="header"><h1>库存管理</h1><p>库存优化与补货建议</p></div>
            <div class="content-area">
                <div style="margin-bottom:12px"><button class="btn btn-primary" onclick="loadInventory()">🔄 刷新</button> <button class="btn btn-danger" onclick="loadLowStock()">⚠️ 低库存预警</button> <button class="btn" onclick="askInventory()">🤖 AI 补货建议</button></div>
                <table id="inventory-table" style="width:100%;border-collapse:collapse;font-size:13px">
                    <thead><tr style="border-bottom:1px solid #30363d">
                        <th style="text-align:left;padding:8px 12px;color:#8b949e">商品</th>
                        <th style="text-align:left;padding:8px 12px;color:#8b949e">分类</th>
                        <th style="text-align:right;padding:8px 12px;color:#8b949e">价格</th>
                        <th style="text-align:right;padding:8px 12px;color:#8b949e">库存</th>
                        <th style="text-align:right;padding:8px 12px;color:#8b949e">补货点</th>
                        <th style="text-align:center;padding:8px 12px;color:#8b949e">状态</th>
                    </tr></thead>
                    <tbody id="inventory-tbody"><tr><td colspan="6" style="padding:20px;text-align:center;color:#8b949e">加载中...</td></tr></tbody>
                </table>
                <div id="inventory-result" style="margin-top:16px"></div>
            </div>
        </div>

        <!-- Settings -->
        <div id="page-settings" class="page" style="display:none">
            <div class="header"><h1>系统设置</h1><p>配置 ACAS Pro 参数</p></div>
            <div class="content-area">
                <h3 style="margin-bottom: 20px;">🤖 LLM 配置</h3>
                <form id="llm-form">
                    <div class="form-group">
                        <label>Provider</label>
                        <select id="llm-provider" name="provider">
                            <option value="openai">OpenAI</option>
                            <option value="anthropic">Anthropic</option>
                            <option value="kimi">Kimi</option>
                            <option value="deepseek">DeepSeek</option>
                            <option value="qwen">通义千问</option>
                            <option value="lmstudio">LM Studio</option>
                            <option value="ollama">Ollama</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>API Key</label>
                        <input type="password" id="llm-api-key" name="api_key" placeholder="输入 API Key">
                    </div>
                    <div class="form-group">
                        <label>API Base (可选)</label>
                        <input type="text" id="llm-api-base" name="api_base" placeholder="https://api.example.com/v1">
                    </div>
                    <div class="form-group">
                        <label>Model</label>
                        <input type="text" id="llm-model" name="model" placeholder="gpt-4o, deepseek-chat 等">
                    </div>
                    <button type="submit" class="btn btn-primary">💾 保存配置</button>
                    <button type="button" class="btn" onclick="testLLM()">🧪 测试连接</button>
                </form>
                <div id="llm-result" style="margin-top: 16px;"></div>
            </div>
        </div>
    </div>

    <script>
        function escapeHtml(str) {
            if (str == null) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#39;');
        }

        // ── State ──
        let authToken = localStorage.getItem('acas_token') || '';
        let chatHistory = [];
        let isRegisterMode = false;

        // ── Init ──
        (function init() {
            loadCurrentConfig();
            if (authToken) {
                document.getElementById('auth-overlay').classList.add('hidden');
                loadDashboard();
                fetchUserInfo();
            } else {
                document.getElementById('auth-overlay').classList.remove('hidden');
            }
        })();

        // ── Auth ──
        function toggleAuthMode() {
            isRegisterMode = !isRegisterMode;
            document.getElementById('auth-title').textContent = isRegisterMode ? '注册 ACAS Pro' : '登录 ACAS Pro';
            document.getElementById('auth-register-fields').style.display = isRegisterMode ? 'block' : 'none';
            document.getElementById('auth-switch-text').textContent = isRegisterMode ? '已有账号？' : '没有账号？';
            document.getElementById('auth-switch-link').textContent = isRegisterMode ? '登录' : '注册';
        }

        function getCsrfToken() {
            const match = document.cookie.match(/csrf_token=([0-9a-f]{64})/);
            return match ? match[1] : '';
        }

        async function doAuth() {
            const account = document.getElementById('auth-account').value.trim();
            const password = document.getElementById('auth-password').value.trim();
            const nickname = document.getElementById('auth-nickname').value.trim();
            if (!account || !password) return alert('请输入账号和密码');

            const endpoint = isRegisterMode ? '/api/auth/register' : '/api/auth/login';
            const body = isRegisterMode ? {account, password, nickname} : {account, password};

            const res = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRF-Token': getCsrfToken(),
                },
                body: JSON.stringify(body),
                credentials: 'include',
            });
            const data = await res.json();
            if (data.success) {
                authToken = data.token;
                localStorage.setItem('acas_token', authToken);
                document.getElementById('auth-overlay').classList.add('hidden');
                loadDashboard();
                fetchUserInfo();
            } else {
                alert(data.error || '操作失败');
            }
        }

        async function fetchUserInfo() {
            try {
                const res = await fetch('/api/auth/me', {headers: {'Authorization': 'Bearer ' + authToken}});
                const data = await res.json();
                if (data.account) {
                    document.getElementById('nav-user').textContent = '👤 ' + data.account;
                }
            } catch(e) {}
        }

        function authHeaders() {
            return {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + authToken,
                'X-CSRF-Token': getCsrfToken(),
            };
        }

        // ── Navigation ──
        function showPage(page, el) {
            document.querySelectorAll('.page').forEach(p => p.style.display = 'none');
            document.getElementById('page-' + page).style.display = 'block';
            document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
            if (el) el.classList.add('active');
            if (page === 'llm') updateLLMStatus();
            if (page === 'accounts') loadAccounts();
            if (page === 'festival') loadFestivals();
            if (page === 'forecast') loadForecast();
            if (page === 'inventory') loadInventory();
        }

        // ── Dashboard ──
        async function loadDashboard() {
            try {
                const res = await fetch('/api/dashboard/stats', {headers: authHeaders()});
                const s = await res.json();
                document.getElementById('stat-revenue').textContent = '¥' + (s.revenue || 0).toLocaleString();
                document.getElementById('stat-revenue-sub').textContent = s.llm_enabled ? 'AI 已启用 · ' + s.llm_provider : 'AI 未启用';
                document.getElementById('stat-orders').textContent = (s.active_orders || 0).toLocaleString();
                document.getElementById('stat-inventory').textContent = (s.inventory || 0).toLocaleString();
                document.getElementById('stat-inventory-sub').textContent = (s.low_stock || 0) > 0 ? (s.low_stock + '项需补货') : '库存充足';
                document.getElementById('stat-alerts').textContent = s.risk_alerts || 0;
                document.getElementById('stat-alerts-sub').textContent = (s.risk_alerts || 0) > 0 ? '需要关注' : '一切正常';
            } catch(e) {
                document.getElementById('stat-revenue-sub').textContent = '数据加载失败';
            }
        }

        // ── LLM Status ──
        function updateLLMStatus() {
            const el = document.getElementById('llm-status');
            const provider = '{{ llm_provider | safe }}';
            const enabled = {{ 'true' if llm_enabled else 'false' }};
            if (enabled) {
                el.innerHTML = '<span class="status-badge status-ok">已启用 · ' + escapeHtml(provider) + '</span>';
            } else {
                el.innerHTML = '<span class="status-badge status-err">未启用</span> 请先在 <a onclick="showPage(\'settings\', document.querySelector(\'[data-page=settings]\'))" style="color:#58a6ff;cursor:pointer">系统设置</a> 中配置 API Key';
            }
        }

        // ── Chat ──
        async function sendChat() {
            const input = document.getElementById('chat-input');
            const msg = input.value.trim();
            if (!msg) return;
            input.value = '';

            // Show user message
            appendChat('user', msg);
            chatHistory.push({role: 'user', content: msg});

            // Show typing indicator
            const typingEl = appendChat('assistant', '思考中...', true);

            try {
                const res = await fetch('/api/llm/chat', {
                    method: 'POST',
                    headers: authHeaders(),
                    body: JSON.stringify({message: msg, history: chatHistory.slice(-10)})
                });
                const data = await res.json();
                typingEl.remove();
                if (data.success) {
                    appendChat('assistant', data.content);
                    chatHistory.push({role: 'assistant', content: data.content});
                } else {
                    appendChat('assistant', '❌ ' + (data.error || '请求失败'));
                }
            } catch(e) {
                typingEl.remove();
                appendChat('assistant', '❌ 网络错误: ' + escapeHtml(String(e.message)));
            }
        }

        function appendChat(role, content, isTyping) {
            const container = document.getElementById('chat-messages');
            const div = document.createElement('div');
            div.className = 'chat-msg ' + role + (isTyping ? ' typing' : '');
            div.textContent = content;
            container.appendChild(div);
            container.scrollTop = container.scrollHeight;
            return div;
        }

        // ── Content Generation ──
        async function generateContent() {
            const platform = document.getElementById('content-platform').value;
            const topic = document.getElementById('content-topic').value.trim();
            const style = document.getElementById('content-style').value;
            if (!topic) return alert('请输入主题');
            const el = document.getElementById('content-result');
            el.innerHTML = '<span class="typing">AI 正在生成...</span>';
            const prompt = `请为${platform}平台创作一篇关于"${topic}"的内容，风格：${style}。要求：标题吸引人、内容有干货、符合平台调性、包含合适的话题标签。`;
            const res = await chatWithAI(prompt);
            el.innerHTML = '<div style="white-space:pre-wrap; line-height:1.8;">' + escapeHtml(res) + '</div>';
        }

        // ── Festival ──
        async function loadFestivals() {
            const el = document.getElementById('festivals-tbody');
            el.innerHTML = '<tr><td colspan="6" style="padding:20px;text-align:center;color:#8b949e">加载中...</td></tr>';
            try {
                const res = await fetch('/api/festivals', {headers: authHeaders()});
                const data = await res.json();
                if (!data.success || !data.festivals || data.festivals.length === 0) {
                    el.innerHTML = '<tr><td colspan="6" style="padding:20px;text-align:center;color:#8b949e">暂无节日数据</td></tr>';
                    return;
                }
                el.innerHTML = data.festivals.map(f => {
                    const imp = {5:'&#9733;&#9733;&#9733;', 4:'&#9733;&#9733;&#9733;&#9733;', 3:'&#9733;&#9733;&#9733;', 2:'&#9733;&#9733;', 1:'&#9733;'}[f.importance] || '-';
                    const date = `${f.month}月${f.day}日`;
                    const themes = f.themes ? f.themes.substring(0,30) : '';
                    return '<tr style="border-bottom:1px solid #21262d">'
                        + `<td style="padding:8px 12px">${escapeHtml(String(f.name))}</td>`
                        + `<td style="padding:8px 12px;text-align:center">${date}</td>`
                        + `<td style="padding:8px 12px;text-align:center">${escapeHtml(String(f.festival_type || '-'))}</td>`
                        + `<td style="padding:8px 12px;text-align:center">${imp}</td>`
                        + `<td style="padding:8px 12px;text-align:center">${f.duration_days || 0}天</td>`
                        + `<td style="padding:8px 12px">${escapeHtml(String(themes))}${themes?'...':''}</td>`
                        + '</tr>';
                }).join('');
            } catch(e) {
                el.innerHTML = '<tr><td colspan="6" style="padding:20px;color:#f85149">加载失败: ' + escapeHtml(String(e.message)) + '</td></tr>';
            }
        }

        async function askFestival() {
            await loadFestivals();
            const q = document.getElementById('festival-query').value.trim();
            if (!q) return;
            const el = document.getElementById('festival-result');
            el.innerHTML = '<span class="typing">AI 分析中...</span>';
            const res = await chatWithAI(`关于节日营销：${q}。请提供节日信息和营销建议。`);
            el.innerHTML = '<div style="white-space:pre-wrap; line-height:1.8; margin-top:12px; padding:12px; background:#21262d; border-radius:8px;">' + escapeHtml(res) + '</div>';
        }

        // ── Forecast ──
        async function loadForecast() {
            const tbody = document.getElementById('forecast-tbody');
            const chartEl = document.getElementById('forecast-chart');
            tbody.innerHTML = '<tr><td colspan="5" style="padding:20px;text-align:center;color:#8b949e">加载中...</td></tr>';
            chartEl.innerHTML = '加载中...';
            try {
                const res = await fetch('/api/forecast/daily', {headers: authHeaders()});
                const data = await res.json();
                if (!data.success || !data.data || data.data.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="5" style="padding:20px;text-align:center;color:#8b949e">暂无数据</td></tr>';
                    chartEl.innerHTML = '近30天无销售数据';
                    return;
                }
                const rows = data.data;
                let totalRevenue = 0;
                rows.forEach(r => { totalRevenue += (r.revenue || 0); });
                chartEl.innerHTML = `近30天共 <b style="color:#3fb950">${rows.length}</b> 条记录，总营收 <b style="color:#3fb950">¥${totalRevenue.toLocaleString()}</b>`;
                tbody.innerHTML = rows.slice(-20).map(r => {
                    const rev = (r.revenue || 0).toLocaleString();
                    return '<tr style="border-bottom:1px solid #21262d">'
                        + `<td style="padding:8px 12px">${escapeHtml(String(r.date || '-'))}</td>`
                        + `<td style="padding:8px 12px">${escapeHtml(String(r.platform || '-'))}</td>`
                        + `<td style="padding:8px 12px;text-align:right;color:#3fb950">¥${rev}</td>`
                        + `<td style="padding:8px 12px;text-align:right">${(r.orders || 0)}</td>`
                        + `<td style="padding:8px 12px;text-align:right">${(r.views || 0).toLocaleString()}</td>`
                        + '</tr>';
                }).join('');
            } catch(e) {
                tbody.innerHTML = '<tr><td colspan="5" style="padding:20px;color:#f85149">加载失败: ' + escapeHtml(String(e.message)) + '</td></tr>';
            }
        }

        async function askForecast() {
            await loadForecast();
            const q = document.getElementById('forecast-query').value.trim();
            if (!q) return;
            const el = document.getElementById('forecast-result');
            el.innerHTML = '<span class="typing">AI 分析中...</span>';
            const res = await chatWithAI(`关于销售预测：${q}。请基于一般商业知识给出分析和建议。`);
            el.innerHTML = '<div style="white-space:pre-wrap; line-height:1.8; margin-top:12px; padding:12px; background:#21262d; border-radius:8px;">' + escapeHtml(res) + '</div>';
        }

        // ── Inventory ──
        async function loadInventory() {
            const tbody = document.getElementById('inventory-tbody');
            tbody.innerHTML = '<tr><td colspan="6" style="padding:20px;text-align:center;color:#8b949e">加载中...</td></tr>';
            try {
                const res = await fetch('/api/products', {headers: authHeaders()});
                const data = await res.json();
                if (!data.success || !data.products || data.products.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="padding:20px;text-align:center;color:#8b949e">暂无商品数据</td></tr>';
                    return;
                }
                tbody.innerHTML = data.products.map(p => {
                    const status = p.stock_quantity === 0 ? '<span style="color:#f85149">缺货</span>'
                        : p.stock_quantity <= (p.reorder_point || 0) ? '<span style="color:#d29922">预警</span>'
                        : '<span style="color:#3fb950">正常</span>';
                    return '<tr style="border-bottom:1px solid #21262d">'
                        + `<td style="padding:8px 12px">${escapeHtml(String(p.name || '-'))}</td>`
                        + `<td style="padding:8px 12px">${escapeHtml(String(p.category || '-'))}</td>`
                        + `<td style="padding:8px 12px;text-align:right">¥${(p.price || 0).toLocaleString()}</td>`
                        + `<td style="padding:8px 12px;text-align:right">${p.stock_quantity || 0}</td>`
                        + `<td style="padding:8px 12px;text-align:right">${p.reorder_point || 0}</td>`
                        + `<td style="padding:8px 12px;text-align:center">${status}</td>`
                        + '</tr>';
                }).join('');
            } catch(e) {
                tbody.innerHTML = '<tr><td colspan="6" style="padding:20px;color:#f85149">加载失败: ' + escapeHtml(String(e.message)) + '</td></tr>';
            }
        }

        async function loadLowStock() {
            const tbody = document.getElementById('inventory-tbody');
            tbody.innerHTML = '<tr><td colspan="6" style="padding:20px;text-align:center;color:#8b949e">加载中...</td></tr>';
            try {
                const res = await fetch('/api/products/low-stock', {headers: authHeaders()});
                const data = await res.json();
                if (!data.success || !data.products || data.products.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="padding:20px;text-align:center;color:#3fb950">库存充足，无需补货</td></tr>';
                    return;
                }
                tbody.innerHTML = '<tr><td colspan="6" style="padding:8px 12px;color:#d29922;font-weight:bold">⚠ 低库存预警 (' + escapeHtml(String(data.products.length)) + ' 项)</td></tr>'
                    + data.products.map(p => {
                    return '<tr style="border-bottom:1px solid #21262d; background:#1a1500">'
                        + `<td style="padding:8px 12px">${escapeHtml(String(p.name || '-'))}</td>`
                        + `<td style="padding:8px 12px">${escapeHtml(String(p.category || '-'))}</td>`
                        + `<td style="padding:8px 12px;text-align:right">¥${(p.price || 0).toLocaleString()}</td>`
                        + `<td style="padding:8px 12px;text-align:right;color:#f85149">${p.stock_quantity || 0}</td>`
                        + `<td style="padding:8px 12px;text-align:right">${p.reorder_point || 0}</td>`
                        + `<td style="padding:8px 12px;text-align:center;color:#f85149">缺 ${p.deficit || 0} 件</td>`
                        + '</tr>';
                }).join('');
            } catch(e) {
                tbody.innerHTML = '<tr><td colspan="6" style="padding:20px;color:#f85149">加载失败: ' + escapeHtml(String(e.message)) + '</td></tr>';
            }
        }

        async function loadAccounts() {
            const tbody = document.getElementById('accounts-tbody');
            tbody.innerHTML = '<tr><td colspan="6" style="padding:20px;text-align:center;color:#8b949e">加载中...</td></tr>';
            try {
                const res = await fetch('/api/accounts', {headers: authHeaders()});
                const data = await res.json();
                if (!data.success || !data.accounts || data.accounts.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="6" style="padding:20px;text-align:center;color:#8b949e">暂无账号数据</td></tr>';
                    return;
                }
                tbody.innerHTML = data.accounts.map(a => {
                    const status = a.status === 'active' ? '<span style="color:#3fb950">活跃</span>'
                        : a.status === 'inactive' ? '<span style="color:#8b949e">停用</span>'
                        : '<span style="color:#d29922">' + escapeHtml(String(a.status || '-')) + '</span>';
                    return '<tr style="border-bottom:1px solid #21262d">'
                        + `<td style="padding:8px 12px">${escapeHtml(String(a.platform || '-'))}</td>`
                        + `<td style="padding:8px 12px">${escapeHtml(String(a.account_name || '-'))}</td>`
                        + `<td style="padding:8px 12px;text-align:right">${(a.followers || 0).toLocaleString()}</td>`
                        + `<td style="padding:8px 12px;text-align:right">${a.content_count || 0}</td>`
                        + `<td style="padding:8px 12px;text-align:right">${(a.total_views || 0).toLocaleString()}</td>`
                        + `<td style="padding:8px 12px;text-align:center">${status}</td>`
                        + '</tr>';
                }).join('');
            } catch(e) {
                tbody.innerHTML = '<tr><td colspan="6" style="padding:20px;color:#f85149">加载失败: ' + escapeHtml(String(e.message)) + '</td></tr>';
            }
        }

        async function askInventory() {
            await loadInventory();
            const q = document.getElementById('inventory-query').value.trim();
            if (!q) return;
            const el = document.getElementById('inventory-result');
            el.innerHTML = '<span class="typing">AI 分析中...</span>';
            const res = await chatWithAI(`关于库存管理：${q}。请给出库存优化建议。`);
            el.innerHTML = '<div style="white-space:pre-wrap; line-height:1.8; margin-top:12px; padding:12px; background:#21262d; border-radius:8px;">' + escapeHtml(res) + '</div>';
        }

        // ── AI Helper ──
        async function chatWithAI(message) {
            try {
                const res = await fetch('/api/llm/chat', {
                    method: 'POST',
                    headers: authHeaders(),
                    body: JSON.stringify({message, system: '你是 ACAS Pro 商业智能助手，专精于电商运营、内容营销、库存管理和销售预测。回答要专业、实用、简洁。'})
                });
                const data = await res.json();
                return data.success ? escapeHtml(data.content) : '❌ ' + escapeHtml(data.error || '请求失败');
            } catch(e) {
                return '❌ 网络错误: ' + escapeHtml(e.message);
            }
        }

        function escapeHtml(str) {
            const div = document.createElement('div');
            div.textContent = str;
            return div.innerHTML;
        }

        // ── Settings ──
        function loadCurrentConfig() {
            // Pre-fill from server-rendered values
            const provider = '{{ llm_provider }}';
            const keyMask = '{{ llm_key_mask }}';
            if (provider) document.getElementById('llm-provider').value = provider;
        }

        document.getElementById('llm-form').onsubmit = async function(e) {
            e.preventDefault();
            const data = {
                provider: document.getElementById('llm-provider').value,
                api_key: document.getElementById('llm-api-key').value,
                api_base: document.getElementById('llm-api-base').value,
                model: document.getElementById('llm-model').value,
            };
            const res = await fetch('/api/llm/config', {
                method: 'POST',
                headers: authHeaders(),
                body: JSON.stringify(data)
            });
            const result = await res.json();
            document.getElementById('llm-result').innerHTML =
                '<span class="status-badge status-' + (result.success ? 'ok' : 'err') + '">' +
                (result.success ? '✅ 保存成功 · ' + result.provider : '❌ ' + (result.error || '保存失败')) + '</span>';
        };

        async function testLLM() {
            const el = document.getElementById('llm-result');
            el.innerHTML = '<span class="typing">测试中...</span>';
            const res = await fetch('/api/llm/test', {headers: authHeaders()});
            const result = await res.json();
            el.innerHTML = '<span class="status-badge status-' + (result.success ? 'ok' : 'err') + '">' +
                (result.success ? '✅ 连接成功 · ' + escapeHtml(String(result.message)) : '❌ ' + escapeHtml(String(result.error))) + '</span>';
        }

    </script>
</body>
</html>
'''


@app.route('/')
def index():
    llm_provider = config().llm.provider if config().llm.enabled else '未启用'
    llm_key = config().llm.api_key
    llm_key_mask = llm_key[:8] + '****' if llm_key and len(llm_key) > 8 else '未设置'
    return render_template_string(
        DASHBOARD_HTML,
        llm_provider=llm_provider,
        llm_key_mask=llm_key_mask,
        llm_enabled=config().llm.enabled,
    )


if __name__ == '__main__':
    print("=" * 50)
    print("ACAS Pro Web 版本")
    print("=" * 50)
    llm_status = config().llm.provider if config().llm.enabled else 'not configured'
    print(f"LLM: {llm_status}")
    print(f"访问地址: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
