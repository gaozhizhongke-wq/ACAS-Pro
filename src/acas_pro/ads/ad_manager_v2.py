"""ACAS Pro - Ad Manager v2"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import uuid

from ..core.config_v2 import AppConfig
from ..core.database_v2 import DatabaseManager


class AdManager:
    """Ad manager - testable with DI"""
    
    def __init__(self, config: Optional[AppConfig] = None, db: Optional[DatabaseManager] = None):
        self.config = config or AppConfig.load()
        self.db = db or DatabaseManager(self.config.database)
        self._init_tables()
    
    def _init_tables(self):
        """Initialize tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                budget REAL DEFAULT 0,
                spent REAL DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS ads (
                id TEXT PRIMARY KEY,
                campaign_id TEXT,
                title TEXT,
                content TEXT,
                status TEXT DEFAULT 'active',
                created_at TEXT
            )
        """)
    
    def create_campaign(self, name: str, budget: float = 0) -> Tuple[bool, str]:
        """Create campaign"""
        campaign_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        self.db.execute("""
            INSERT INTO campaigns (id, name, budget, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (campaign_id, name, budget, 'active', now, now))
        
        return True, campaign_id
    
    def get_campaign(self, campaign_id: str) -> Optional[Dict]:
        """Get campaign"""
        return self.db.fetchone("SELECT * FROM campaigns WHERE id = ?", (campaign_id,))
    
    def list_campaigns(self, limit: int = 100) -> List[Dict]:
        """List campaigns"""
        return self.db.fetchall("SELECT * FROM campaigns LIMIT ?", (limit,))
    
    def update_campaign(self, campaign_id: str, **kwargs) -> Tuple[bool, str]:
        """Update campaign"""
        allowed = {'name', 'budget', 'status'}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        
        if not updates:
            return False, "No valid fields"
        
        set_clause = ", ".join(f"{k} = ?" for k in updates.keys())
        self.db.execute(
            f"UPDATE campaigns SET {set_clause}, updated_at = ? WHERE id = ?",
            (*list(updates.values()), datetime.now(timezone.utc).isoformat(), campaign_id)
        )
        return True, "Updated"
    
    def delete_campaign(self, campaign_id: str) -> Tuple[bool, str]:
        """Delete campaign"""
        self.db.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
        return True, "Deleted"
    
    def create_ad(self, campaign_id: str, title: str, content: str) -> Tuple[bool, str]:
        """Create ad"""
        ad_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        self.db.execute("""
            INSERT INTO ads (id, campaign_id, title, content, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (ad_id, campaign_id, title, content, 'active', now))
        
        return True, ad_id
    
    def get_ad(self, ad_id: str) -> Optional[Dict]:
        """Get ad"""
        return self.db.fetchone("SELECT * FROM ads WHERE id = ?", (ad_id,))
    
    def list_ads(self, campaign_id: str = None, limit: int = 100) -> List[Dict]:
        """List ads"""
        if campaign_id:
            return self.db.fetchall("SELECT * FROM ads WHERE campaign_id = ? LIMIT ?", (campaign_id, limit))
        return self.db.fetchall("SELECT * FROM ads LIMIT ?", (limit,))
