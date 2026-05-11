"""ACAS Pro - Publish Manager v2"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import uuid

from ..core.config_v2 import AppConfig
from ..core.database_v2 import DatabaseManager


class PublishManager:
    """Publish manager - testable with DI"""
    
    def __init__(self, config: Optional[AppConfig] = None, db: Optional[DatabaseManager] = None):
        self.config = config or AppConfig.load()
        self.db = db or DatabaseManager(self.config.database)
        self._init_tables()
    
    def _init_tables(self):
        """Initialize tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS publications (
                id TEXT PRIMARY KEY,
                title TEXT,
                content TEXT,
                platform TEXT,
                status TEXT DEFAULT 'draft',
                scheduled_at TEXT,
                published_at TEXT,
                created_at TEXT
            )
        """)
    
    def create_publication(self, title: str, content: str, platform: str = "") -> Tuple[bool, str]:
        """Create publication"""
        pub_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        self.db.execute("""
            INSERT INTO publications (id, title, content, platform, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (pub_id, title, content, platform, 'draft', now))
        
        return True, pub_id
    
    def schedule_publication(self, pub_id: str, scheduled_at: str) -> Tuple[bool, str]:
        """Schedule publication"""
        self.db.execute(
            "UPDATE publications SET scheduled_at = ?, status = 'scheduled' WHERE id = ?",
            (scheduled_at, pub_id)
        )
        return True, "Scheduled"
    
    def publish(self, pub_id: str) -> Tuple[bool, str]:
        """Publish"""
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "UPDATE publications SET status = 'published', published_at = ? WHERE id = ?",
            (now, pub_id)
        )
        return True, "Published"
    
    def get_publication(self, pub_id: str) -> Optional[Dict]:
        """Get publication"""
        return self.db.fetchone("SELECT * FROM publications WHERE id = ?", (pub_id,))
    
    def list_publications(self, status: str = None, limit: int = 100) -> List[Dict]:
        """List publications"""
        if status:
            return self.db.fetchall("SELECT * FROM publications WHERE status = ? LIMIT ?", (status, limit))
        return self.db.fetchall("SELECT * FROM publications LIMIT ?", (limit,))
