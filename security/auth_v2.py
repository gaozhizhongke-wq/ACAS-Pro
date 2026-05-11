#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
认证授权模块 V2 - 生产级 JWT + RBAC 实现

版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
All Rights Reserved.
"""

import os
import re
import jwt
import logging
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from flask import request, g, jsonify

from .key_manager import get_key_manager

logger = logging.getLogger(__name__)


class UserRole(Enum):
    """用户角色枚举"""
    ADMIN = "admin"           # 超级管理员
    OPERATOR = "operator"     # 操作员
    VIEWER = "viewer"         # 只读用户
    AUDITOR = "auditor"       # 审计员
    SERVICE = "service"       # 服务账号


@dataclass
class Permission:
    """权限定义"""
    resource: str      # 资源: user, content, account, analytics, system
    action: str        # 操作: create, read, update, delete, execute
    scope: str = "own"  # 范围: own(自己的), team(团队的), all(全部)


# 角色权限映射
ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.ADMIN: [
        Permission("*", "*", "all")  # 所有权限
    ],
    UserRole.OPERATOR: [
        Permission("content", "*", "own"),
        Permission("account", "*", "own"),
        Permission("analytics", "read", "team"),
        Permission("user", "read", "own"),
        Permission("user", "update", "own"),
    ],
    UserRole.VIEWER: [
        Permission("content", "read", "team"),
        Permission("account", "read", "team"),
        Permission("analytics", "read", "team"),
    ],
    UserRole.AUDITOR: [
        Permission("*", "read", "all"),
        Permission("audit", "*", "all"),
    ],
    UserRole.SERVICE: [
        Permission("api", "execute", "all"),
    ]
}


@dataclass
class User:
    """用户对象"""
    id: str
    username: str
    email: str
    role: UserRole
    team_id: Optional[str] = None
    is_active: bool = True
    password_changed: bool = False  # 是否已修改默认密码
    permissions: List[Permission] = field(default_factory=list)
    
    def has_permission(self, resource: str, action: str, scope: str = "own") -> bool:
        """检查是否有指定权限"""
        for perm in self.permissions:
            # 通配符匹配
            if perm.resource == "*" or perm.resource == resource:
                if perm.action == "*" or perm.action == action:
                    if perm.scope == "all" or perm.scope == scope:
                        return True
        return False


class AuthManager:
    """认证管理器"""
    
    def __init__(self):
        self.key_manager = get_key_manager()
        self._users: Dict[str, User] = {}  # 内存存储，生产环境应使用数据库
        self._init_default_users()
    
    def _init_default_users(self):
        """初始化默认用户（首次启动）"""
        # 检查是否已存在用户
        if not self._users:
            # 创建默认管理员（强制首次登录修改密码）
            admin = User(
                id="admin_001",
                username="admin",
                email="admin@acas.local",
                role=UserRole.ADMIN,
                is_active=True,
                password_changed=False,
                permissions=ROLE_PERMISSIONS[UserRole.ADMIN]
            )
            self._users["admin"] = admin
            logger.warning("默认管理员已创建，请立即修改密码！")
    
    def _get_jwt_secret(self) -> str:
        """获取 JWT 密钥"""
        secret = self.key_manager.get_jwt_secret("jwt_secret")
        if not secret:
            raise RuntimeError("JWT 密钥未初始化")
        return secret
    
    def generate_token(self, user: User, expires_hours: int = 24) -> str:
        """
        生成 JWT Token
        
        Args:
            user: 用户对象
            expires_hours: 过期小时数
        """
        payload = {
            "sub": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "team_id": user.team_id,
            "password_changed": user.password_changed,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(hours=expires_hours),
            "jti": os.urandom(16).hex()  # JWT ID，用于撤销
        }
        
        token = jwt.encode(payload, self._get_jwt_secret(), algorithm="HS256")
        return token
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """验证 JWT Token"""
        try:
            payload = jwt.decode(token, self._get_jwt_secret(), algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT Token 已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT Token 无效: {e}")
            return None
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        用户认证
        
        注意：这是简化版，生产环境应使用 bcrypt/argon2 等密码哈希
        """
        # TODO: 集成数据库查询和 bcrypt 验证
        if username == "admin" and password == "admin123":
            return self._users.get("admin")
        return None
    
    def change_password(self, user_id: str, new_password: str) -> bool:
        """
        修改密码
        
        密码策略:
        - 至少 8 位
        - 包含大小写字母
        - 包含数字
        - 包含特殊字符
        """
        # 密码强度检查
        if len(new_password) < 8:
            raise ValueError("密码长度至少 8 位")
        
        if not re.search(r'[A-Z]', new_password):
            raise ValueError("密码必须包含大写字母")
        
        if not re.search(r'[a-z]', new_password):
            raise ValueError("密码必须包含小写字母")
        
        if not re.search(r'\d', new_password):
            raise ValueError("密码必须包含数字")
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
            raise ValueError("密码必须包含特殊字符")
        
        # TODO: 更新数据库中的密码哈希
        
        # 标记密码已修改
        if user_id in self._users:
            self._users[user_id].password_changed = True
            logger.info(f"用户 {user_id} 密码已修改")
            return True
        
        return False
    
    def require_auth(self, f: Callable) -> Callable:
        """装饰器：要求认证"""
        @wraps(f)
        def decorated(*args, **kwargs):
            auth_header = request.headers.get('Authorization', '')
            
            if not auth_header.startswith('Bearer '):
                return jsonify({
                    "success": False,
                    "error": {"code": "UNAUTHORIZED", "message": "缺少认证信息"}
                }), 401
            
            token = auth_header[7:]  # 去掉 "Bearer "
            payload = self.verify_token(token)
            
            if not payload:
                return jsonify({
                    "success": False,
                    "error": {"code": "INVALID_TOKEN", "message": "Token 无效或已过期"}
                }), 401
            
            # 检查是否已修改默认密码
            if not payload.get('password_changed'):
                # 允许访问修改密码接口
                if request.endpoint != 'change_password':
                    return jsonify({
                        "success": False,
                        "error": {
                            "code": "PASSWORD_NOT_CHANGED",
                            "message": "请先修改默认密码",
                            "action_required": "change_password"
                        }
                    }), 403
            
            # 设置当前用户到 g
            g.user_id = payload['sub']
            g.user_role = payload['role']
            g.user_team = payload.get('team_id')
            
            return f(*args, **kwargs)
        
        return decorated
    
    def require_permission(self, resource: str, action: str):
        """装饰器：要求特定权限"""
        def decorator(f: Callable):
            @wraps(f)
            def decorated(*args, **kwargs):
                # 先检查认证
                auth_result = self._check_auth()
                if auth_result:
                    return auth_result
                
                # 检查权限
                user = self._users.get(g.user_id)
                if not user:
                    return jsonify({
                        "success": False,
                        "error": {"code": "USER_NOT_FOUND", "message": "用户不存在"}
                    }), 404
                
                if not user.has_permission(resource, action):
                    logger.warning(f"用户 {g.user_id} 尝试越权访问: {resource}:{action}")
                    return jsonify({
                        "success": False,
                        "error": {"code": "FORBIDDEN", "message": "权限不足"}
                    }), 403
                
                return f(*args, **kwargs)
            
            return decorated
        return decorator
    
    def _check_auth(self):
        """内部认证检查"""
        auth_header = request.headers.get('Authorization', '')
        
        if not auth_header.startswith('Bearer '):
            return jsonify({
                "success": False,
                "error": {"code": "UNAUTHORIZED", "message": "缺少认证信息"}
            }), 401
        
        token = auth_header[7:]
        payload = self.verify_token(token)
        
        if not payload:
            return jsonify({
                "success": False,
                "error": {"code": "INVALID_TOKEN", "message": "Token 无效或已过期"}
            }), 401
        
        g.user_id = payload['sub']
        g.user_role = payload['role']
        g.user_team = payload.get('team_id')
        
        return None


# 全局认证管理器
_auth_manager: Optional[AuthManager] = None


def get_auth_manager() -> AuthManager:
    """获取全局认证管理器"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = AuthManager()
    return _auth_manager


def init_auth():
    """初始化认证系统"""
    # 确保密钥已初始化
    from .key_manager import init_security_keys
    init_security_keys()
    
    # 初始化认证管理器
    auth = get_auth_manager()
    logger.info("认证系统初始化完成")
    return auth


# 便捷装饰器
def require_auth(f):
    """要求认证的装饰器"""
    return get_auth_manager().require_auth(f)


def require_permission(resource: str, action: str):
    """要求权限的装饰器"""
    return get_auth_manager().require_permission(resource, action)
