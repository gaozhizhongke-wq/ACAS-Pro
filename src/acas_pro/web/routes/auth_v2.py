"""ACAS Pro - Auth Routes v2 (real implementation)"""
from flask import Blueprint, request, jsonify, g
from acas_pro.core.logging import get_logger

logger = get_logger(__name__)
bp = Blueprint('auth_v2', __name__, url_prefix='/api/v2/auth')


@bp.route('/register', methods=['POST'])
def register():
    """Register user - delegates to auth v1 logic"""
    from acas_pro.web.routes.auth import auth_register
    return auth_register()


@bp.route('/login', methods=['POST'])
def login():
    """Login user - delegates to auth v1 logic"""
    from acas_pro.web.routes.auth import auth_login
    return auth_login()


@bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current user info (requires authentication)"""
    user = g.get('user') if hasattr(g, 'user') else None
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    return jsonify({'success': True, 'user': {'id': user['user_id'], 'account': user['account']}})
