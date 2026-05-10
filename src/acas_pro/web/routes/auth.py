"""Authentication routes for ACAS Pro Web"""
from flask import Blueprint, request, jsonify, g
from datetime import datetime, timezone

from acas_pro.core.security import password_validator as pv, rate_limiter, JWTManager
from acas_pro.core.config import config
from acas_pro.services.user_service import user_service
from acas_pro.core.logging import get_logger

logger = get_logger(__name__)
bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def generate_token(user_id: str, account: str) -> str:
    """Generate JWT using JWTManager (unified auth system)."""
    return JWTManager.generate_token(user_id, extra_claims={'account': account})


def verify_token(token: str) -> dict | None:
    """
    Verify JWT using JWTManager. Supports both:
    - New tokens (JWTManager, claim='sub')
    - Old tokens (legacy, claim='user_id') for backward compatibility
    """
    import jwt
    
    payload = JWTManager.verify_token(token, expected_type='access')
    if payload:
        return payload
    # Fallback: try legacy format
    try:
        JWT_SECRET = config.security.secret_key
        payload = jwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        if payload.get('user_id'):
            return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        pass
    return None


@bp.route('/register', methods=['POST'])
def auth_register():
    """Register a new user account"""
    data = request.json or {}
    account = data.get('account', '').strip()
    password = data.get('password', '').strip()
    nickname = data.get('nickname', '').strip()

    if not account or not password:
        return jsonify({'error': 'account and password are required'}), 400
    
    # Enforce strong password policy
    is_valid, pw_msg = pv.PasswordValidator.validate(password)
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
    return jsonify({
        'success': True,
        'token': token,
        'user': {'user_id': profile.id, 'account': profile.account, 'nickname': profile.nickname}
    })


@bp.route('/login', methods=['POST'])
def auth_login():
    """Login with account and password"""
    data = request.json or {}
    account = data.get('account', '').strip()
    password = data.get('password', '').strip()

    if not account or not password:
        return jsonify({'error': 'account and password are required'}), 400

    # Rate limit login attempts: 20 per 10 minutes per account
    rate_key = f"login:{account}"
    if not rate_limiter.is_allowed(rate_key, max_attempts=20, window_seconds=600):
        return jsonify({'error': 'Too many login attempts. Please try again later.'}), 429
    rate_limiter.record_attempt(rate_key)

    ok, msg, profile = user_service.login(account=account, password=password)
    if not ok:
        return jsonify({'error': msg}), 401

    token = generate_token(profile.id, account)
    return jsonify({
        'success': True,
        'token': token,
        'user': {'user_id': profile.id, 'account': profile.account, 'nickname': profile.nickname}
    })


@bp.route('/me', methods=['GET'])
def auth_me():
    """Get current user info"""
    user = g.user
    return jsonify({'user_id': user['user_id'], 'account': user['account']})
