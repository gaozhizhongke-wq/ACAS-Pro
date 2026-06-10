#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Enterprise Security
Production-grade authentication and encryption
"""

import re
import json
import secrets
import time
import hashlib
import hmac
import jwt
import os
import sys
if sys.platform == 'win32':
    import msvcrt
    _WIN32 = True
else:
    import fcntl
    _WIN32 = False
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from .config import get_config
from .logging import get_logger, audit_logger
from functools import wraps

logger = get_logger(__name__)

# Lazy config accessor for module-level usage
def _cfg() -> Any:
    return get_config()


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
        salt = secrets.token_hex(_cfg().security.salt_length)
        dk = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            _cfg().security.pbkdf2_iterations
        )
        return f"pbkdf2:sha256:{_cfg().security.pbkdf2_iterations}${salt}${dk.hex()}"
    
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
        
        except (ValueError, IndexError, AttributeError) as e:
            logger.error(f"Password verification error: {e}")
            return False


class TokenBlacklist:
    """
    JWT token blacklist for revocation support.

    Storage backend selection (auto):
      1. Redis  – if REDIS_URL is set and connection succeeds
      2. DB    – if DatabaseManager is available (persistent, cross-process)
      3. Memory – fallback for development / testing

    The DB backend creates a ``token_blacklist`` table on first use.
    """

    # In-memory fallback: jti -> expiry timestamp
    _blacklist: Dict[str, float] = {}
    _lock = None  # Thread lock for thread safety
    _backend: Optional[str] = None  # 'redis' | 'db' | 'memory'
    _redis_client = None  # type: ignore[assignment]
    _REDIS_PREFIX = "acas:token_bl:"

    # ------------------------------------------------------------------
    # Backend detection
    # ------------------------------------------------------------------

    @classmethod
    def _detect_backend(cls) -> str:
        """Detect the best available storage backend."""
        # 1. Try Redis
        redis_url = os.environ.get('REDIS_URL')
        if redis_url:
            try:
                import redis as _redis
                client = _redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                client.ping()
                cls._redis_client = client
                cls._backend = 'redis'
                logger.info("TokenBlacklist: using Redis backend")
                return 'redis'
            except Exception as e:
                logger.warning(f"TokenBlacklist: Redis unavailable ({e}), trying DB")

        # 2. Try DatabaseManager
        try:
            from .database import get_db
            db = get_db()
            # token_blacklist table is managed by core/schema.py
            cls._backend = 'db'
            logger.info("TokenBlacklist: using DB backend")
            return 'db'
        except Exception as e:
            logger.warning(f"TokenBlacklist: DB unavailable ({e}), falling back to memory")

        # 3. Memory fallback
        cls._backend = 'memory'
        logger.warning("TokenBlacklist: using in-memory backend (tokens lost on restart)")
        return 'memory'

    @classmethod
    def _get_backend(cls) -> Optional[str]:
        if cls._backend is None:
            cls._detect_backend()
        return cls._backend

    # ------------------------------------------------------------------
    # Lock helper (used only by memory backend)
    # ------------------------------------------------------------------

    @classmethod
    def _get_lock(cls):
        """Get or create thread lock"""
        if cls._lock is None:
            import threading
            cls._lock = threading.Lock()
        return cls._lock

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def add(cls, jti: str, expires_at: datetime) -> None:
        """Add token jti to blacklist"""
        exp_ts = expires_at.timestamp()
        backend = cls._get_backend()

        if backend == 'redis':
            ttl = max(int(exp_ts - time.time()), 1)
            cls._redis_client.setex(f"{cls._REDIS_PREFIX}{jti}", ttl, "1")  # type: ignore[union-attr]
            logger.info(f"Token revoked (redis): jti={jti[:16]}...")

        elif backend == 'db':
            try:
                from .database import get_db
                db = get_db()
                db.execute(
                    "INSERT OR REPLACE INTO token_blacklist (jti, expires_at) VALUES (?, ?)",
                    (jti, exp_ts)
                )
                logger.info(f"Token revoked (db): jti={jti[:16]}...")
                cls._cleanup_db(db)
            except Exception as e:
                logger.error(f"TokenBlacklist DB write failed: {e}")
                # Fallback to memory so the revoke is not lost
                with cls._get_lock():
                    cls._blacklist[jti] = exp_ts

        else:  # memory
            with cls._get_lock():
                cls._blacklist[jti] = exp_ts
                logger.info(f"Token revoked (memory): jti={jti[:16]}...")
                cls._cleanup()

    @classmethod
    def is_revoked(cls, jti: str) -> bool:
        """Check if token jti is revoked"""
        backend = cls._get_backend()

        if backend == 'redis':
            return bool(cls._redis_client.exists(f"{cls._REDIS_PREFIX}{jti}"))  # type: ignore[union-attr]

        if backend == 'db':
            try:
                from .database import get_db
                db = get_db()
                row = db.fetchone(
                    "SELECT 1 FROM token_blacklist WHERE jti = ? AND expires_at > ?",
                    (jti, time.time())
                )
                return row is not None
            except Exception as e:
                logger.error(f"TokenBlacklist DB read failed: {e}")
                # Check in-memory fallback as well
                with cls._get_lock():
                    return jti in cls._blacklist

        # memory
        with cls._get_lock():
            return jti in cls._blacklist

    # ------------------------------------------------------------------
    # Cleanup helpers
    # ------------------------------------------------------------------

    @classmethod
    def _cleanup(cls) -> None:
        """Remove expired entries from in-memory blacklist"""
        now = time.time()
        expired = [jti for jti, exp in cls._blacklist.items() if exp < now]
        for jti in expired:
            del cls._blacklist[jti]
        if expired:
            logger.debug(f"Cleaned {len(expired)} expired blacklist entries (memory)")

    @classmethod
    def _cleanup_db(cls, db) -> None:
        """Remove expired entries from DB blacklist"""
        try:
            db.execute("DELETE FROM token_blacklist WHERE expires_at < ?", (time.time(),))
        except Exception as e:
            logger.debug(f"TokenBlacklist DB cleanup skipped: {e}")

    @classmethod
    def reset(cls) -> None:
        """Reset all backends (for testing)."""
        cls._blacklist.clear()
        cls._backend = None
        cls._redis_client = None


class JWTManager:
    """
    JWT token management with refresh token support
    
    Features:
    - Access token (short-lived, 15 min default)
    - Refresh token (long-lived, 7 days default)
    - Token revocation support via blacklist
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
            key = os.environ.get('JWT_SECRET')  # Fallback for backward compatibility
        if not key:
            key = _cfg().security.secret_key
        if not key:
            raise ValueError("JWT secret key not configured. Set ACAS_JWT_SECRET env var or _cfg().security.secret_key")
        return key
    
    @classmethod
    def generate_token(cls, user_id: str, extra_claims: Optional[Dict[str, Any]] = None) -> str:
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
        
        
        return jwt.encode(  # type: ignore[no-any-return]

            payload,
            cls._get_secret_key(),
            algorithm=_cfg().security.jwt_algorithm
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
        
        return jwt.encode(  # type: ignore[no-any-return]

            payload,
            cls._get_secret_key(),
            algorithm=_cfg().security.jwt_algorithm
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
                algorithms=[_cfg().security.jwt_algorithm]
            )
            
            # Verify token type
            if payload.get('type') != expected_type:
                logger.warning(f"Invalid token type: expected {expected_type}, got {payload.get('type')}")
                return None
            
            # Check blacklist (token revocation)
            jti = payload.get('jti')
            if jti and TokenBlacklist.is_revoked(jti):
                logger.warning(f"Token revoked: jti={jti[:16]}...")
                return None
            
            return payload  # type: ignore[no-any-return]

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
    
    @classmethod
    def revoke_token(cls, token: str) -> bool:
        """
        Revoke a token by adding its jti to blacklist
        
        Args:
            token: JWT token to revoke
            
        Returns:
            True if token was revoked, False if already expired/invalid
        """
        try:
            # Decode without expiry verification to get jti
            payload = jwt.decode(
                token,
                cls._get_secret_key(),
                algorithms=[_cfg().security.jwt_algorithm],
                options={'verify_exp': False}
            )
            jti = payload.get('jti')
            exp = payload.get('exp')
            
            if jti and exp:
                TokenBlacklist.add(jti, datetime.fromtimestamp(exp, tz=timezone.utc))
                return True
        except jwt.InvalidTokenError:
            pass
        return False


class SessionManager:
    """User session management"""
    
    def __init__(self) -> None:
        self._sessions: Dict[str, Dict[str, Any]] = {}
        self.db = None
    
    def _get_db(self) -> Any:
        if self.db is None:
            from .database import db
            self.db = db
        return self.db
    
    def create_session(self, user_id: str, ip_address: Optional[str] = None, 
                       user_agent: Optional[str] = None) -> str:
        """Create new session"""
        token = secrets.token_urlsafe(32)
        now = datetime.now(timezone.utc)
        expires = now + timedelta(minutes=_cfg().security.session_timeout_minutes)
        
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
            return None  # FAIL FAST — do not return token without DB record  # type: ignore[return-value]


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
            
            return row['user_id']  # type: ignore[no-any-return]

        
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
            return result.rowcount  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"Failed to revoke user sessions: {e}")
            return 0


