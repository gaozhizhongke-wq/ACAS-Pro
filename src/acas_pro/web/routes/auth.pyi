from typing import Dict, Optional, Tuple, Any
from flask import Response

# ... existing imports ...


def auth_register() -> Tuple[Response, int]:
    """Register a new user account"""
    data: Dict[str, Any] = request.json or {}
    account: str = data.get('account', '').strip()
    password: str = data.get('password', '').strip()
    nickname: str = data.get('nickname', '').strip()

    if not account or not password:
        return jsonify({'error': 'account and password are required'}), 400

    # ... rest of function ...


def auth_login() -> Tuple[Response, int]:
    """Login with account and password"""
    data: Dict[str, Any] = request.json or {}
    account: str = data.get('account', '').strip()
    password: str = data.get('password', '').strip()

    if not account or not password:
        return jsonify({'error': 'account and password are required'}), 400

    # ... rest of function ...


def auth_me() -> Tuple[Response, int] | Response:
    """Get current user info (requires authentication)"""
    user: Optional[Dict[str, Any]] = g.get('user') if hasattr(g, 'user') else None
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    return jsonify({'user_id': user['user_id'], 'account': user['account']})
