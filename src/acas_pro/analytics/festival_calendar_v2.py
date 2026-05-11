"""ACAS Pro - Festival Calendar v2"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ..core.config_v2 import AppConfig
from ..core.database_v2 import DatabaseManager


class FestivalCalendar:
    """Festival calendar - testable with DI"""
    
    def __init__(self, config: Optional[AppConfig] = None, db: Optional[DatabaseManager] = None):
        self.config = config or AppConfig.load()
        self.db = db or DatabaseManager(self.config.database)
        self._init_tables()
    
    def _init_tables(self):
        """Initialize tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS festivals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                date TEXT,
                category TEXT,
                description TEXT
            )
        """)
    
    def add_festival(self, name: str, date: str, category: str = "", description: str = "") -> bool:
        """Add festival"""
        self.db.execute(
            "INSERT INTO festivals (name, date, category, description) VALUES (?, ?, ?, ?)",
            (name, date, category, description)
        )
        return True
    
    def get_festivals(self, month: int = None) -> List[Dict]:
        """Get festivals"""
        if month:
            return self.db.fetchall("SELECT * FROM festivals WHERE strftime('%m', date) = ?", (f"{month:02d}",))
        return self.db.fetchall("SELECT * FROM festivals")
    
    def get_upcoming(self, days: int = 30) -> List[Dict]:
        """Get upcoming festivals"""
        return self.db.fetchall(
            "SELECT * FROM festivals WHERE date >= date('now') AND date <= date('now', '+{} days')".format(days)
        )
