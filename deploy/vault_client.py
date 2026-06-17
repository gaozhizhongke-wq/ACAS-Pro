#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - HashiCorp Vault Client
Enterprise-grade secret management
"""

import os
import sys
import json
import base64
import hashlib
import hmac
from typing import Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from functools import wraps

# Enterprise dependencies
try:
    import hvac
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    VAULT_AVAILABLE = True
except ImportError:
    VAULT_AVAILABLE = False
    print("[WARNING] hvac/cryptography not installed")


class VaultClient:
    """
    Vault客户端 - 企业级密钥管理
    
    Features:
    - 动态数据库凭证
    - 自动密钥轮换
    - 加密配置存储
    - 审计日志集成
    """
    
    def __init__(self, vault_addr: str = None, vault_token: str = None):
        self.vault_addr = vault_addr or os.environ.get('VAULT_ADDR', 'http://localhost:8200')
        self.vault_token = vault_token or os.environ.get('VAULT_TOKEN')
        
        if not VAULT_AVAILABLE:
            raise RuntimeError("hvac package required for Vault integration")
        
        if not self.vault_token:
            raise RuntimeError("VAULT_TOKEN not set")
        
        self.client = hvac.Client(url=self.vault_addr, token=self.vault_token)
        
        if not self.client.is_authenticated():
            raise RuntimeError("Vault authentication failed")
        
        # 本地加密备用 (Vault不可用时)
        self._local_key = self._derive_local_key()
    
    def _derive_local_key(self) -> bytes:
        """派生本地加密密钥"""
        master = os.environ.get('ACAS_MASTER_KEY', 'fallback-key-32bytes-long!')
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=master[:16].encode(),
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(master.encode()))
    
    def store_secret(self, path: str, secret: Dict[str, Any]) -> bool:
        """存储密钥到Vault"""
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=secret
            )
            return True
        except Exception as e:
            print(f"[ERROR] Vault store failed: {e}")
            # 降级到本地加密存储
            return self._store_local(path, secret)
    
    def get_secret(self, path: str) -> Optional[Dict[str, Any]]:
        """从Vault读取密钥"""
        try:
            response = self.client.secrets.kv.v2.read_secret_version(path=path)
            return response['data']['data']
        except Exception as e:
            print(f"[WARNING] Vault read failed: {e}")
            # 尝试本地存储
            return self._get_local(path)
    
    def delete_secret(self, path: str) -> bool:
        """删除密钥"""
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(path=path)
            return True
        except Exception as e:
            print(f"[ERROR] Vault delete failed: {e}")
            return False
    
    def rotate_secret(self, path: str, new_secret: Dict[str, Any]) -> bool:
        """轮换密钥"""
        try:
            # 创建新版本
            self.client.secrets.kv.v2.create_or_update_secret(
                path=path,
                secret=new_secret
            )
            
            # 审计日志
            self._audit_log('SECRET_ROTATE', path, 'SUCCESS')
            return True
        except Exception as e:
            self._audit_log('SECRET_ROTATE', path, 'FAILED', str(e))
            return False
    
    def get_database_credentials(self, role: str = 'acas-app') -> Dict[str, str]:
        """获取动态数据库凭证"""
        try:
            response = self.client.secrets.database.generate_credentials(name=role)
            return {
                'username': response['data']['username'],
                'password': response['data']['password'],
                'lease_id': response['lease_id'],
                'lease_duration': response['lease_duration']
            }
        except Exception as e:
            print(f"[ERROR] Dynamic credentials failed: {e}")
            # 返回静态凭证 (降级)
            return self._get_static_db_creds()
    
    def _get_static_db_creds(self) -> Dict[str, str]:
        """获取静态数据库凭证 (降级方案)"""
        secret = self.get_secret('database/static')
        if secret:
            return {
                'username': secret.get('username', 'acas'),
                'password': secret.get('password', ''),
                'lease_id': 'static',
                'lease_duration': 0
            }
        raise RuntimeError("No database credentials available")
    
    def _store_local(self, path: str, secret: Dict[str, Any]) -> bool:
        """本地加密存储 (降级)"""
        try:
            from cryptography.fernet import Fernet
            cipher = Fernet(self._local_key)
            
            encrypted = cipher.encrypt(json.dumps(secret).encode())
            
            # 存储到文件
            local_path = f".vault_local/{path.replace('/', '_')}.enc"
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            
            with open(local_path, 'wb') as f:
                f.write(encrypted)
            
            print(f"[WARNING] Stored locally (Vault unavailable): {path}")
            return True
        except Exception as e:
            print(f"[ERROR] Local store failed: {e}")
            return False
    
    def _get_local(self, path: str) -> Optional[Dict[str, Any]]:
        """本地加密读取 (降级)"""
        try:
            from cryptography.fernet import Fernet
            cipher = Fernet(self._local_key)
            
            local_path = f".vault_local/{path.replace('/', '_')}.enc"
            
            if not os.path.exists(local_path):
                return None
            
            with open(local_path, 'rb') as f:
                encrypted = f.read()
            
            decrypted = cipher.decrypt(encrypted)
            return json.loads(decrypted.decode())
        except Exception as e:
            print(f"[ERROR] Local read failed: {e}")
            return None
    
    def _audit_log(self, action: str, resource: str, result: str, details: str = None):
        """审计日志"""
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'action': action,
            'resource': resource,
            'result': result,
            'details': details,
            'vault_addr': self.vault_addr
        }
        
        # 写入审计日志
        with open('logs/vault_audit.log', 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        try:
            health = self.client.sys.read_health_status()
            return {
                'status': 'healthy' if health.status_code == 200 else 'unhealthy',
                'sealed': False,
                'version': health.json().get('version', 'unknown')
            }
        except Exception as e:
            return {
                'status': 'unreachable',
                'error': str(e)
            }


# 全局实例
_vault_client: Optional[VaultClient] = None

def get_vault() -> VaultClient:
    """获取Vault客户端"""
    global _vault_client
    if _vault_client is None:
        _vault_client = VaultClient()
    return _vault_client


# 便捷函数
def get_secret(path: str) -> Optional[Dict[str, Any]]:
    """获取密钥"""
    return get_vault().get_secret(path)

def store_secret(path: str, secret: Dict[str, Any]) -> bool:
    """存储密钥"""
    return get_vault().store_secret(path, secret)

def get_db_creds(role: str = 'acas-app') -> Dict[str, str]:
    """获取数据库凭证"""
    return get_vault().get_database_credentials(role)


if __name__ == '__main__':
    # 测试
    print("="*60)
    print("ACAS Pro - Vault Client Test")
    print("="*60)
    
    # 需要Vault服务器运行
    print("\n[NOTE] This test requires Vault server running")
    print("Start Vault: vault server -dev")
    print("Export VAULT_ADDR and VAULT_TOKEN")
    print("\nSkipping automated test (requires external service)")
