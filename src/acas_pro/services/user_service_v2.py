"""
ACAS Pro - User Service v2
Testable user service with dependency injection
"""

import json
from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass, asdict

from ..core.config_v2 import AppConfig
from ..core.security_v2 import PasswordValidator, PasswordHasher, JWTManager, SessionManager
from ..core.database_v2 import DatabaseManager


@dataclass
class UserProfile:
    """User profile data"""
    id: str
    account: str
    nickname: str
    email: str
    phone: str
    role: str = "user"
    status: str = "active"
    created_at: str = ""
    updated_at: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class UserService:
    """User service - testable with DI"""
    
    def __init__(self, 
                 config: Optional[AppConfig] = None,
                 db: Optional[DatabaseManager] = None,
                 password_validator: Optional[PasswordValidator] = None,
                 password_hasher: Optional[PasswordHasher] = None,
                 jwt_manager: Optional[JWTManager] = None,
                 session_manager: Optional[SessionManager] = None):
        self.config = config or AppConfig.load()
        self.db = db or DatabaseManager(self.config.database)
        self.password_validator = password_validator or PasswordValidator()
        self.password_hasher = password_hasher or PasswordHasher(self.config.security)
        self.jwt_manager = jwt_manager or JWTManager(self.config.security)
        self.session_manager = session_manager or SessionManager(self.config.security)
        self._init_tables()
    
    def _init_tables(self):
        """Initialize database tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                account TEXT UNIQUE NOT NULL,
                nickname TEXT,
                email TEXT,
                phone TEXT,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                status TEXT DEFAULT 'active',
                created_at TEXT,
                updated_at TEXT
            )
        """)
    
    def register(self, account: str, password: str, email: str = "", 
                 phone: str = "", nickname: str = "") -> Tuple[bool, str]:
        """Register new user"""
        # Validate password
        is_valid, msg = self.password_validator.validate(password)
        if not is_valid:
            return False, msg
        
        # Check if account exists
        existing = self.db.fetchone(
            "SELECT id FROM users WHERE account = ?",
            (account,)
        )
        if existing:
            return False, "Account already exists"
        
        # Hash password
        password_hash = self.password_hasher.hash(password)
        
        # Create user
        import uuid
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        self.db.execute("""
            INSERT INTO users (id, account, nickname, email, phone, password_hash, role, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, account, nickname, email, phone, password_hash, "user", "active", now, now))
        
        return True, user_id
    
    def login(self, account: str, password: str) -> Tuple[bool, str]:
        """Login user"""
        user = self.db.fetchone(
            "SELECT id, password_hash, status FROM users WHERE account = ?",
            (account,)
        )
        
        if not user:
            return False, "Invalid account or password"
        
        if user['status'] != 'active':
            return False, "Account is disabled"
        
        if not self.password_hasher.verify(password, user['password_hash']):
            return False, "Invalid account or password"
        
        # Generate token
        token = self.jwt_manager.generate_token(user['id'])
        
        return True, token
    
    def get_user(self, user_id: str) -> Optional[UserProfile]:
        """Get user by ID"""
        row = self.db.fetchone(
            "SELECT * FROM users WHERE id = ?",
            (user_id,)
        )
        
        if not row:
            return None
        
        return UserProfile(
            id=row['id'],
            account=row['account'],
            nickname=row['nickname'] or "",
            email=row['email'] or "",
            phone=row['phone'] or "",
            role=row['role'],
            status=row['status'],
            created_at=row['created_at'] or "",
            updated_at=row['updated_at'] or ""
        )
    
    def update_user(self, user_id: str, **kwargs) -> Tuple[bool, str]:
        """Update user"""
        allowed_fields = {'nickname', 'email', 'phone'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False, "No valid fields to update"
        
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        values = list(updates.values()) + [user_id]
        
        self.db.execute(
            f"UPDATE users SET {set_clause}, updated_at = ? WHERE id = ?",
            (*list(updates.values()), datetime.now(timezone.utc).isoformat(), user_id)
        )
        
        return True, "User updated"
    
    def delete_user(self, user_id: str) -> Tuple[bool, str]:
        """Delete user (soft delete)"""
        self.db.execute(
            "UPDATE users SET status = 'deleted', updated_at = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), user_id)
        )
        return True, "User deleted"
    
    def list_users(self, limit: int = 100, offset: int = 0) -> list:
        """List users"""
        rows = self.db.fetchall(
            "SELECT * FROM users WHERE status != 'deleted' LIMIT ? OFFSET ?",
            (limit, offset)
        )
        return [UserProfile(**row).to_dict() for row in rows]
