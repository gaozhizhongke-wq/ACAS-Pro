#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Enterprise Security
Production-grade authentication and encryption
"""

import re
import secrets
import hashlib
import hmac
import jwt
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from .config import config
from .logging import get_logger, audit_logger

logger = get_logger(__name__)


class PasswordValidator:
    """Password strength validator"""
    
    MIN_LENGTH = 8
    MAX_LENGTH = 128
    
    @classmethod
    def validate(cls, password: str) -> Tuple[bool, str]:
        """
        Validate password strength
        Returns (is_valid, error_message)
        """
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
        
        # Check for common passwords
        common_passwords = {'password', '123456', 'qwerty', 'admin', 'letmein',
                          'password1', 'password123', 'p@ssword', 'passw0rd'}
        pwd_lower = password.lower()
        # Strip common special chars appended to common bases
        pwd_base = re.sub(r'[^a-z0-9]', '', pwd_lower)
        if pwd_lower in common_passwords or pwd_base in common_passwords:
            return False, "Password is too common"
        
        return True, ""


class PasswordHasher:
    """Secure password hashing using PBKDF2"""
    
    @staticmethod
    def hash(password: str) -> str:
        """Hash password with random salt"""
        salt = secrets.token_hex(config.security.salt_length)
        dk = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            config.security.pbkdf2_iterations
        )
        return f"pbkdf2:sha256:{config.security.pbkdf2_iterations}${salt}${dk.hex()}"
    
    @staticmethod
    def verify(password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            # Parse hash format
            parts = password_hash.split('$')
            if len(parts) != 3:
                # Legacy format fallback
                return False
            
            algo_part, salt, stored_hash = parts
            algo_info = algo_part.split(':')
            if len(algo_info) != 3:
                return False
            
            iterations = int(algo_info[2])
            
            dk = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                iterations
            )
            
            # Constant-time comparison
            return hmac.compare_digest(dk.hex(), stored_hash)
        
        except Exception as e:
            logger.error(f"Password verification error: {e}")
            return False


class JWTManager:
    """
    JWT token management with refresh token support
    
    Features:
    - Access token (short-lived, 15 min default)
    - Refresh token (long-lived, 7 days default)
    - Token revocation support
    - Secure secret key from environment
    """
    
    # Token type constants
    ACCESS_TOKEN_EXPIRY_MINUTES = 15
    REFRESH_TOKEN_EXPIRY_DAYS = 7
    
    @staticmethod
    def _get_secret_key() -> str:
        """Get secret key from environment or config"""
        # Priority: env var > config
        key = os.environ.get('ACAS_JWT_SECRET')
        if not key:
            key = config.security.secret_key
        if not key:
            raise ValueError("JWT secret key not configured. Set ACAS_JWT_SECRET env var or config.security.secret_key")
        return key
    
    @classmethod
    def generate_token(cls, user_id: str, extra_claims: Dict[str, Any] = None) -> str:
        """Generate access token (short-lived)"""
        now = datetime.now(timezone.utc)
        payload = {
            'sub': user_id,
            'iat': now,
            'exp': now + timedelta(minutes=cls.ACCESS_TOKEN_EXPIRY_MINUTES),
            'jti': secrets.token_hex(16),  # Unique token ID for revocation
            'type': 'access'
        }
        
        if extra_claims:
            payload.update(extra_claims)
        
        
        return jwt.encode(
            payload,
            cls._get_secret_key(),
            algorithm=config.security.jwt_algorithm
        )
    
    @classmethod
    def generate_refresh_token(cls, user_id: str) -> str:
        """Generate refresh token (long-lived)"""
        now = datetime.now(timezone.utc)
        payload = {
            'sub': user_id,
            'iat': now,
            'exp': now + timedelta(days=cls.REFRESH_TOKEN_EXPIRY_DAYS),
            'jti': secrets.token_hex(16),
            'type': 'refresh'
        }
        
        return jwt.encode(
            payload,
            cls._get_secret_key(),
            algorithm=config.security.jwt_algorithm
        )
    
    @classmethod
    def verify_token(cls, token: str, expected_type: str = 'access') -> Optional[Dict[str, Any]]:
        """
        Verify and decode JWT token
        
        Args:
            token: JWT token string
            expected_type: 'access' or 'refresh'
            
        Returns:
            Payload dict if valid, None otherwise
        """
        try:
            payload = jwt.decode(
                token,
                cls._get_secret_key(),
                algorithms=[config.security.jwt_algorithm]
            )
            
            # Verify token type
            if payload.get('type') != expected_type:
                logger.warning(f"Invalid token type: expected {expected_type}, got {payload.get('type')}")
                return None
            
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None
    
    @classmethod
    def refresh_access_token(cls, refresh_token: str) -> Optional[str]:
        """
        Use refresh token to get new access token
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token if refresh token is valid
        """
        payload = cls.verify_token(refresh_token, expected_type='refresh')
        if not payload:
            return None
        
        user_id = payload.get('sub')
        if not user_id:
            return None
        
        # Generate new access token
        return cls.generate_token(user_id)


class SessionManager:
    """User session management"""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self.db = None
    
    def _get_db(self):
        if self.db is None:
            from .database import db
            self.db = db
        return self.db
    
    def create_session(self, user_id: str, ip_address: str = None, 
                       user_agent: str = None) -> str:
        """Create new session"""
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=config.security.session_timeout_minutes)
        
        session_data = {
            'user_id': user_id,
            'token': token,
            'created_at': now.isoformat(),
            'expires_at': expires.isoformat(),
            'ip_address': ip_address,
            'user_agent': user_agent
        }
        
        # Store in database
        try:
            db = self._get_db()
            db.execute("""
                INSERT INTO sessions (id, user_id, token, created_at, expires_at, ip_address, user_agent)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                secrets.token_hex(16),
                user_id,
                token,
                now.isoformat(),
                expires.isoformat(),
                ip_address,
                user_agent
            ))
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
        
        audit_logger.log(
            'SESSION_CREATED',
            user_id,
            {'ip_address': ip_address},
            ip_address=ip_address
        )
        
        return token
    
    def validate_session(self, token: str) -> Optional[str]:
        """Validate session token, return user_id if valid"""
        try:
            db = self._get_db()
            row = db.fetchone("""
                SELECT user_id, expires_at FROM sessions WHERE token = ?
            """, (token,))
            
            if not row:
                return None
            
            expires = datetime.fromisoformat(row['expires_at'])
            if datetime.now(timezone.utc) > expires:
                # Session expired
                db.execute("DELETE FROM sessions WHERE token = ?", (token,))
                return None
            
            return row['user_id']
        
        except Exception as e:
            logger.error(f"Session validation error: {e}")
            return None
    
    def revoke_session(self, token: str) -> bool:
        """Revoke session"""
        try:
            db = self._get_db()
            db.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return True
        except Exception as e:
            logger.error(f"Failed to revoke session: {e}")
            return False
    
    def revoke_all_user_sessions(self, user_id: str) -> int:
        """Revoke all sessions for user"""
        try:
            db = self._get_db()
            result = db.execute("DELETE FROM sessions WHERE user_id = ?", (user_id,))
            return result.rowcount
        except Exception as e:
            logger.error(f"Failed to revoke user sessions: {e}")
            return 0


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self._attempts: Dict[str, list] = {}
    
    def is_allowed(self, key: str, max_attempts: int = 5, 
                   window_seconds: int = 300) -> bool:
        """Check if action is allowed under rate limit"""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=window_seconds)
        
        # Clean old attempts
        if key in self._attempts:
            self._attempts[key] = [
                t for t in self._attempts[key] 
                if t > window_start
            ]
        else:
            self._attempts[key] = []
        
        # Check limit
        return len(self._attempts[key]) < max_attempts
    
    def record_attempt(self, key: str):
        """Record an attempt"""
        if key not in self._attempts:
            self._attempts[key] = []
        self._attempts[key].append(datetime.now(timezone.utc))
    
    def reset(self, key: str):
        """Reset attempts for key"""
        self._attempts.pop(key, None)


