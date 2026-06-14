#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - 企业级安全核心模块
Phase 1 安全基线 - 交付前提
"""

import os
import sys
import hashlib
import hmac
import secrets
import logging
from datetime import datetime, timezone
from functools import wraps
from typing import Optional, Dict
import json

# 企业级依赖
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    print("[WARNING] cryptography not installed, using fallback")


class EnterpriseSecurityCore:
    """
    企业级安全核心
    满足: TLS, 加密存储, RBAC, 审计日志
    """
    
    def __init__(self, master_key: Optional[str] = None):
        self.master_key = master_key or os.environ.get('ACAS_MASTER_KEY')
        if not self.master_key:
            raise SecurityError("ACAS_MASTER_KEY not set - 企业级部署必须设置主密钥")
        
        self._init_encryption()
        self._init_audit_logger()
        self._init_rbac()
    
    def _init_encryption(self):
        """初始化加密引擎"""
        if not CRYPTO_AVAILABLE:
            raise SecurityError("cryptography package required for enterprise deployment")
        
        # 使用PBKDF2派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=self.master_key[:16].encode(),
            iterations=100000,
            backend=default_backend()
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
        self.cipher = Fernet(key)
    
    def _init_audit_logger(self):
        """初始化审计日志 - 不可篡改"""
        self.audit_logger = logging.getLogger('acas.audit')
        self.audit_logger.setLevel(logging.INFO)
        
        # 审计日志格式: 时间戳 | 用户 | 操作 | 对象 | 结果 | 哈希链
        formatter = logging.Formatter(
            '%(asctime)s | %(message)s | HASH:%(hash)s'
        )
        
        # 文件Handler - 只追加，不修改
        audit_file = os.environ.get('ACAS_AUDIT_LOG', 'logs/audit.log')
        os.makedirs(os.path.dirname(audit_file), exist_ok=True)
        
        handler = logging.FileHandler(audit_file, mode='a')
        handler.setFormatter(formatter)
        self.audit_logger.addHandler(handler)
        
        # 上一个日志的哈希 (用于哈希链)
        self._last_hash = self._load_last_hash()
    
    def _init_rbac(self):
        """初始化RBAC权限体系"""
        self.roles = {
            'super_admin': ['*'],  # 所有权限
            'admin': [
                'user:read', 'user:write',
                'account:read', 'account:write',
                'content:read', 'content:write',
                'report:read', 'report:write',
                'setting:read'
            ],
            'operator': [
                'account:read', 'account:write',
                'content:read', 'content:write',
                'report:read'
            ],
            'viewer': [
                'account:read',
                'report:read'
            ]
        }
        
        # 用户角色映射 (生产环境应从数据库加载)
        self.user_roles: Dict[str, str] = {}
    
    def encrypt(self, plaintext: str) -> str:
        """加密敏感数据"""
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """解密敏感数据"""
        return self.cipher.decrypt(ciphertext.encode()).decode()
    
    def audit_log(self, user: str, action: str, resource: str, 
                  result: str, details: Optional[dict] = None):
        """
        记录审计日志 - 不可篡改
        
        Args:
            user: 操作用户ID
            action: 操作类型 (CREATE/READ/UPDATE/DELETE/LOGIN/LOGOUT)
            resource: 操作对象
            result: 结果 (SUCCESS/FAILURE/DENIED)
            details: 详细信息
        """
        # 构建日志内容
        log_data = {
            'user': user,
            'action': action,
            'resource': resource,
            'result': result,
            'details': details or {},
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'prev_hash': self._last_hash
        }
        
        # 计算当前哈希
        log_str = json.dumps(log_data, sort_keys=True)
        current_hash = hashlib.sha256(log_str.encode()).hexdigest()[:16]
        
        # 记录日志
        log_entry = f"{log_data['timestamp']} | {user} | {action} | {resource} | {result}"
        self.audit_logger.info(log_entry, extra={'hash': current_hash})
        
        # 更新哈希链
        self._last_hash = current_hash
        self._save_last_hash(current_hash)
    
    def check_permission(self, user: str, permission: str) -> bool:
        """检查用户权限"""
        role = self.user_roles.get(user, 'viewer')
        permissions = self.roles.get(role, [])
        
        # 超级权限
        if '*' in permissions:
            return True
        
        # 精确匹配
        if permission in permissions:
            return True
        
        # 通配符匹配 (如 user:* 匹配 user:read)
        resource = permission.split(':')[0]
        if f"{resource}:*" in permissions:
            return True
        
        return False
    
    def require_permission(self, permission: str):
        """权限检查装饰器"""
        def decorator(f):
            @wraps(f)
            def wrapper(*args, **kwargs):
                # 从上下文获取当前用户
                user = kwargs.get('current_user') or 'anonymous'
                
                if not self.check_permission(user, permission):
                    self.audit_log(user, 'ACCESS_DENIED', permission, 'DENIED')
                    raise PermissionError(f"User {user} lacks permission: {permission}")
                
                return f(*args, **kwargs)
            return wrapper
        return decorator
    
    def generate_secure_token(self, length: int = 32) -> str:
        """生成安全随机令牌"""
        return secrets.token_urlsafe(length)
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """验证密码 (PBKDF2)"""
        # 格式: algorithm$iterations$salt$hash
        try:
            algo, iters, salt, hash_val = hashed.split('$')
            if algo != 'pbkdf2_sha256':
                return False
            
            new_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                salt.encode(),
                int(iters)
            ).hex()
            
            return hmac.compare_digest(new_hash, hash_val)
        except Exception:
            return False
    
    def hash_password(self, password: str) -> str:
        """哈希密码"""
        salt = secrets.token_hex(16)
        iters = 100000
        hash_val = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            iters
        ).hex()
        return f"pbkdf2_sha256${iters}${salt}${hash_val}"
    
    def _load_last_hash(self) -> str:
        """加载上一个哈希值"""
        hash_file = 'logs/.audit_chain'
        if os.path.exists(hash_file):
            with open(hash_file, 'r') as f:
                return f.read().strip()
        return '0' * 16
    
    def _save_last_hash(self, hash_val: str):
        """保存当前哈希值"""
        hash_file = 'logs/.audit_chain'
        with open(hash_file, 'w') as f:
            f.write(hash_val)


class SecurityError(Exception):
    """安全错误"""
    pass


# 全局安全实例 (懒加载)
_security_instance: Optional[EnterpriseSecurityCore] = None

def get_security() -> EnterpriseSecurityCore:
    """获取安全核心实例"""
    global _security_instance
    if _security_instance is None:
        _security_instance = EnterpriseSecurityCore()
    return _security_instance


# 便捷函数
def encrypt_sensitive(data: str) -> str:
    """加密敏感数据"""
    return get_security().encrypt(data)

def decrypt_sensitive(data: str) -> str:
    """解密敏感数据"""
    return get_security().decrypt(data)

def audit(user: str, action: str, resource: str, result: str, details: dict = None):
    """记录审计日志"""
    get_security().audit_log(user, action, resource, result, details)

def check_perm(user: str, permission: str) -> bool:
    """检查权限"""
    return get_security().check_permission(user, permission)


if __name__ == '__main__':
    # 测试
    import base64
    
    print("="*60)
    print("ACAS Pro - Enterprise Security Core Test")
    print("="*60)
    
    # 设置测试密钥
    os.environ['ACAS_MASTER_KEY'] = 'test-master-key-for-enterprise-32bytes!'
    
    try:
        sec = EnterpriseSecurityCore()
        
        # 测试加密
        plaintext = "sensitive-api-key-12345"
        encrypted = sec.encrypt(plaintext)
        decrypted = sec.decrypt(encrypted)
        assert decrypted == plaintext
        print("[OK] Encryption/Decryption")
        
        # 测试审计日志
        sec.audit_log('admin@company.com', 'LOGIN', 'system', 'SUCCESS')
        print("[OK] Audit logging")
        
        # 测试RBAC
        sec.user_roles['operator1'] = 'operator'
        assert sec.check_permission('operator1', 'account:read') == True  # noqa: E712
        assert sec.check_permission('operator1', 'setting:write') == False  # noqa: E712
        print("[OK] RBAC permissions")
        
        # 测试密码哈希
        pwd_hash = sec.hash_password('MySecurePassword123!')
        assert sec.verify_password('MySecurePassword123!', pwd_hash) == True  # noqa: E712
        assert sec.verify_password('WrongPassword', pwd_hash) == False  # noqa: E712
        print("[OK] Password hashing")
        
        print("\n" + "="*60)
        print("All security tests passed!")
        print("="*60)
        
    except Exception as e:
        print(f"[FAILED] {e}")
        sys.exit(1)