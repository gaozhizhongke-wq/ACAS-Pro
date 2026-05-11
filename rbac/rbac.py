#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Role-Based Access Control (RBAC)
Enterprise-grade permission system
"""

import os
import sys
import json
import hashlib
import secrets
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Callable
from datetime import datetime, timedelta, timezone
from functools import wraps
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('acas.rbac')


class Permission(Enum):
    """权限枚举"""
    # 用户管理
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_ADMIN = "user:admin"
    
    # 账号管理
    ACCOUNT_CREATE = "account:create"
    ACCOUNT_READ = "account:read"
    ACCOUNT_UPDATE = "account:update"
    ACCOUNT_DELETE = "account:delete"
    ACCOUNT_ADMIN = "account:admin"
    
    # 内容管理
    CONTENT_CREATE = "content:create"
    CONTENT_READ = "content:read"
    CONTENT_UPDATE = "content:update"
    CONTENT_DELETE = "content:delete"
    CONTENT_PUBLISH = "content:publish"
    
    # 数据分析
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"
    
    # 系统设置
    SETTING_READ = "setting:read"
    SETTING_WRITE = "setting:write"
    
    # 审计
    AUDIT_READ = "audit:read"
    
    # 超级权限
    SUPER_ADMIN = "*"


@dataclass
class Role:
    """角色定义"""
    name: str
    description: str
    permissions: Set[Permission]
    data_scope: str = "all"  # all, tenant, own
    is_system: bool = True


@dataclass
class User:
    """用户定义"""
    id: str
    email: str
    name: str
    role: str
    tenant_id: Optional[str] = None
    is_active: bool = True
    mfa_enabled: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None


class RBACManager:
    """
    RBAC管理器
    
    Features:
    - 角色定义与管理
    - 权限检查
    - 数据范围控制
    - 审计日志
    """
    
    # 系统预定义角色
    SYSTEM_ROLES = {
        'super_admin': Role(
            name='super_admin',
            description='超级管理员 - 全部权限',
            permissions={Permission.SUPER_ADMIN},
            data_scope='all',
            is_system=True
        ),
        'admin': Role(
            name='admin',
            description='管理员 - 用户和系统管理',
            permissions={
                Permission.USER_CREATE, Permission.USER_READ, Permission.USER_UPDATE, Permission.USER_DELETE,
                Permission.ACCOUNT_CREATE, Permission.ACCOUNT_READ, Permission.ACCOUNT_UPDATE, Permission.ACCOUNT_DELETE,
                Permission.CONTENT_CREATE, Permission.CONTENT_READ, Permission.CONTENT_UPDATE, Permission.CONTENT_DELETE, Permission.CONTENT_PUBLISH,
                Permission.ANALYTICS_READ, Permission.ANALYTICS_EXPORT,
                Permission.SETTING_READ, Permission.SETTING_WRITE,
                Permission.AUDIT_READ
            },
            data_scope='tenant',
            is_system=True
        ),
        'operator': Role(
            name='operator',
            description='运营人员 - 日常运营',
            permissions={
                Permission.ACCOUNT_READ, Permission.ACCOUNT_UPDATE,
                Permission.CONTENT_CREATE, Permission.CONTENT_READ, Permission.CONTENT_UPDATE, Permission.CONTENT_PUBLISH,
                Permission.ANALYTICS_READ
            },
            data_scope='tenant',
            is_system=True
        ),
        'viewer': Role(
            name='viewer',
            description='查看者 - 只读访问',
            permissions={
                Permission.ACCOUNT_READ,
                Permission.CONTENT_READ,
                Permission.ANALYTICS_READ
            },
            data_scope='tenant',
            is_system=True
        ),
        'auditor': Role(
            name='auditor',
            description='审计员 - 审计只读',
            permissions={
                Permission.AUDIT_READ,
                Permission.ANALYTICS_READ,
                Permission.ANALYTICS_EXPORT
            },
            data_scope='all',
            is_system=True
        )
    }
    
    def __init__(self, db_connection=None):
        self.db = db_connection
        self.roles: Dict[str, Role] = self.SYSTEM_ROLES.copy()
        self.users: Dict[str, User] = {}
        self._load_data()
    
    def _load_data(self):
        """从数据库加载数据"""
        # 加载自定义角色
        roles_file = 'config/rbac_roles.json'
        if os.path.exists(roles_file):
            with open(roles_file, 'r') as f:
                data = json.load(f)
                for name, role_data in data.items():
                    if name not in self.roles:  # 不覆盖系统角色
                        self.roles[name] = Role(
                            name=role_data['name'],
                            description=role_data['description'],
                            permissions={Permission(p) for p in role_data['permissions']},
                            data_scope=role_data.get('data_scope', 'tenant'),
                            is_system=False
                        )
        
        # 加载用户
        users_file = 'config/rbac_users.json'
        if os.path.exists(users_file):
            with open(users_file, 'r') as f:
                data = json.load(f)
                for user_id, user_data in data.items():
                    self.users[user_id] = User(
                        id=user_data['id'],
                        email=user_data['email'],
                        name=user_data['name'],
                        role=user_data['role'],
                        tenant_id=user_data.get('tenant_id'),
                        is_active=user_data.get('is_active', True),
                        mfa_enabled=user_data.get('mfa_enabled', False),
                        created_at=datetime.fromisoformat(user_data['created_at']),
                        last_login=datetime.fromisoformat(user_data['last_login']) if user_data.get('last_login') else None
                    )
    
    def _save_data(self):
        """保存数据到文件"""
        # 保存自定义角色
        custom_roles = {
            name: {
                'name': role.name,
                'description': role.description,
                'permissions': [p.value for p in role.permissions],
                'data_scope': role.data_scope
            }
            for name, role in self.roles.items()
            if not role.is_system
        }
        
        os.makedirs('config', exist_ok=True)
        with open('config/rbac_roles.json', 'w') as f:
            json.dump(custom_roles, f, indent=2)
        
        # 保存用户
        users_data = {
            user_id: {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'role': user.role,
                'tenant_id': user.tenant_id,
                'is_active': user.is_active,
                'mfa_enabled': user.mfa_enabled,
                'created_at': user.created_at.isoformat(),
                'last_login': user.last_login.isoformat() if user.last_login else None
            }
            for user_id, user in self.users.items()
        }
        
        with open('config/rbac_users.json', 'w') as f:
            json.dump(users_data, f, indent=2)
    
    def create_role(self, name: str, description: str, permissions: List[str], 
                    data_scope: str = 'tenant') -> Role:
        """创建自定义角色"""
        if name in self.roles:
            raise ValueError(f"Role {name} already exists")
        
        role = Role(
            name=name,
            description=description,
            permissions={Permission(p) for p in permissions},
            data_scope=data_scope,
            is_system=False
        )
        
        self.roles[name] = role
        self._save_data()
        
        logger.info(f"Created role: {name}")
        return role
    
    def create_user(self, email: str, name: str, role: str, 
                    tenant_id: str = None, password: str = None) -> User:
        """创建用户"""
        if role not in self.roles:
            raise ValueError(f"Role {role} does not exist")
        
        user_id = secrets.token_urlsafe(16)
        
        user = User(
            id=user_id,
            email=email,
            name=name,
            role=role,
            tenant_id=tenant_id,
            is_active=True,
            mfa_enabled=False
        )
        
        self.users[user_id] = user
        self._save_data()
        
        # 如果提供了密码，保存到安全存储
        if password:
            self._store_password(user_id, password)
        
        logger.info(f"Created user: {email} with role {role}")
        return user
    
    def check_permission(self, user_id: str, permission: Permission, 
                        resource_tenant_id: str = None) -> bool:
        """检查用户权限"""
        user = self.users.get(user_id)
        if not user or not user.is_active:
            return False
        
        role = self.roles.get(user.role)
        if not role:
            return False
        
        # 超级管理员
        if Permission.SUPER_ADMIN in role.permissions:
            return True
        
        # 检查具体权限
        if permission not in role.permissions:
            return False
        
        # 检查数据范围
        if role.data_scope == 'own':
            # 只能访问自己的数据
            return resource_tenant_id == user.tenant_id or resource_tenant_id is None
        elif role.data_scope == 'tenant':
            # 只能访问同租户数据
            return resource_tenant_id == user.tenant_id or resource_tenant_id is None
        
        return True
    
    def get_user_permissions(self, user_id: str) -> Set[Permission]:
        """获取用户所有权限"""
        user = self.users.get(user_id)
        if not user:
            return set()
        
        role = self.roles.get(user.role)
        if not role:
            return set()
        
        return role.permissions.copy()
    
    def require_permission(self, permission: Permission):
        """权限检查装饰器"""
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                # 从上下文获取用户ID
                user_id = kwargs.get('current_user_id') or 'anonymous'
                
                if not self.check_permission(user_id, permission):
                    self._audit_log('ACCESS_DENIED', user_id, permission.value)
                    raise PermissionError(f"User {user_id} lacks permission: {permission.value}")
                
                self._audit_log('ACCESS_GRANTED', user_id, permission.value)
                return f(*args, **kwargs)
            return wrapper
        return decorator
    
    def _store_password(self, user_id: str, password: str):
        """安全存储密码"""
        # 使用PBKDF2哈希
        salt = secrets.token_hex(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000).hex()
        
        # 存储到安全位置
        passwords_file = 'config/.passwords'
        os.makedirs('config', exist_ok=True)
        
        passwords = {}
        if os.path.exists(passwords_file):
            with open(passwords_file, 'r') as f:
                passwords = json.load(f)
        
        passwords[user_id] = {
            'salt': salt,
            'hash': pwd_hash,
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        with open(passwords_file, 'w') as f:
            json.dump(passwords, f)
    
    def verify_password(self, user_id: str, password: str) -> bool:
        """验证密码"""
        passwords_file = 'config/.passwords'
        if not os.path.exists(passwords_file):
            return False
        
        with open(passwords_file, 'r') as f:
            passwords = json.load(f)
        
        if user_id not in passwords:
            return False
        
        stored = passwords[user_id]
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode(), stored['salt'].encode(), 100000).hex()
        
        return secrets.compare_digest(pwd_hash, stored['hash'])
    
    def _audit_log(self, action: str, user_id: str, resource: str):
        """审计日志"""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'action': action,
            'user_id': user_id,
            'resource': resource
        }
        
        os.makedirs('logs', exist_ok=True)
        with open('logs/rbac_audit.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')


# 全局实例
_rbac_manager: Optional[RBACManager] = None

def get_rbac() -> RBACManager:
    """获取RBAC管理器"""
    global _rbac_manager
    if _rbac_manager is None:
        _rbac_manager = RBACManager()
    return _rbac_manager


if __name__ == '__main__':
    # 测试
    print("="*60)
    print("ACAS Pro - RBAC Manager Test")
    print("="*60)
    
    rbac = RBACManager()
    
    # 创建测试用户
    admin = rbac.create_user('admin@acas.pro', 'Admin User', 'admin', tenant_id='tenant-1')
    operator = rbac.create_user('operator@acas.pro', 'Operator User', 'operator', tenant_id='tenant-1')
    viewer = rbac.create_user('viewer@acas.pro', 'Viewer User', 'viewer', tenant_id='tenant-2')
    
    # 测试权限
    print("\nPermission checks:")
    print(f"  Admin can delete user: {rbac.check_permission(admin.id, Permission.USER_DELETE)}")
    print(f"  Operator can delete user: {rbac.check_permission(operator.id, Permission.USER_DELETE)}")
    print(f"  Viewer can read account: {rbac.check_permission(viewer.id, Permission.ACCOUNT_READ)}")
    print(f"  Viewer can create account: {rbac.check_permission(viewer.id, Permission.ACCOUNT_CREATE)}")
    
    # 数据范围测试
    print("\nData scope checks:")
    print(f"  Admin access tenant-1: {rbac.check_permission(admin.id, Permission.ACCOUNT_READ, 'tenant-1')}")
    print(f"  Admin access tenant-2: {rbac.check_permission(admin.id, Permission.ACCOUNT_READ, 'tenant-2')}")
    
    print("\n" + "="*60)
    print("RBAC test completed")
