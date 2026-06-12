#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Security Module Integration
Integrates all security components
"""

import sys
import os

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from typing import Dict, Optional
from datetime import datetime, timezone
import logging

# Import security modules
from vault.vault_client import VaultClient
from rbac.rbac import RBACManager, Permission
from audit.audit_logger import ImmutableAuditLogger, AuditEventType
from auth.jwt_auth import JWTAuthManager, TokenPair
from auth.mfa import MFAManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('acas.security')


class SecurityContext:
    """
    安全上下文 - 统一入口
    
    整合所有安全模块:
    - Vault: 密钥管理
    - RBAC: 权限控制
    - Audit: 审计日志
    - JWT: 认证
    - MFA: 多因素认证
    """
    
    def __init__(self):
        self.vault = None
        self.rbac = None
        self.audit = None
        self.auth = None
        self.mfa = None
        self._initialized = False
    
    def initialize(self, vault_addr: str = None, vault_token: str = None) -> bool:
        """初始化所有安全模块"""
        try:
            logger.info("Initializing security context...")
            
            # 1. Vault (可选，有降级方案)
            try:
                self.vault = VaultClient(vault_addr, vault_token)
                logger.info("✓ Vault connected")
            except Exception as e:
                logger.warning(f"⚠ Vault unavailable: {e}, using local encryption")
                self.vault = None
            
            # 2. RBAC
            self.rbac = RBACManager()
            logger.info("✓ RBAC initialized")
            
            # 3. Audit Logger
            self.audit = ImmutableAuditLogger()
            logger.info("✓ Audit logger initialized")
            
            # 4. JWT Auth
            self.auth = JWTAuthManager()
            logger.info("✓ JWT auth initialized")
            
            # 5. MFA
            self.mfa = MFAManager()
            logger.info("✓ MFA initialized")
            
            self._initialized = True
            logger.info("Security context initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize security context: {e}")
            return False
    
    # ============== Authentication ==============
    
    def authenticate(self, email: str, password: str, 
                    mfa_code: str = None,
                    device_fingerprint: str = None) -> Dict:
        """
        用户认证流程
        
        1. 验证用户名密码
        2. 检查MFA
        3. 生成Token
        4. 记录审计日志
        """
        if not self._initialized:
            raise RuntimeError("Security context not initialized")
        
        # 查找用户
        user = None
        for u in self.rbac.users.values():
            if u.email == email:
                user = u
                break
        
        if not user:
            self._log_auth_event(email, None, 'failed', 'user_not_found', device_fingerprint)
            raise PermissionError("Invalid credentials")
        
        # 验证密码
        if not self.rbac.verify_password(user.id, password):
            self._log_auth_event(email, user.id, 'failed', 'invalid_password', device_fingerprint)
            raise PermissionError("Invalid credentials")
        
        # 检查MFA
        if self.mfa.is_mfa_enabled(user.id):
            if not mfa_code:
                self._log_auth_event(email, user.id, 'mfa_required', None, device_fingerprint)
                return {
                    'status': 'mfa_required',
                    'method': self.mfa.mfa_configs[user.id].method,
                    'user_id': user.id
                }
            
            if not self.mfa.verify_mfa(user.id, mfa_code):
                self._log_auth_event(email, user.id, 'failed', 'invalid_mfa', device_fingerprint)
                raise PermissionError("Invalid MFA code")
        
        # 检查信任设备
        skip_mfa_next_time = False
        if device_fingerprint and self.mfa.is_mfa_enabled(user.id):
            if self.mfa.is_trusted_device(user.id, device_fingerprint):
                skip_mfa_next_time = True
            else:
                # 添加信任设备选项
                pass
        
        # 获取权限
        permissions = self.rbac.get_user_permissions(user.id)
        permission_list = [p.value for p in permissions]
        
        # 生成Token
        tokens = self.auth.create_token_pair(
            user_id=user.id,
            email=user.email,
            role=user.role,
            tenant_id=user.tenant_id,
            permissions=permission_list,
            device_fingerprint=device_fingerprint
        )
        
        # 更新最后登录时间
        user.last_login = datetime.now(timezone.utc)
        self.rbac._save_data()
        
        # 记录成功日志
        self._log_auth_event(email, user.id, 'success', None, device_fingerprint)
        
        return {
            'status': 'success',
            'access_token': tokens.access_token,
            'refresh_token': tokens.refresh_token,
            'expires_in': 900,  # 15分钟
            'user': {
                'id': user.id,
                'email': user.email,
                'name': user.name,
                'role': user.role,
                'permissions': permission_list
            },
            'mfa': {
                'enabled': self.mfa.is_mfa_enabled(user.id),
                'trusted_device': skip_mfa_next_time
            }
        }
    
    def _log_auth_event(self, email: str, user_id: str, status: str, 
                       reason: str, device_fingerprint: str):
        """记录认证事件"""
        event_type = AuditEventType.AUTH_LOGIN if status == 'success' else AuditEventType.AUTH_FAILED
        
        self.audit.log(
            event_type=event_type,
            user_id=user_id or 'anonymous',
            user_email=email,
            ip_address='0.0.0.0',  # 应从请求获取
            user_agent='unknown',
            resource_type='auth',
            resource_id='login',
            action='authenticate',
            status=status,
            details={
                'reason': reason,
                'device_fingerprint': device_fingerprint
            }
        )
    
    def refresh_token(self, refresh_token: str, device_fingerprint: str = None) -> TokenPair:
        """刷新Token"""
        return self.auth.refresh_access_token(refresh_token, device_fingerprint)
    
    def logout(self, token: str):
        """登出"""
        self.auth.revoke_token(token)
    
    # ============== Authorization ==============
    
    def check_permission(self, user_id: str, permission: str, 
                        resource_tenant_id: str = None) -> bool:
        """检查权限"""
        perm = Permission(permission)
        return self.rbac.check_permission(user_id, perm, resource_tenant_id)
    
    def require_permission(self, token: str, permission: str):
        """要求权限"""
        # 验证Token
        payload = self.auth.verify_token(token)
        
        # 检查权限
        if permission not in payload.permissions:
            raise PermissionError(f"Permission denied: {permission}")
        
        return payload
    
    # ============== MFA ==============
    
    def setup_mfa(self, user_id: str, method: str, email: str = None, 
                  phone: str = None) -> Dict:
        """设置MFA"""
        if method == 'totp':
            secret, qr_code, backup_codes = self.mfa.setup_totp(user_id, email)
            return {
                'method': 'totp',
                'secret': secret,
                'qr_code': qr_code,
                'backup_codes': backup_codes
            }
        elif method == 'sms':
            self.mfa.send_sms_code(user_id, phone)
            return {
                'method': 'sms',
                'phone': phone
            }
        else:
            raise ValueError(f"Unsupported MFA method: {method}")
    
    def verify_mfa_setup(self, user_id: str, code: str) -> bool:
        """验证MFA设置"""
        return self.mfa.verify_totp_setup(user_id, code)
    
    # ============== Audit ==============
    
    def log_event(self, event_type: str, user_id: str, user_email: str,
                 action: str, resource_type: str, resource_id: str,
                 status: str, details: Dict = None):
        """记录审计事件"""
        self.audit.log(
            event_type=AuditEventType(event_type),
            user_id=user_id,
            user_email=user_email,
            ip_address='0.0.0.0',
            user_agent='unknown',
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            status=status,
            details=details or {}
        )
    
    def get_audit_report(self, start_date: datetime, end_date: datetime) -> Dict:
        """获取审计报告"""
        events = self.audit.query_events(start_time=start_date, end_time=end_date, limit=10000)
        integrity = self.audit.verify_log_integrity()
        
        return {
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'summary': {
                'total_events': len(events),
                'integrity_status': integrity['valid'],
                'failed_events': len([e for e in events if e['status'] == 'failed'])
            },
            'events': events[:100]  # 只返回前100条
        }
    
    # ============== Vault ==============
    
    def get_secret(self, path: str) -> Optional[Dict]:
        """获取密钥"""
        if self.vault:
            return self.vault.get_secret(path)
        return None
    
    def store_secret(self, path: str, secret: Dict) -> bool:
        """存储密钥"""
        if self.vault:
            return self.vault.store_secret(path, secret)
        return False


# 全局实例
_security_context: Optional[SecurityContext] = None

def get_security_context() -> SecurityContext:
    """获取安全上下文"""
    global _security_context
    if _security_context is None:
        _security_context = SecurityContext()
    return _security_context


if __name__ == '__main__':
    # 集成测试
    print("="*70)
    print("ACAS Pro - Security Integration Test")
    print("="*70)
    
    security = SecurityContext()
    
    # 初始化
    print("\n[1] Initializing security context...")
    success = security.initialize()
    print(f"    Result: {'✓ Success' if success else '✗ Failed'}")
    
    if success:
        # 创建测试用户
        print("\n[2] Creating test user...")
        user = security.rbac.create_user(
            email='admin@acas.pro',
            name='Test Admin',
            role='admin',
            tenant_id='tenant-1',
            password=os.environ.get('TEST_ADMIN_PASSWORD', 'TestPass123!')
        )
        print(f"    User: {user.email} ({user.id})")
        
        # 认证测试
        print("\n[3] Testing authentication...")
        try:
            result = security.authenticate('admin@acas.pro', 'TestPass123!')
            print(f"    Status: {result['status']}")
            if result['status'] == 'success':
                print(f"    Token: {result['access_token'][:50]}...")
                
                # 权限检查
                print("\n[4] Testing authorization...")
                has_perm = security.check_permission(user.id, 'user:create')
                print(f"    Can create user: {has_perm}")
                
                # 审计日志
                print("\n[5] Testing audit logging...")
                security.log_event(
                    event_type='data:read',
                    user_id=user.id,
                    user_email=user.email,
                    action='read',
                    resource_type='account',
                    resource_id='acc-123',
                    status='success'
                )
                print("    Event logged")
                
                # 验证审计完整性
                integrity = security.audit.verify_log_integrity()
                print(f"    Log integrity: {integrity['valid']}")
        
        except PermissionError as e:
            print(f"    Auth failed: {e}")
    
    print("\n" + "="*70)
    print("Security integration test completed")
    print("="*70)
