"""ACAS Pro - Auth Routes v2"""
from flask import Blueprint, jsonify


bp = Blueprint('auth_v2', __name__, url_prefix='/api/v2/auth')


@bp.route('/register', methods=['POST'])
def register():
    """Register user"""
    return jsonify({"success": True, "message": "Registered"})


@bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    return jsonify({"success": True, "token": "test-token"})


@bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current user"""
    return jsonify({"success": True, "user": {"id": "1", "account": "test"}})
