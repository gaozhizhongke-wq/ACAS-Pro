"""ACAS Pro - Data Monitor v2"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ..core.config_v2 import AppConfig
from ..core.database_v2 import DatabaseManager


class DataMonitor:
    """Data monitor - testable with DI"""
    
    def __init__(self, config: Optional[AppConfig] = None, db: Optional[DatabaseManager] = None):
        self.config = config or AppConfig.load()
        self.db = db or DatabaseManager(self.config.database)
        self._init_tables()
    
    def _init_tables(self):
        """Initialize tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                value REAL,
                timestamp TEXT
            )
        """)
    
    def record_metric(self, name: str, value: float) -> bool:
        """Record metric"""
        now = datetime.now(timezone.utc).isoformat()
        self.db.execute(
            "INSERT INTO metrics (name, value, timestamp) VALUES (?, ?, ?)",
            (name, value, now)
        )
        return True
    
    def get_metrics(self, name: str, limit: int = 100) -> List[Dict]:
        """Get metrics"""
        return self.db.fetchall(
            "SELECT * FROM metrics WHERE name = ? ORDER BY timestamp DESC LIMIT ?",
            (name, limit)
        )
    
    def get_latest_metric(self, name: str) -> Optional[Dict]:
        """Get latest metric"""
        return self.db.fetchone(
            "SELECT * FROM metrics WHERE name = ? ORDER BY timestamp DESC LIMIT 1",
            (name,)
        )
    
    def get_average(self, name: str, hours: int = 24) -> float:
        """Get average"""
        result = self.db.fetchone(
            "SELECT AVG(value) as avg FROM metrics WHERE name = ? AND timestamp > datetime('now', '-{} hours')".format(hours),
            (name,)
        )
        return result['avg'] if result and result['avg'] else 0.0