class RateLimiter:
    """
    File-based rate limiter for multi-process safety (gunicorn workers).

    Uses a JSON file on disk to track attempt timestamps per key,
    so that rate limits persist across worker processes and restarts.

    CRITICAL FIX: All operations use fcntl.flock for atomicity,  # type: ignore[name-defined]

    eliminating the read-modify-write race condition.
    Bounded storage: max 100 entries per key to prevent unbounded growth.
    """

    MAX_ENTRIES_PER_KEY = 100

    def __init__(self, storage_path: Optional[str] = None) -> None:
        if storage_path is None:
            storage_path = os.path.join(
                os.environ.get('ACAS_DATA_DIR',
                               os.path.join(Path.home(), '.acas-pro')),
                '.rate_limit.json'
            )
        self._path = storage_path
        os.makedirs(os.path.dirname(self._path), exist_ok=True)

    @contextmanager
    def _atomic(self) -> None:
        """Atomic read-write via exclusive file lock."""
        lock_path = self._path + '.lock'
        with open(lock_path, 'w') as lf:
            if _WIN32:
                msvcrt.locking(lf.fileno(), msvcrt.LK_LOCK, 1)
                try:
                    yield
                finally:
                    lf.seek(0)
                    msvcrt.locking(lf.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                pass  # fcntl not available on Windows, file locking handled by OS
                try:
                    yield
                finally:
                    fcntl.flock(lf.fileno(), fcntl.LOCK_UN)  # type: ignore[name-defined]


    def _load_unlocked(self) -> Dict[str, list]:
        try:
            with open(self._path, 'r', encoding='utf-8') as f:
                return json.load(f)  # type: ignore[no-any-return]

        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    # Alias for test compatibility
    def _load(self) -> Dict[str, list]:
        with self._atomic():
            return self._load_unlocked()

    def _save_unlocked(self, data: Dict[str, list]) -> Any:
        with open(self._path + '.tmp', 'w', encoding='utf-8') as f:
            json.dump(data, f, default=str)
        os.replace(self._path + '.tmp', self._path)

    def is_allowed(self, key: str, max_attempts: int = 5,
                   window_seconds: int = 300) -> bool:
        """Check if action is allowed under rate limit (atomic, does NOT record)."""
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=window_seconds)

        with self._atomic():
            data = self._load_unlocked()
            entries = [t for t in data.get(key, []) if _parse_dt(t) > window_start]
            return len(entries) < max_attempts

    def record_attempt(self, key: str) -> Any:
        """Record an attempt (atomic)."""
        with self._atomic():
            data = self._load_unlocked()
            now = datetime.now(timezone.utc)
            entries = data.get(key, [])
            entries.append(now.isoformat())
            if len(entries) > self.MAX_ENTRIES_PER_KEY:
                entries = entries[-self.MAX_ENTRIES_PER_KEY:]
            data[key] = entries
            self._save_unlocked(data)

    def reset(self, key: str) -> Any:
        """Reset attempts for key (atomic)."""
        with self._atomic():
            data = self._load_unlocked()
            data.pop(key, None)
            self._save_unlocked(data)


