#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Multi-Factor Authentication (MFA)
TOTP and SMS-based 2FA
"""

import pyotp
import qrcode
import io
import base64
import secrets
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('acas.mfa')


class MFAMethod(Enum):
    """MFA方法枚举"""
    TOTP = "totp"
    SMS = "sms"
    EMAIL = "email"
    BACKUP_CODES = "backup_codes"


@dataclass
class MFAConfig:
    """MFA配置"""
    user_id: str
    method: str  # 'totp', 'sms', 'email'
    secret: str
    verified: bool = False
    backup_codes: list = None
    created_at: datetime = None
    last_used: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)
        if self.backup_codes is None:
            self.backup_codes = []


class MFAManager:
    """
    MFA管理器
    
    Features:
    - TOTP (Google Authenticator compatible)
    - SMS验证码
    - 备用恢复码
    - 设备信任
    """
    
    def __init__(self):
        # 存储 (实际应使用数据库)
        self.mfa_configs: Dict[str, MFAConfig] = {}
        self.sms_codes: Dict[str, Dict] = {}  # user_id -> {code, expires_at}
        self.trusted_devices: Dict[str, Dict] = {}  # user_id -> {device_fingerprint: expires_at}
        
        # 配置
        self.sms_code_length = 6
        self.sms_code_ttl = timedelta(minutes=5)
        self.trusted_device_ttl = timedelta(days=30)
    
    def setup_totp(self, user_id: str, user_email: str) -> Tuple[str, str]:
        """
        设置TOTP
        
        Returns:
            (secret, qr_code_url)
        """
        # 生成密钥
        secret = pyotp.random_base32()
        
        # 创建TOTP对象
        totp = pyotp.TOTP(secret)
        
        # 生成URI
        issuer = "ACAS Pro"
        uri = totp.provisioning_uri(
            name=user_email,
            issuer_name=issuer
        )
        
        # 生成二维码
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # 转换为base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        qr_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        # 生成备用恢复码
        backup_codes = [secrets.token_hex(4).upper() for _ in range(10)]
        
        # 保存配置 (未验证状态)
        self.mfa_configs[user_id] = MFAConfig(
            user_id=user_id,
            method='totp',
            secret=secret,
            verified=False,
            backup_codes=backup_codes
        )
        
        logger.info(f"TOTP setup initiated for user {user_id}")
        
        return secret, qr_base64, backup_codes
    
    def verify_totp_setup(self, user_id: str, code: str) -> bool:
        """验证TOTP设置"""
        config = self.mfa_configs.get(user_id)
        if not config or config.method != 'totp':
            return False
        
        totp = pyotp.TOTP(config.secret)
        
        # 验证当前码和前后各一个码 (防止时间漂移)
        if totp.verify(code, valid_window=1):
            config.verified = True
            logger.info(f"TOTP verified for user {user_id}")
            return True
        
        return False
    
    def verify_totp(self, user_id: str, code: str) -> bool:
        """验证TOTP码"""
        config = self.mfa_configs.get(user_id)
        if not config or config.method != 'totp' or not config.verified:
            return False
        
        totp = pyotp.TOTP(config.secret)
        
        if totp.verify(code, valid_window=1):
            config.last_used = datetime.now(timezone.utc)
            return True
        
        # 检查备用码
        if code.upper() in config.backup_codes:
            config.backup_codes.remove(code.upper())
            logger.warning(f"Backup code used for user {user_id}")
            return True
        
        return False
    
    def send_sms_code(self, user_id: str, phone_number: str) -> bool:
        """发送SMS验证码"""
        # 生成验证码
        code = ''.join([str(secrets.randbelow(10)) for _ in range(self.sms_code_length)])
        
        # 存储验证码
        self.sms_codes[user_id] = {
            'code': code,
            'phone': phone_number,
            'expires_at': datetime.now(timezone.utc) + self.sms_code_ttl,
            'attempts': 0
        }
        
        # 实际项目中调用SMS服务商API
        # 这里模拟发送
        logger.info(f"SMS code sent to {phone_number}: {code}")
        print(f"[SMS SIMULATION] Code for {phone_number}: {code}")
        
        return True
    
    def verify_sms_code(self, user_id: str, code: str) -> bool:
        """验证SMS验证码"""
        sms_data = self.sms_codes.get(user_id)
        if not sms_data:
            return False
        
        # 检查过期
        if datetime.now(timezone.utc) > sms_data['expires_at']:
            del self.sms_codes[user_id]
            return False
        
        # 检查尝试次数
        if sms_data['attempts'] >= 3:
            del self.sms_codes[user_id]
            return False
        
        sms_data['attempts'] += 1
        
        if sms_data['code'] == code:
            del self.sms_codes[user_id]
            
            # 保存MFA配置
            self.mfa_configs[user_id] = MFAConfig(
                user_id=user_id,
                method='sms',
                secret=sms_data['phone'],
                verified=True
            )
            
            return True
        
        return False
    
    def is_mfa_enabled(self, user_id: str) -> bool:
        """检查用户是否启用MFA"""
        config = self.mfa_configs.get(user_id)
        return config is not None and config.verified
    
    def verify_mfa(self, user_id: str, code: str, method: str = None) -> bool:
        """验证MFA码"""
        config = self.mfa_configs.get(user_id)
        if not config:
            return False
        
        if method and config.method != method:
            return False
        
        if config.method == 'totp':
            return self.verify_totp(user_id, code)
        elif config.method == 'sms':
            return self.verify_sms_code(user_id, code)
        
        return False
    
    def add_trusted_device(self, user_id: str, device_fingerprint: str):
        """添加信任设备"""
        if user_id not in self.trusted_devices:
            self.trusted_devices[user_id] = {}
        
        self.trusted_devices[user_id][device_fingerprint] = \
            datetime.now(timezone.utc) + self.trusted_device_ttl
        
        logger.info(f"Device trusted for user {user_id}")
    
    def is_trusted_device(self, user_id: str, device_fingerprint: str) -> bool:
        """检查是否为信任设备"""
        devices = self.trusted_devices.get(user_id, {})
        expires_at = devices.get(device_fingerprint)
        
        if not expires_at:
            return False
        
        if datetime.now(timezone.utc) > expires_at:
            # 过期，移除
            del devices[device_fingerprint]
            return False
        
        return True
    
    def remove_trusted_device(self, user_id: str, device_fingerprint: str):
        """移除信任设备"""
        devices = self.trusted_devices.get(user_id, {})
        if device_fingerprint in devices:
            del devices[device_fingerprint]
            logger.info(f"Trusted device removed for user {user_id}")
    
    def disable_mfa(self, user_id: str) -> bool:
        """禁用MFA"""
        if user_id in self.mfa_configs:
            del self.mfa_configs[user_id]
            # 同时清除信任设备
            if user_id in self.trusted_devices:
                del self.trusted_devices[user_id]
            logger.info(f"MFA disabled for user {user_id}")
            return True
        return False
    
    def get_mfa_status(self, user_id: str) -> Dict:
        """获取MFA状态"""
        config = self.mfa_configs.get(user_id)
        
        if not config:
            return {
                'enabled': False,
                'method': None,
                'verified': False
            }
        
        return {
            'enabled': True,
            'method': config.method,
            'verified': config.verified,
            'created_at': config.created_at.isoformat() if config.created_at else None,
            'last_used': config.last_used.isoformat() if config.last_used else None,
            'backup_codes_remaining': len(config.backup_codes) if config.backup_codes else 0
        }


# 全局实例
_mfa_manager: Optional[MFAManager] = None

def get_mfa_manager() -> MFAManager:
    """获取MFA管理器"""
    global _mfa_manager
    if _mfa_manager is None:
        _mfa_manager = MFAManager()
    return _mfa_manager


if __name__ == '__main__':
    # 测试
    print("="*60)
    print("ACAS Pro - MFA Manager Test")
    print("="*60)
    
    mfa = MFAManager()
    user_id = 'user-123'
    
    # TOTP设置
    print("\n1. TOTP Setup")
    secret, qr_code, backup_codes = mfa.setup_totp(user_id, 'admin@acas.pro')
    print(f"   Secret: {secret}")
    print(f"   Backup codes: {backup_codes[:3]}...")
    
    # 生成TOTP码验证
    totp = pyotp.TOTP(secret)
    code = totp.now()
    print(f"   Current TOTP code: {code}")
    
    # 验证设置
    success = mfa.verify_totp_setup(user_id, code)
    print(f"   Setup verified: {success}")
    
    # 验证MFA
    print("\n2. MFA Verification")
    new_code = totp.now()
    verified = mfa.verify_mfa(user_id, new_code)
    print(f"   MFA verified: {verified}")
    
    # 备用码测试
    print("\n3. Backup Code Test")
    backup_code = backup_codes[0]
    verified = mfa.verify_mfa(user_id, backup_code)
    print(f"   Backup code verified: {verified}")
    print(f"   Remaining backup codes: {len(mfa.mfa_configs[user_id].backup_codes)}")
    
    # 信任设备
    print("\n4. Trusted Device")
    mfa.add_trusted_device(user_id, 'device-abc-123')
    is_trusted = mfa.is_trusted_device(user_id, 'device-abc-123')
    print(f"   Device trusted: {is_trusted}")
    
    # MFA状态
    print("\n5. MFA Status")
    status = mfa.get_mfa_status(user_id)
    print(f"   Status: {status}")
    
    print("\n" + "="*60)
    print("MFA test completed")
