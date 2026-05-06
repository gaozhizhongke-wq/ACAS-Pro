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
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple

from acas_pro.core.config import config
from acas_pro.core.logging import get_logger, audit_logger

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
        common_passwords = {'password', '123456', 'qwerty', 'admin', 'letmein'}
        if password.lower() in common_passwords:
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
    """JWT token management"""
    
    @staticmethod
    def generate_token(user_id: str, extra_claims: Dict[str, Any] = None) -> str:
        """Generate JWT token"""
        now = datetime.utcnow()
        payload = {
            'sub': user_id,
            'iat': now,
            'exp': now + timedelta(hours=config.security.jwt_expiry_hours),
            'jti': secrets.token_hex(16),  # Unique token ID
            'type': 'access'
        }
        
        if extra_claims:
            payload.update(extra_claims)
        
        return jwt.encode(
            payload,
            config.security.secret_key,
            algorithm=config.security.jwt_algorithm
        )
    
    @staticmethod
    def verify_token(token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(
                token,
                config.security.secret_key,
                algorithms=[config.security.jwt_algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None


class SessionManager:
    """User session management"""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self.db = None
    
    def _get_db(self):
        if self.db is None:
            from acas_pro.core.database import db
            self.db = db
        return self.db
    
    def create_session(self, user_id: str, ip_address: str = None, 
                       user_agent: str = None) -> str:
        """Create new session"""
        token = secrets.token_urlsafe(32)
        now = datetime.utcnow()
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
            if datetime.utcnow() > expires:
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
        now = datetime.utcnow()
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
        self._attempts[key].append(datetime.utcnow())
    
    def reset(self, key: str):
        """Reset attempts for key"""
        self._attempts.pop(key, None)


# Global instances
password_validator = PasswordValidator()
password_hasher = PasswordHasher()
jwt_manager = JWTManager()
session_manager = SessionManager()
rate_limiter = RateLimiter()
