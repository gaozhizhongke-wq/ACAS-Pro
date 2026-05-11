#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
密钥管理模块 - 安全的密钥生成、存储与轮换

版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
All Rights Reserved.
"""

import os
import secrets
import hashlib
import hmac
import base64
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class KeyManager:
    """
    密钥管理器
    
    功能:
    - 安全的密钥生成（密码学安全随机数）
    - 密钥存储（文件权限控制）
    - 密钥轮换策略
    - 密钥版本管理
    """
    
    def __init__(self, keys_dir: str = ".keys"):
        self.keys_dir = Path(keys_dir)
        self.keys_dir.mkdir(mode=0o700, exist_ok=True)  # 仅所有者可读写
        
        self._keys: Dict[str, Dict] = {}
        self._load_keys()
    
    def _load_keys(self):
        """从文件加载所有密钥"""
        for key_file in self.keys_dir.glob("*.key"):
            key_name = key_file.stem
            try:
                with open(key_file, 'r') as f:
                    content = f.read().strip()
                    # 格式: version:created_at:expires_at:key_value
                    parts = content.split(':', 3)
                    if len(parts) == 4:
                        self._keys[key_name] = {
                            'version': int(parts[0]),
                            'created_at': datetime.fromisoformat(parts[1]),
                            'expires_at': datetime.fromisoformat(parts[2]) if parts[2] else None,
                            'value': parts[3]
                        }
            except Exception as e:
                logger.error(f"加载密钥 {key_name} 失败: {e}")
    
    def _save_key(self, name: str, key_data: Dict):
        """保存密钥到文件"""
        key_file = self.keys_dir / f"{name}.key"
        
        expires_str = key_data['expires_at'].isoformat() if key_data['expires_at'] else ''
        content = f"{key_data['version']}:{key_data['created_at'].isoformat()}:{expires_str}:{key_data['value']}"
        
        # 原子写入
        temp_file = key_file.with_suffix('.tmp')
        with open(temp_file, 'w') as f:
            f.write(content)
        
        # 设置权限后重命名
        os.chmod(temp_file, 0o600)
        temp_file.replace(key_file)
    
    def generate_jwt_secret(self, name: str = "jwt_secret", 
                           rotate: bool = False) -> str:
        """
        生成 JWT 密钥
        
        Args:
            name: 密钥名称
            rotate: 是否轮换（生成新版本）
        
        Returns:
            密钥值
        """
        if name in self._keys and not rotate:
            return self._keys[name]['value']
        
        # 生成 256-bit 密钥 (HS256)
        secret = secrets.token_urlsafe(32)
        
        version = 1
        if name in self._keys and rotate:
            version = self._keys[name]['version'] + 1
            # 保留旧版本一段时间（ graceful rotation ）
            old_key = self._keys[name]
            old_name = f"{name}_v{old_key['version']}"
            self._keys[old_name] = old_key.copy()
            self._keys[old_name]['expires_at'] = datetime.now(timezone.utc) + timedelta(days=7)
            self._save_key(old_name, self._keys[old_name])
        
        self._keys[name] = {
            'version': version,
            'created_at': datetime.now(timezone.utc),
            'expires_at': None,  # JWT secret 不过期，通过轮换更新
            'value': secret
        }
        
        self._save_key(name, self._keys[name])
        logger.info(f"JWT 密钥已生成: {name} (v{version})")
        
        return secret
    
    def generate_api_key(self, name: str, expires_days: int = 365) -> str:
        """
        生成 API Key
        
        Args:
            name: API Key 名称/用途标识
            expires_days: 过期天数
        
        Returns:
            API Key (前缀 + 密钥)
        """
        prefix = "acas_"
        # 生成 256-bit 密钥
        secret = secrets.token_urlsafe(32)
        api_key = f"{prefix}{secret}"
        
        # 存储哈希值用于验证（不存储明文）
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        self._keys[name] = {
            'version': 1,
            'created_at': datetime.now(timezone.utc),
            'expires_at': datetime.now(timezone.utc) + timedelta(days=expires_days),
            'value': key_hash,  # 存储哈希
            'prefix': prefix
        }
        
        self._save_key(name, self._keys[name])
        logger.info(f"API Key 已生成: {name}")
        
        # 返回明文（仅这一次）
        return api_key
    
    def verify_api_key(self, name: str, api_key: str) -> bool:
        """验证 API Key"""
        if name not in self._keys:
            return False
        
        key_data = self._keys[name]
        
        # 检查过期
        if key_data.get('expires_at') and datetime.now(timezone.utc) > key_data['expires_at']:
            logger.warning(f"API Key {name} 已过期")
            return False
        
        # 验证哈希
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        return hmac.compare_digest(key_hash, key_data['value'])
    
    def get_jwt_secret(self, name: str = "jwt_secret") -> Optional[str]:
        """获取 JWT 密钥"""
        if name not in self._keys:
            return self.generate_jwt_secret(name)
        return self._keys[name]['value']
    
    def rotate_key(self, name: str) -> Optional[str]:
        """
        轮换密钥
        
        Returns:
            新密钥值（仅 JWT 密钥返回）
        """
        if name not in self._keys:
            logger.error(f"密钥 {name} 不存在")
            return None
        
        if 'jwt' in name.lower():
            return self.generate_jwt_secret(name, rotate=True)
        else:
            # API Key 直接生成新的
            expires = None
            if self._keys[name].get('expires_at'):
                expires = (self._keys[name]['expires_at'] - self._keys[name]['created_at']).days
            return self.generate_api_key(name, expires or 365)
    
    def revoke_key(self, name: str) -> bool:
        """撤销密钥"""
        if name not in self._keys:
            return False
        
        key_file = self.keys_dir / f"{name}.key"
        revoked_file = self.keys_dir / f"{name}.revoked.{datetime.now(timezone.utc).strftime('%Y%m%d')}"
        
        try:
            key_file.rename(revoked_file)
            del self._keys[name]
            logger.info(f"密钥 {name} 已撤销")
            return True
        except Exception as e:
            logger.error(f"撤销密钥失败: {e}")
            return False
    
    def list_keys(self) -> Dict[str, Dict]:
        """列出所有密钥状态（不含密钥值）"""
        result = {}
        for name, data in self._keys.items():
            result[name] = {
                'version': data['version'],
                'created_at': data['created_at'].isoformat(),
                'expires_at': data['expires_at'].isoformat() if data['expires_at'] else None,
                'status': 'active' if not data.get('expires_at') or datetime.now(timezone.utc) < data['expires_at'] else 'expired'
            }
        return result
    
    def cleanup_expired(self) -> int:
        """清理过期密钥，返回清理数量"""
        cleaned = 0
        now = datetime.now(timezone.utc)
        
        for name in list(self._keys.keys()):
            data = self._keys[name]
            if data.get('expires_at') and now > data['expires_at'] + timedelta(days=7):
                # 过期超过 7 天的旧版本可以删除
                if '_v' in name:  # 旧版本密钥
                    key_file = self.keys_dir / f"{name}.key"
                    try:
                        key_file.unlink()
                        del self._keys[name]
                        cleaned += 1
                    except Exception as e:
                        logger.error(f"清理密钥 {name} 失败: {e}")
        
        return cleaned


# 全局密钥管理器实例
_key_manager: Optional[KeyManager] = None


def get_key_manager() -> KeyManager:
    """获取全局密钥管理器"""
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager


def init_security_keys():
    """初始化系统所需的所有密钥"""
    km = get_key_manager()
    
    # 确保 JWT 密钥存在
    jwt_secret = km.get_jwt_secret("jwt_secret")
    if not jwt_secret:
        jwt_secret = km.generate_jwt_secret("jwt_secret")
        logger.info("JWT 密钥已初始化")
    
    # 清理过期密钥
    cleaned = km.cleanup_expired()
    if cleaned > 0:
        logger.info(f"清理了 {cleaned} 个过期密钥")
    
    return km


if __name__ == "__main__":
    # 测试
    km = KeyManager()
    
    # 生成 JWT 密钥
    jwt = km.generate_jwt_secret()
    print(f"JWT Secret: {jwt[:20]}...")
    
    # 生成 API Key
    api_key = km.generate_api_key("test_service", expires_days=30)
    print(f"API Key: {api_key[:30]}...")
    
    # 验证
    print(f"验证结果: {km.verify_api_key('test_service', api_key)}")
    
    # 列出密钥
    print("\n密钥列表:")
    for name, info in km.list_keys().items():
        print(f"  {name}: {info}")
