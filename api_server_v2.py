#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro API Server V2 - 生产级安全加固版本

改进点:
- JWT 密钥外部注入
- 强制首次登录修改密码
- RBAC 权限控制
- 分级速率限制
- 结构化日志

版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
All Rights Reserved.
"""

import os
import sys
import json
import logging
from datetime import datetime
from functools import wraps

from flask import Flask, request, jsonify, g
from flask_cors import CORS

# 添加路径
sys.path.insert(0, os.path.dirname(__file__))

# 导入安全模块
from security import (
    init_security, require_auth, require_permission,
    rate_limit, rate_limit_exempt, RateLimitTier
)
from security.auth_v2 import get_auth_manager, UserRole
from config import get_config
from database import get_db

# 配置结构化日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/api.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 确保日志目录存在
os.makedirs('logs', exist_ok=True)

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# CORS 配置 - 生产环境限制来源
CORS(app, resources={
    r"/api/*": {
        "origins": os.getenv('ALLOWED_ORIGINS', 'http://localhost:8080').split(','),
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
})


# ============ 中间件 ============

@app.before_request
def before_request():
    """请求前处理"""
    g.request_id = os.urandom(8).hex()
    g.start_time = datetime.utcnow()
    
    # 记录请求日志
    logger.info(f"[{g.request_id}] {request.method} {request.path} - {request.remote_addr}")


@app.after_request
def after_request(response):
    """请求后处理"""
    duration = (datetime.utcnow() - g.start_time).total_seconds() * 1000
    
    # 添加安全响应头
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['X-Request-ID'] = g.request_id
    
    logger.info(f"[{g.request_id}] Response: {response.status_code} ({duration:.2f}ms)")
    
    return response


# ============ 错误处理 ============

@app.errorhandler(400)
def bad_request(error):
    return jsonify({
        "success": False,
        "error": {"code": "BAD_REQUEST", "message": str(error.description)}
    }), 400


@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": {"code": "NOT_FOUND", "message": "资源不存在"}
    }), 404


@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal error: {error}", exc_info=True)
    return jsonify({
        "success": False,
        "error": {"code": "INTERNAL_ERROR", "message": "服务器内部错误"}
    }), 500


# ============ 公开端点 ============

@app.route('/health', methods=['GET'])
@rate_limit_exempt
def health_check():
    """健康检查 - 豁免限流"""
    return jsonify({
        "status": "healthy",
        "version": "2.1.0",
        "timestamp": datetime.utcnow().isoformat()
    })


@app.route('/api/v2/auth/login', methods=['POST'])
@rate_limit(RateLimitTier.ANONYMOUS)
def login():
    """用户登录"""
    data = request.get_json()
    
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({
            "success": False,
            "error": {"code": "MISSING_CREDENTIALS", "message": "缺少用户名或密码"}
        }), 400
    
    auth_mgr = get_auth_manager()
    user = auth_mgr.authenticate(data['username'], data['password'])
    
    if not user:
        logger.warning(f"登录失败: {data['username']} from {request.remote_addr}")
        return jsonify({
            "success": False,
            "error": {"code": "INVALID_CREDENTIALS", "message": "用户名或密码错误"}
        }), 401
    
    token = auth_mgr.generate_token(user)
    
    logger.info(f"用户登录成功: {user.username}")
    
    return jsonify({
        "success": True,
        "data": {
            "token": token,
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role.value,
                "password_changed": user.password_changed
            }
        }
    })


@app.route('/api/v2/auth/change-password', methods=['POST'])
@require_auth
def change_password():
    """修改密码"""
    data = request.get_json()
    
    if not data or 'new_password' not in data:
        return jsonify({
            "success": False,
            "error": {"code": "MISSING_PASSWORD", "message": "缺少新密码"}
        }), 400
    
    try:
        auth_mgr = get_auth_manager()
        auth_mgr.change_password(g.user_id, data['new_password'])
        
        # 重新生成 token（标记密码已修改）
        user = auth_mgr._users.get(g.user_id)
        new_token = auth_mgr.generate_token(user)
        
        logger.info(f"用户修改密码: {g.user_id}")
        
        return jsonify({
            "success": True,
            "message": "密码修改成功",
            "data": {"token": new_token}
        })
        
    except ValueError as e:
        return jsonify({
            "success": False,
            "error": {"code": "WEAK_PASSWORD", "message": str(e)}
        }), 400


# ============ 受保护端点 ============

@app.route('/api/v2/users/me', methods=['GET'])
@require_auth
@rate_limit()
def get_current_user():
    """获取当前用户信息"""
    auth_mgr = get_auth_manager()
    user = auth_mgr._users.get(g.user_id)
    
    if not user:
        return jsonify({
            "success": False,
            "error": {"code": "USER_NOT_FOUND", "message": "用户不存在"}
        }), 404
    
    return jsonify({
        "success": True,
        "data": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "permissions": [
                {"resource": p.resource, "action": p.action, "scope": p.scope}
                for p in user.permissions
            ]
        }
    })


@app.route('/api/v2/content', methods=['GET'])
@require_auth
@require_permission('content', 'read')
@rate_limit()
def list_content():
    """获取内容列表"""
    db = get_db()
    contents = db.query_all("SELECT * FROM contents WHERE created_by = ?", (g.user_id,))
    
    return jsonify({
        "success": True,
        "data": contents
    })


@app.route('/api/v2/content', methods=['POST'])
@require_auth
@require_permission('content', 'create')
@rate_limit()
def create_content():
    """创建内容"""
    data = request.get_json()
    
    if not data or 'title' not in data:
        return jsonify({
            "success": False,
            "error": {"code": "MISSING_TITLE", "message": "缺少标题"}
        }), 400
    
    db = get_db()
    content_id = db.execute(
        "INSERT INTO contents (title, body, created_by, created_at) VALUES (?, ?, ?, ?)",
        (data['title'], data.get('body', ''), g.user_id, datetime.utcnow().isoformat())
    )
    
    logger.info(f"内容创建: {content_id} by {g.user_id}")
    
    return jsonify({
        "success": True,
        "data": {"id": content_id}
    }), 201


@app.route('/api/v2/admin/users', methods=['GET'])
@require_auth
@require_permission('user', 'read')
@rate_limit(RateLimitTier.ADMIN)
def list_users():
    """管理员：获取用户列表"""
    auth_mgr = get_auth_manager()
    users = []
    
    for uid, user in auth_mgr._users.items():
        users.append({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active
        })
    
    return jsonify({
        "success": True,
        "data": users
    })


# ============ 启动 ============

def init_app():
    """初始化应用"""
    # 初始化安全体系
    init_security()
    logger.info("安全体系初始化完成")
    
    # 初始化数据库
    db = get_db()
    logger.info("数据库初始化完成")
    
    return app


if __name__ == '__main__':
    # 生产环境应使用 Gunicorn/uWSGI
    # gunicorn -w 4 -b 0.0.0.0:5000 api_server_v2:app
    
    init_app()
    
    ssl_context = None
    cert_file = os.getenv('SSL_CERT_FILE')
    key_file = os.getenv('SSL_KEY_FILE')
    
    if cert_file and key_file and os.path.exists(cert_file) and os.path.exists(key_file):
        ssl_context = (cert_file, key_file)
        logger.info(f"SSL 已启用: {cert_file}")
    else:
        logger.warning("SSL 未配置，使用 HTTP（生产环境不推荐）")
    
    app.run(
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', 5000)),
        ssl_context=ssl_context,
        debug=False
    )
