"""
ACAS Pro - Database v2
Testable database layer with dependency injection
"""

import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
from contextlib import contextmanager
from dataclasses import asdict

from .config_v2 import AppConfig, DatabaseConfig


class DatabaseManager:
    """Database manager - testable with DI"""
    
    def __init__(self, config: Optional[DatabaseConfig] = None):
        self.config = config or DatabaseConfig()
        self._local = threading.local()
        self._lock = threading.Lock()
        self._init_db()
    
    def _init_db(self):
        """Initialize database"""
        if self.config.type == 'sqlite':
            Path(self.config.path).parent.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self):
        """Get thread-local connection"""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            if self.config.type == 'sqlite':
                self._local.conn = sqlite3.connect(self.config.path, check_same_thread=False)
                self._local.conn.row_factory = sqlite3.Row
            else:
                # PostgreSQL would be handled here
                raise NotImplementedError("PostgreSQL not yet implemented in v2")
        return self._local.conn
    
    def execute(self, sql: str, parameters: tuple = None) -> None:
        """Execute SQL"""
        conn = self._get_connection()
        cursor = conn.cursor()
        if parameters:
            cursor.execute(sql, parameters)
        else:
            cursor.execute(sql)
        conn.commit()
        return cursor
    
    def fetchone(self, sql: str, parameters: tuple = None) -> Optional[Dict]:
        """Fetch one row"""
        conn = self._get_connection()
        cursor = conn.cursor()
        if parameters:
            cursor.execute(sql, parameters)
        else:
            cursor.execute(sql)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def fetchall(self, sql: str, parameters: tuple = None) -> List[Dict]:
        """Fetch all rows"""
        conn = self._get_connection()
        cursor = conn.cursor()
        if parameters:
            cursor.execute(sql, parameters)
        else:
            cursor.execute(sql)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    
    def close(self):
        """Close connection"""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
    
    def health_check(self) -> Dict[str, Any]:
        """Health check"""
        try:
            self.execute("SELECT 1")
            return {'status': 'healthy', 'database': self.config.type}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}


# Factory function
def create_database_manager(config: Optional[AppConfig] = None) -> DatabaseManager:
    """Create database manager"""
    cfg = config or AppConfig.load()
    return DatabaseManager(cfg.database)