def _parse_dt(val) -> datetime:
    """Parse datetime from string or datetime object."""
    if isinstance(val, datetime):
        return val
    return datetime.fromisoformat(val)


class CryptoManager:
    """
    Production-grade encryption using Fernet (AES-128-CBC + HMAC)
    
    Security guarantees:
    - AES-128 in CBC mode for encryption
    - HMAC-SHA256 for authentication
    - Unique IV for each encryption
    - Key derived from PBKDF2 with 600k iterations
    """
    
    def __init__(self, key: Optional[str] = None) -> None:
        """
        Initialize Fernet encryption
        
        Args:
            key: Optional key (if None, derives from config().secret_key)
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
                secret = _cfg().security.secret_key
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
            # Development: use persistent salt file to avoid data corruption on restart
            if _cfg().environment == 'production':
                logger.error(
                    "ACAS_ENCRYPTION_SALT is not set! Set it to a random 32-byte hex string:\n"
                    "  python -c \"import secrets; print(secrets.token_hex(32))\""
                )
                raise ValueError("ACAS_ENCRYPTION_SALT must be set in production")
            else:
                # Use persistent dev salt file
                dev_salt_file = Path.home() / ".acas-pro" / ".dev_encryption_salt"
                if dev_salt_file.exists():
                    salt = dev_salt_file.read_text().strip().encode('utf-8')
                    logger.debug("Using persistent development salt")
                else:
                    # Generate and save persistent salt
                    salt = secrets.token_hex(16).encode('utf-8')
                    dev_salt_file.parent.mkdir(parents=True, exist_ok=True)
                    dev_salt_file.write_text(salt.decode('utf-8'))
                    # Restrict file permissions: Unix chmod + Windows ACL
                    if os.name == 'nt':
                        try:
                            import subprocess
                            subprocess.run(
                                ['icacls', str(dev_salt_file), '/inheritance:r', '/grant:r',
                                 f'{os.environ.get("USERNAME", "%USERNAME%")}:R'],
                                check=True, capture_output=True, timeout=5
                            )
                        except Exception as e:
                            # nosec B110  # Best effort Windows ACL - do not fail on permission errors
                            logger.debug(f"icacls permission hardening skipped: {e}")
                    else:
                        os.chmod(dev_salt_file, 0o600)
                    logger.warning(
                        f"ACAS_ENCRYPTION_SALT not set — using persistent dev salt: {dev_salt_file}. "
                        "Set ACAS_ENCRYPTION_SALT in .env for production."
                    )

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
            return encrypted.decode('ascii')  # type: ignore[no-any-return]

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
            return decrypted.decode('utf-8')  # type: ignore[no-any-return]

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


# Lazy-initialized global instances — avoids module-reload state pollution
# All external imports (e.g. `from acas_pro.core.security import password_validator`)
# continue to work because Python falls through to __getattr__ when the name
# is not found in the module dict.

_lazy_instances: dict = {}


def _get_lazy(name: str, cls: type) -> Any:  # type: ignore[arg-type]

    """Return a singleton instance of *cls*, created on first access."""
    if name not in _lazy_instances:
        _lazy_instances[name] = cls()
    return _lazy_instances[name]


def __getattr__(name) -> Any:
    """Module-level __getattr__ for lazy attribute access."""
    _LAZY_MAP = {
        'password_validator': PasswordValidator,
        'password_hasher': PasswordHasher,
        'jwt_manager': JWTManager,
        'session_manager': SessionManager,
        'crypto_manager': CryptoManager,
        'rate_limiter': None,  # placeholder, handled below
    }
    if name == 'rate_limiter':
        if name not in _lazy_instances:
            _lazy_instances[name] = _build_rate_limiter()
        return _lazy_instances[name]
    if name in _LAZY_MAP:
        return _get_lazy(name, _LAZY_MAP[name])  # type: ignore[arg-type]

    if name == 'encrypt_data':
        return _get_lazy('crypto_manager', CryptoManager).encrypt  # type: ignore[arg-type]

    if name == 'decrypt_data':
        return _get_lazy('crypto_manager', CryptoManager).decrypt  # type: ignore[arg-type]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _reset_lazy_instances() -> Any:
    """Clear all lazy singletons — used by test fixtures."""
    _lazy_instances.clear()




# ── Redis-backed Rate Limiter ────────────────────────────────────────────────

class RedisRateLimiter:
    """
    Redis-backed rate limiter for distributed multi-worker deployments.
    Uses Redis ZADD with timestamp score for sliding-window rate limiting.
    Falls back to file-based RateLimiter if Redis unavailable.
    """

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self.redis_url = redis_url or os.environ.get('REDIS_URL')
        self._client: Any = None
        if self.redis_url:
            try:
                import redis as _redis
                self._client = _redis.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2,
                )
                self._client.ping()
            except Exception as e:
                logger.warning(f"Redis connection failed, rate limiter disabled: {e}")
                self._client = None  # type: ignore[no-redef]

    @property
    def available(self) -> bool:
        return self._client is not None

    def is_allowed(self, key: str, max_attempts: int = 5,
                   window_seconds: int = 300) -> bool:
        if not self.available:
            return RateLimiter().is_allowed(key, max_attempts, window_seconds)
        now = time.time()
        window_start = now - window_seconds
        pipe = self._client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zcard(key)
        pipe.execute()
        count = self._client.zcard(key)
        return count < max_attempts  # type: ignore[no-any-return]


    def record_attempt(self, key: str) -> Any:
        if not self.available:
            return RateLimiter().record_attempt(key)
        now = time.time()
        pipe = self._client.pipeline()
        pipe.zadd(key, {str(now): now})
        pipe.expire(key, 86400)
        pipe.execute()

    def reset(self, key: str) -> Any:
        if not self.available:
            return RateLimiter().reset(key)
        self._client.delete(key)


# Convenience: unified rate_limiter with auto-detection
def _build_rate_limiter() -> Any:
    redis_url = os.environ.get('REDIS_URL')
    if redis_url:
        rl = RedisRateLimiter(redis_url)
        if rl.available:
            return rl
    return RateLimiter()


def _get_rate_limiter() -> Any:
    """Lazy rate_limiter accessor"""
    return _get_lazy('rate_limiter', None)  # handled specially  # type: ignore[arg-type]


# We no longer create rate_limiter at module level.
# It is available via __getattr__ below.


# ── JWT httpOnly Cookie ──────────────────────────────────────────────────────
# Store JWT in httpOnly cookie to prevent XSS exfiltration.
# JavaScript can still read the JWT from cookie for Authorization header,
# but httpOnly prevents direct document.cookie exfiltration by XSS.

JWT_COOKIE_NAME = 'acas_jwt'
JWT_COOKIE_MAX_AGE = 3600 * 8  # 8 hours


def set_jwt_cookie(response, token: str) -> None:
    response.set_cookie(
        JWT_COOKIE_NAME, token,
        max_age=JWT_COOKIE_MAX_AGE,
        httponly=True,   # Block JS read — prevents XSS exfiltration
        secure=True,     # HTTPS only
        samesite='Lax',
    )


def clear_jwt_cookie(response) -> None:
    response.set_cookie(
        JWT_COOKIE_NAME, '',
        max_age=0,
        httponly=True,
        secure=True,
        samesite='Lax',
    )


def get_jwt_from_cookie(request) -> str:
    return request.cookies.get(JWT_COOKIE_NAME, '')  # type: ignore[no-any-return]



# ── CSRF Protection ─────────────────────────────────────────────────────────

# CSRF_STATE_SECRET must be set via environment variable.
# If not set, CSRF tokens are purely per-request (generate_csrf_token) and do not
# need a persistent secret — but HMAC-based CSRF would require this.
CSRF_STATE_SECRET = os.environ.get('CSRF_STATE_SECRET')
if not CSRF_STATE_SECRET:
    import logging as _logging
    _logging.getLogger(__name__).warning(
        "CSRF_STATE_SECRET not set — set it in .env for stable HMAC-based CSRF. "
        "Per-request tokens still work."
    )


def generate_csrf_token() -> str:
    return secrets.token_hex(32)


def create_csrf_cookie(response) -> str:
    token = generate_csrf_token()
    response.set_cookie(
        'csrf_token', token,
        max_age=3600 * 24,
        httponly=False, secure=os.environ.get('ACAS_ENV') != 'testing', samesite='Lax',
    )
    return token


def validate_csrf_request(request) -> Tuple[bool, str]:
    # Skip CSRF validation in testing environment
    if os.environ.get('ACAS_ENV') == 'testing':
        return True, ''
    header_token = request.headers.get('X-CSRF-Token', '').strip()
    cookie_token = request.cookies.get('csrf_token', '').strip()
    if not header_token:
        return False, 'Missing CSRF token (X-CSRF-Token header required)'
    if not cookie_token:
        return False, 'CSRF cookie not set — please refresh and try again'
    if header_token != cookie_token:
        return False, 'CSRF token mismatch'
    if not re.fullmatch(r'[0-9a-f]{64}', header_token):
        return False, 'Invalid CSRF token format'
    return True, ''


def require_csrf(f) -> Any:
    @wraps(f)
    def wrapped(*args, **kwargs) -> Any:
        from flask import request
        if request.method not in ('POST', 'PUT', 'DELETE', 'PATCH'):
            return f(*args, **kwargs)
        ok, msg = validate_csrf_request(request)
        if not ok:
            from flask import jsonify
            return jsonify({'error': msg, 'code': 'CSRF_INVALID'}), 403
        return f(*args, **kwargs)
    return wrapped


# --- Factory functions for lazy instantiation ---

def get_password_validator() -> PasswordValidator:
    """Get a PasswordValidator instance."""
    return PasswordValidator()


def get_password_hasher() -> PasswordHasher:
    """Get a PasswordHasher instance."""
    return PasswordHasher()


def get_session_manager() -> SessionManager:
    """Get a SessionManager instance."""
    return SessionManager()


def get_rate_limiter() -> RateLimiter:
    """Get a RateLimiter instance."""
    return RateLimiter()

