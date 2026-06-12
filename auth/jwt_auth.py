#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - JWT Authentication Service
Enterprise-grade token management with refresh rotation
"""

import os
import jwt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, List
from dataclasses import dataclass
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('acas.auth')


class TokenType(Enum):
    ACCESS = "access"
    REFRESH = "refresh"


@dataclass
class TokenPair:
    """Token对"""
    access_token: str
    refresh_token: str
    access_expires_at: datetime
    refresh_expires_at: datetime
    token_id: str


@dataclass
class TokenPayload:
    """Token载荷"""
    user_id: str
    email: str
    role: str
    tenant_id: Optional[str]
    permissions: List[str]
    token_id: str
    type: TokenType
    issued_at: datetime
    expires_at: datetime


class JWTAuthManager:
    """
    JWT认证管理器
    
    Features:
    - Access Token (15分钟)
    - Refresh Token (7天)
    - Token轮换
    - 黑名单
    - 设备绑定
    """
    
    def __init__(self):
        # 从环境变量获取密钥
        self.secret_key = os.environ.get('JWT_SECRET_KEY')
        if not self.secret_key:
            logger.warning("JWT_SECRET_KEY not set, using random key (DO NOT USE IN PRODUCTION)")
            self.secret_key = secrets.token_urlsafe(32)
        
        self.algorithm = 'HS256'
        self.access_token_expire = timedelta(minutes=15)
        self.refresh_token_expire = timedelta(days=7)
        
        # Token黑名单 (应使用Redis)
        self.token_blacklist: set = set()
        self.refresh_token_store: Dict[str, Dict] = {}
        
        # 设备绑定
        self.device_bindings: Dict[str, str] = {}  # token_id -> device_fingerprint
    
    def create_token_pair(self, user_id: str, email: str, role: str,
                         tenant_id: Optional[str], permissions: List[str],
                         device_fingerprint: Optional[str] = None) -> TokenPair:
        """
        创建Token对
        
        Args:
            user_id: 用户ID
            email: 邮箱
            role: 角色
            tenant_id: 租户ID
            permissions: 权限列表
            device_fingerprint: 设备指纹
        """
        token_id = secrets.token_urlsafe(16)
        now = datetime.now(timezone.utc)
        
        # Access Token
        access_payload = {
            'sub': user_id,
            'email': email,
            'role': role,
            'tenant_id': tenant_id,
            'permissions': permissions,
            'token_id': token_id,
            'type': TokenType.ACCESS.value,
            'iat': now,
            'exp': now + self.access_token_expire,
            'jti': secrets.token_urlsafe(8)
        }
        
        access_token = jwt.encode(access_payload, self.secret_key, algorithm=self.algorithm)
        
        # Refresh Token
        refresh_payload = {
            'sub': user_id,
            'token_id': token_id,
            'type': TokenType.REFRESH.value,
            'iat': now,
            'exp': now + self.refresh_token_expire,
            'jti': secrets.token_urlsafe(8)
        }
        
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm=self.algorithm)
        
        # 存储Refresh Token信息
        self.refresh_token_store[token_id] = {
            'user_id': user_id,
            'device_fingerprint': device_fingerprint,
            'created_at': now.isoformat(),
            'expires_at': (now + self.refresh_token_expire).isoformat(),
            'rotation_count': 0
        }
        
        # 设备绑定
        if device_fingerprint:
            self.device_bindings[token_id] = device_fingerprint
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=now + self.access_token_expire,
            refresh_expires_at=now + self.refresh_token_expire,
            token_id=token_id
        )
    
    def verify_token(self, token: str, expected_type: TokenType = None) -> TokenPayload:
        """
        验证Token
        
        Args:
            token: JWT token
            expected_type: 期望的token类型
            
        Returns:
            TokenPayload
            
        Raises:
            jwt.ExpiredSignatureError: Token过期
            jwt.InvalidTokenError: Token无效
        """
        # 检查黑名单
        if token in self.token_blacklist:
            raise jwt.InvalidTokenError("Token has been revoked")
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # 验证类型
            token_type = TokenType(payload.get('type', 'access'))
            if expected_type and token_type != expected_type:
                raise jwt.InvalidTokenError(f"Expected {expected_type.value} token")
            
            return TokenPayload(
                user_id=payload['sub'],
                email=payload.get('email', ''),
                role=payload.get('role', ''),
                tenant_id=payload.get('tenant_id'),
                permissions=payload.get('permissions', []),
                token_id=payload['token_id'],
                type=token_type,
                issued_at=datetime.fromtimestamp(payload['iat']),
                expires_at=datetime.fromtimestamp(payload['exp'])
            )
            
        except jwt.ExpiredSignatureError:
            raise
        except jwt.InvalidTokenError as e:
            raise jwt.InvalidTokenError(f"Invalid token: {e}")
    
    def refresh_access_token(self, refresh_token: str, 
                            device_fingerprint: Optional[str] = None) -> TokenPair:
        """
        刷新Access Token (Token轮换)
        
        每次刷新都会:
        1. 验证Refresh Token
        2. 使旧Token对失效
        3. 生成新的Token对
        """
        # 验证Refresh Token
        payload = self.verify_token(refresh_token, TokenType.REFRESH)
        token_id = payload.token_id
        
        # 检查Refresh Token是否存在
        if token_id not in self.refresh_token_store:
            raise jwt.InvalidTokenError("Refresh token not found")
        
        stored = self.refresh_token_store[token_id]
        
        # 设备绑定验证
        if stored.get('device_fingerprint'):
            if device_fingerprint != stored['device_fingerprint']:
                logger.warning(f"Device mismatch for token {token_id}")
                raise jwt.InvalidTokenError("Device mismatch")
        
        # 检查旋转次数 (防止无限旋转)
        if stored.get('rotation_count', 0) > 100:
            raise jwt.InvalidTokenError("Maximum rotation count exceeded")
        
        # 使旧Token失效
        self.token_blacklist.add(refresh_token)
        
        # 获取用户信息 (实际应从数据库获取)
        user_id = payload.user_id
        
        # 创建新的Token对
        # 这里简化处理，实际应该从数据库获取完整用户信息
        new_pair = self.create_token_pair(
            user_id=user_id,
            email=stored.get('email', ''),
            role=stored.get('role', ''),
            tenant_id=stored.get('tenant_id'),
            permissions=stored.get('permissions', []),
            device_fingerprint=device_fingerprint or stored.get('device_fingerprint')
        )
        
        # 更新旋转计数
        self.refresh_token_store[new_pair.token_id] = {
            **stored,
            'rotation_count': stored.get('rotation_count', 0) + 1
        }
        
        # 删除旧token记录
        del self.refresh_token_store[token_id]
        
        logger.info(f"Token rotated for user {user_id}")
        return new_pair
    
    def revoke_token(self, token: str):
        """吊销Token"""
        self.token_blacklist.add(token)
        
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm], options={"verify_exp": False})
            token_id = payload.get('token_id')
            if token_id and token_id in self.refresh_token_store:
                del self.refresh_token_store[token_id]
        except Exception:
            pass
        
        logger.info("Token revoked")
    
    def revoke_all_user_tokens(self, user_id: str):
        """吊销用户所有Token"""
        # 查找并吊销所有该用户的token
        tokens_to_revoke = [
            token_id for token_id, info in self.refresh_token_store.items()
            if info.get('user_id') == user_id
        ]
        
        for token_id in tokens_to_revoke:
            del self.refresh_token_store[token_id]
        
        logger.info(f"Revoked all tokens for user {user_id}")
    
    def get_token_info(self, token_id: str) -> Optional[Dict]:
        """获取Token信息"""
        return self.refresh_token_store.get(token_id)
    
    def cleanup_expired_tokens(self):
        """清理过期Token"""
        now = datetime.now(timezone.utc)
        expired = [
            token_id for token_id, info in self.refresh_token_store.items()
            if datetime.fromisoformat(info['expires_at']) < now
        ]
        
        for token_id in expired:
            del self.refresh_token_store[token_id]
        
        if expired:
            logger.info(f"Cleaned up {len(expired)} expired tokens")


# 便捷函数
_auth_manager: Optional[JWTAuthManager] = None

def get_auth_manager() -> JWTAuthManager:
    """获取认证管理器"""
    global _auth_manager
    if _auth_manager is None:
        _auth_manager = JWTAuthManager()
    return _auth_manager


def require_auth(permissions: List[str] = None):
    """认证装饰器"""
    def decorator(f):
        def wrapper(*args, **kwargs):
            # 从请求头获取token
            # 实际实现取决于web框架
            token = kwargs.get('token') or 'Bearer xxx'
            
            auth = get_auth_manager()
            try:
                payload = auth.verify_token(token.replace('Bearer ', ''))
                
                # 权限检查
                if permissions:
                    user_perms = set(payload.permissions)
                    required_perms = set(permissions)
                    if not required_perms.issubset(user_perms):
                        raise PermissionError("Insufficient permissions")
                
                kwargs['current_user'] = payload
                return f(*args, **kwargs)
                
            except jwt.ExpiredSignatureError:
                raise PermissionError("Token expired")
            except jwt.InvalidTokenError as e:
                raise PermissionError(f"Invalid token: {e}")
                
        return wrapper
    return decorator


if __name__ == '__main__':
    # 测试
    print("="*60)
    print("ACAS Pro - JWT Auth Manager Test")
    print("="*60)
    
    auth = JWTAuthManager()
    
    # 创建Token对
    print("\nCreating token pair...")
    tokens = auth.create_token_pair(
        user_id='user-123',
        email='admin@acas.pro',
        role='admin',
        tenant_id='tenant-1',
        permissions=['user:read', 'user:write', 'account:read'],
        device_fingerprint='device-abc'
    )
    print(f"  Access token: {tokens.access_token[:50]}...")
    print(f"  Refresh token: {tokens.refresh_token[:50]}...")
    print(f"  Token ID: {tokens.token_id}")
    
    # 验证Access Token
    print("\nVerifying access token...")
    payload = auth.verify_token(tokens.access_token)
    print(f"  User: {payload.email}")
    print(f"  Role: {payload.role}")
    print(f"  Permissions: {payload.permissions}")
    
    # Token轮换
    print("\nRotating tokens...")
    new_tokens = auth.refresh_access_token(tokens.refresh_token, 'device-abc')
    print(f"  New access token: {new_tokens.access_token[:50]}...")
    print(f"  New token ID: {new_tokens.token_id}")
    
    # 验证旧Refresh Token已失效
    print("\nVerifying old refresh token is revoked...")
    try:
        auth.verify_token(tokens.refresh_token)
        print("  ERROR: Old token still valid!")
    except jwt.InvalidTokenError as e:
        print(f"  OK: {e}")
    
    print("\n" + "="*60)
    print("JWT auth test completed")
