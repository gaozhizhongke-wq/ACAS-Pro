#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro 安全配置管理
解决密钥明文存储问题
"""

import os
import base64
import getpass
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class SecureConfig:
    """安全配置管理器"""
    
    def __init__(self, config_dir: str = None):
        self.config_dir = Path(config_dir or os.path.dirname(__file__))
        self.key_file = self.config_dir / '.secure_key'
        self.config_file = self.config_dir / '.env.encrypted'
        self._key = None
        self._cipher = None
    
    def _get_or_create_key(self, password: str = None) -> bytes:
        """获取或创建加密密钥"""
        if self._key:
            return self._key
        
        if self.key_file.exists():
            # 使用机器指纹 + 用户输入
            salt = self.key_file.read_bytes()
            password = password or os.environ.get('ACAS_MASTER_KEY', '')
            if not password:
                password = getpass.getpass('Enter master key: ')
        else:
            # 首次运行，创建新密钥
            salt = os.urandom(16)
            self.key_file.write_bytes(salt)
            password = password or os.urandom(32).hex()
            print(f"[INFO] Generated master key (save this!): {password[:16]}...")
        
        # 派生密钥
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        self._key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self._cipher = Fernet(self._key)
        return self._key
    
    def encrypt_value(self, value: str, password: str = None) -> str:
        """加密值"""
        key = self._get_or_create_key(password)
        cipher = Fernet(key)
        return cipher.encrypt(value.encode()).decode()
    
    def decrypt_value(self, encrypted: str, password: str = None) -> str:
        """解密值"""
        key = self._get_or_create_key(password)
        cipher = Fernet(key)
        return cipher.decrypt(encrypted.encode()).decode()
    
    def save_secure_config(self, config: dict, password: str = None):
        """保存加密配置"""
        import json
        key = self._get_or_create_key(password)
        cipher = Fernet(key)
        
        config_json = json.dumps(config, ensure_ascii=False)
        encrypted = cipher.encrypt(config_json.encode())
        self.config_file.write_bytes(encrypted)
        print(f"[OK] Config saved to {self.config_file}")
    
    def load_secure_config(self, password: str = None) -> dict:
        """加载加密配置"""
        import json
        if not self.config_file.exists():
            return {}
        
        key = self._get_or_create_key(password)
        cipher = Fernet(key)
        
        encrypted = self.config_file.read_bytes()
        config_json = cipher.decrypt(encrypted).decode()
        return json.loads(config_json)
    
    def migrate_from_env(self, env_file: str = '.env'):
        """从明文.env迁移到加密存储"""
        env_path = self.config_dir / env_file
        if not env_path.exists():
            print(f"[WARNING] {env_file} not found")
            return
        
        # 读取现有配置
        config = {}
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    config[key] = value
        
        # 加密保存
        print(f"[INFO] Migrating {len(config)} keys from {env_file}")
        self.save_secure_config(config)
        
        # 备份原文件
        backup = env_path.with_suffix('.env.backup')
        env_path.rename(backup)
        print(f"[OK] Original file backed up to {backup}")


def setup_secure_config():
    """交互式设置安全配置"""
    print("="*60)
    print("ACAS Pro - 安全配置向导")
    print("="*60)
    print()
    
    secure = SecureConfig()
    
    # 检查是否需要迁移
    env_file = Path('.env')
    if env_file.exists():
        print("[1/3] 发现明文配置文件，正在迁移...")
        secure.migrate_from_env()
    else:
        print("[1/3] 创建新的安全配置...")
    
    print("[2/3] 配置敏感信息...")
    config = secure.load_secure_config() if secure.config_file.exists() else {}
    
    # DeepSeek API Key
    api_key = input("DeepSeek API Key (按Enter保持不变): ").strip()
    if api_key:
        config['DEEPSEEK_API_KEY'] = api_key
    
    # 其他配置
    config.setdefault('ACAS_DEBUG', 'false')
    config.setdefault('ACAS_LOG_LEVEL', 'INFO')
    config.setdefault('ACAS_DB_PATH', 'data/acas.db')
    
    secure.save_secure_config(config)
    
    print("[3/3] 验证配置...")
    loaded = secure.load_secure_config()
    if 'DEEPSEEK_API_KEY' in loaded:
        masked = loaded['DEEPSEEK_API_KEY'][:8] + '****' + loaded['DEEPSEEK_API_KEY'][-4:]
        print(f"      API Key: {masked}")
    
    print()
    print("="*60)
    print("安全配置完成！")
    print("="*60)
    print()
    print("重要提示:")
    print("1. 请妥善保存主密钥 (.secure_key)")
    print("2. 建议设置环境变量 ACAS_MASTER_KEY 避免每次输入")
    print("3. 原.env文件已备份为.env.backup")
    print()


if __name__ == '__main__':
    setup_secure_config()
