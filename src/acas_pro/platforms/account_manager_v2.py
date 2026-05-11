"""ACAS Pro - Account Manager v2"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import uuid

from ..core.config_v2 import AppConfig
from ..core.database_v2 import DatabaseManager


class AccountManager:
    """Account manager - testable with DI"""
    
    def __init__(self, config: Optional[AppConfig] = None, db: Optional[DatabaseManager] = None):
        self.config = config or AppConfig.load()
        self.db = db or DatabaseManager(self.config.database)
        self._init_tables()
    
    def _init_tables(self):
        """Initialize tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                platform TEXT,
                username TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT
            )
        """)
    
    def create_account(self, platform: str, username: str) -> Tuple[bool, str]:
        """Create account"""
        account_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        self.db.execute("""
            INSERT INTO accounts (id, platform, username, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (account_id, platform, username, 'active', now))
        
        return True, account_id
    
    def get_account(self, account_id: str) -> Optional[Dict]:
        """Get account"""
        return self.db.fetchone("SELECT * FROM accounts WHERE id = ?", (account_id,))
    
    def list_accounts(self, platform: str = None) -> List[Dict]:
        """List accounts"""
        if platform:
            return self.db.fetchall("SELECT * FROM accounts WHERE platform = ?", (platform,))
        return self.db.fetchall("SELECT * FROM accounts")