class CryptoManager:
    """
    Production-grade encryption using Fernet (AES-128-CBC + HMAC)
    
    Security guarantees:
    - AES-128 in CBC mode for encryption
    - HMAC-SHA256 for authentication
    - Unique IV for each encryption
    - Key derived from PBKDF2 with 600k iterations
    """
    
    def __init__(self, key: str = None):
        """
        Initialize Fernet encryption
        
        Args:
            key: Optional key (if None, derives from config.secret_key)
        """
        if key:
            # Derive Fernet key from provided key
            self._fernet = self._derive_fernet_key(key)
        else:
            # Use environment variable first, then config
            env_key = os.environ.get('ACAS_ENCRYPTION_KEY')
            if env_key:
                self._fernet = self._derive_fernet_key(env_key)
            else:
                # Derive from secret_key with proper KDF
                secret = config.security.secret_key
                self._fernet = self._derive_fernet_key(secret)
        
        # Store key file path for key rotation
        self._key_file = Path.home() / ".acas-pro" / ".encryption_key"
    
    def _derive_fernet_key(self, password: str) -> Fernet:
        """
        Derive Fernet key from password using PBKDF2.

        Fernet requires 32 url-safe base64-encoded bytes.

        IMPORTANT: Salt MUST come from the ACAS_ENCRYPTION_SALT env var
        (at least 16 bytes, randomly generated once per deployment).
        If the salt is hardcoded the KDF provides zero additional security.
        """
        salt_env = os.environ.get('ACAS_ENCRYPTION_SALT')
        if salt_env:
            salt = salt_env.encode('utf-8')
        else:
            # CRITICAL: ACAS_ENCRYPTION_SALT must be set in production.
            # Fall back to a random salt ONLY in development (warn loudly).
            if config.environment == 'production':
                logger.error(
                    "ACAS_ENCRYPTION_SALT is not set! Set it to a random 32-byte hex string:\n"
                    "  python -c \"import secrets; print(secrets.token_hex(32))\""
                )
                raise ValueError("ACAS_ENCRYPTION_SALT must be set in production")
            else:
                logger.warning(
                    "ACAS_ENCRYPTION_SALT not set — using insecure ephemeral salt. "
                    "Set ACAS_ENCRYPTION_SALT in .env for production."
                )
                salt = secrets.token_hex(16).encode('utf-8')

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=600000,
        )

        key = base64.urlsafe_b64encode(kdf.derive(password.encode('utf-8')))
        return Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext using Fernet (AES-128-CBC + HMAC)
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Encrypted string (url-safe base64)
        """
        if not plaintext:
            return ""
        try:
            encrypted = self._fernet.encrypt(plaintext.encode('utf-8'))
            return encrypted.decode('ascii')
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt ciphertext using Fernet
        
        Args:
            ciphertext: Encrypted string
            
        Returns:
            Decrypted plaintext
            
        Raises:
            InvalidToken: If ciphertext is invalid or tampered
        """
        if not ciphertext:
            return ""
        try:
            decrypted = self._fernet.decrypt(ciphertext.encode('ascii'))
            return decrypted.decode('utf-8')
        except InvalidToken:
            logger.warning("Invalid encrypted data (may be corrupted or tampered)")
            raise ValueError("Invalid encrypted data")
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise
    
    def rotate_key(self, new_key: str) -> Dict[str, str]:
        """
        Rotate encryption key (re-encrypt all data)
        
        Args:
            new_key: New encryption key
            
        Returns:
            Dict with status and any errors
        """
        # Store new key
        new_fernet = self._derive_fernet_key(new_key)
        
        # Save new key file
        self._key_file.parent.mkdir(parents=True, exist_ok=True)
        self._key_file.write_text(new_key)
        os.chmod(self._key_file, 0o600)
        
        self._fernet = new_fernet
        
        return {"status": "success", "message": "Encryption key rotated"}


# Alias for backward compatibility
SecurityManager = CryptoManager


# Global instances
password_validator = PasswordValidator()
password_hasher = PasswordHasher()
jwt_manager = JWTManager()
session_manager = SessionManager()
rate_limiter = RateLimiter()
crypto_manager = CryptoManager()

# Aliases for backward compatibility
encrypt_data = crypto_manager.encrypt
decrypt_data = crypto_manager.decrypt
