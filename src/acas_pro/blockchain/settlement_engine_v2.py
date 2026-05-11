"""ACAS Pro - Settlement Engine v2"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import uuid

from ..core.config_v2 import AppConfig
from ..core.database_v2 import DatabaseManager


class SettlementEngine:
    """Settlement engine - testable with DI"""
    
    def __init__(self, config: Optional[AppConfig] = None, db: Optional[DatabaseManager] = None):
        self.config = config or AppConfig.load()
        self.db = db or DatabaseManager(self.config.database)
        self._init_tables()
    
    def _init_tables(self):
        """Initialize tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS settlements (
                id TEXT PRIMARY KEY,
                amount REAL DEFAULT 0,
                currency TEXT DEFAULT 'USD',
                status TEXT DEFAULT 'pending',
                created_at TEXT,
                completed_at TEXT
            )
        """)
    
    def create_settlement(self, amount: float, currency: str = "USD") -> Tuple[bool, str]:
        """Create settlement"""
        settlement_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        
        self.db.execute("""
            INSERT INTO settlements (id, amount, currency, status, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (settlement_id, amount, currency, 'pending', now))
        
        return True, settlement_id
    
    def complete_settlement(self, settlement_id: str) -> Tuple[bool, str]:
        """Complete settlement"""
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "UPDATE settlements SET status = 'completed', completed_at = ? WHERE id = ?",
            (now, settlement_id)
        )
        return True, "Completed"
    
    def get_settlement(self, settlement_id: str) -> Optional[Dict]:
        """Get settlement"""
        return self.db.fetchone("SELECT * FROM settlements WHERE id = ?", (settlement_id,))
    
    def list_settlements(self, status: str = None, limit: int = 100) -> List[Dict]:
        """List settlements"""
        if status:
            return self.db.fetchall("SELECT * FROM settlements WHERE status = ? LIMIT ?", (status, limit))
        return self.db.fetchall("SELECT * FROM settlements LIMIT ?", (limit,))
