"""
ACAS Pro - Security v2
Dependency injection based, testable security module
"""

import re
import json
import secrets
import time
import hashlib
import hmac
import jwt
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from .config_v2 import AppConfig, SecurityConfig


class PasswordValidator:
    """Password strength validator - no side effects"""
    
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    
    @classmethod
    def validate(cls, password: str) -> Tuple[bool, str]:
        """Validate password strength"""
        if len(password) < cls.MIN_LENGTH:
            return False, f"Password must be at least {cls.MIN_LENGTH} characters"
        
        if len(password) > cls.MAX_LENGTH:
            return False, f"Password must not exceed {cls.MAX_LENGTH} characters"
        
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character"
        
        return True, "Password is valid"


class PasswordHasher:
    """Password hashing with PBKDF2 - no side effects"""
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
    
    def hash(self, password: str) -> str:
        """Hash password"""
        salt = os.urandom(32)
        iterations = self.config.pbkdf2_iterations
        
        key = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt,
            iterations
        )
        
        return f"pbkdf2_sha256${iterations}${salt.hex()}${key.hex()}"
    
    def verify(self, password: str, hash_str: str) -> bool:
        """Verify password against hash"""
        try:
            parts = hash_str.split('$')
            if len(parts) != 4:
                return False
            
            algorithm, iterations, salt_hex, key_hex = parts
            
            if algorithm != 'pbkdf2_sha256':
                return False
            
            salt = bytes.fromhex(salt_hex)
            iterations = int(iterations)
            
            key = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt,
                iterations
            )
            
            return key.hex() == key_hex
        except Exception:
            return False


class JWTManager:
    """JWT token manager - no side effects"""
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
    
    def generate_token(self, user_id: str, claims: Dict[str, Any] = None, 
                      expires_in: int = 3600) -> str:
        """Generate JWT token"""
        now = datetime.now(timezone.utc)
        payload = {
            'sub': user_id,
            'iat': now,
            'exp': now + timedelta(seconds=expires_in),
            'jti': secrets.token_hex(16)
        }
        
        if claims:
            payload.update(claims)
        
        secret = self.config.jwt_secret or self.config.secret_key or 'dev-secret'
        return jwt.encode(payload, secret, algorithm='HS256')
    
    def verify_token(self, token: str) -> Tuple[bool, Dict[str, Any]]:
        """Verify JWT token"""
        try:
            secret = self.config.jwt_secret or self.config.secret_key or 'dev-secret'
            payload = jwt.decode(token, secret, algorithms=['HS256'])
            return True, payload
        except jwt.ExpiredSignatureError:
            return False, {'error': 'Token expired'}
        except jwt.InvalidTokenError:
            return False, {'error': 'Invalid token'}


class CryptoManager:
    """Encryption manager - no side effects"""
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self._fernet = None
    
    def _get_fernet(self) -> Fernet:
        """Lazy-load Fernet instance"""
        if self._fernet is None:
            key = self._derive_key()
            self._fernet = Fernet(key)
        return self._fernet
    
    def _derive_key(self) -> bytes:
        """Derive encryption key"""
        password = (self.config.secret_key or 'dev-secret').encode('utf-8')
        salt = (self.config.encryption_salt or 'dev-salt').encode('utf-8')
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password))
        return key
    
    def encrypt(self, data: str) -> str:
        """Encrypt data"""
        return self._get_fernet().encrypt(data.encode('utf-8')).decode('utf-8')
    
    def decrypt(self, data: str) -> str:
        """Decrypt data"""
        try:
            return self._get_fernet().decrypt(data.encode('utf-8')).decode('utf-8')
        except InvalidToken:
            raise ValueError("Invalid or corrupted data")


class SessionManager:
    """Session manager - no side effects"""
    
    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()
        self._sessions: Dict[str, Dict[str, Any]] = {}
    
    def create_session(self, user_id: str, data: Dict[str, Any] = None) -> str:
        """Create new session"""
        session_id = secrets.token_hex(32)
        self._sessions[session_id] = {
            'user_id': user_id,
            'created_at': time.time(),
            'data': data or {}
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data"""
        session = self._sessions.get(session_id)
        if not session:
            return None
        
        # Check expiration
        created_at = session.get('created_at', 0)
        if time.time() - created_at > self.config.session_timeout:
            del self._sessions[session_id]
            return None
        
        return session
    
    def destroy_session(self, session_id: str) -> bool:
        """Destroy session"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False


# Factory functions for DI container
def create_password_validator() -> PasswordValidator:
    return PasswordValidator()


def create_password_hasher(config: Optional[AppConfig] = None) -> PasswordHasher:
    cfg = config or AppConfig.load()
    return PasswordHasher(cfg.security)


def create_jwt_manager(config: Optional[AppConfig] = None) -> JWTManager:
    cfg = config or AppConfig.load()
    return JWTManager(cfg.security)


def create_crypto_manager(config: Optional[AppConfig] = None) -> CryptoManager:
    cfg = config or AppConfig.load()
    return CryptoManager(cfg.security)


def create_session_manager(config: Optional[AppConfig] = None) -> SessionManager:
    cfg = config or AppConfig.load()
    return SessionManager(cfg.security)
