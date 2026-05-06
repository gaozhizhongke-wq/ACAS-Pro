#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Enterprise Database Layer
SQLite with WAL mode for concurrent access
"""

import sqlite3
import threading
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
from contextlib import contextmanager
from dataclasses import asdict

from acas_pro.core.config import config
from acas_pro.core.logging import get_logger

logger = get_logger(__name__)


class DatabaseManager:
    """
    Enterprise database manager
    - Connection pooling
    - WAL mode for concurrent reads/writes
    - Automatic migrations
    - Transaction support
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._db_path = config.database.path
        self._local = threading.local()
        self._initialized = True
        
        # Initialize database
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local connection"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                isolation_level=None  # Autocommit mode for WAL
            )
            self._local.connection.row_factory = sqlite3.Row
            # Enable WAL mode for better concurrency
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA synchronous=NORMAL")
            self._local.connection.execute("PRAGMA cache_size=10000")
        return self._local.connection
    
    @contextmanager
    def transaction(self):
        """Transaction context manager"""
        conn = self._get_connection()
        conn.execute("BEGIN IMMEDIATE")
        try:
            yield conn
            conn.execute("COMMIT")
        except Exception as e:
            conn.execute("ROLLBACK")
            logger.error(f"Transaction failed: {e}")
            raise
    
    def _init_db(self):
        """Initialize database schema"""
        with self.transaction() as conn:
            # Users table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    account_type TEXT NOT NULL,
                    account TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    nickname TEXT,
                    email TEXT,
                    phone TEXT,
                    role TEXT DEFAULT 'user',
                    status TEXT DEFAULT 'active',
                    region TEXT DEFAULT 'global',
                    language TEXT DEFAULT 'zh',
                    timezone TEXT DEFAULT 'Asia/Shanghai',
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    login_count INTEGER DEFAULT 0,
                    failed_login_count INTEGER DEFAULT 0,
                    locked_until TEXT,
                    wallet_balance REAL DEFAULT 0.0,
                    wallet_currency TEXT DEFAULT 'USD',
                    model_preference TEXT DEFAULT 'auto',
                    metadata TEXT
                )
            """)
            
            # Payment methods table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS payment_methods (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    account TEXT,
                    holder TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Transactions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    amount REAL NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    method TEXT,
                    status TEXT DEFAULT 'pending',
                    note TEXT,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Audit log table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    user_id TEXT,
                    ip_address TEXT,
                    details TEXT,
                    severity TEXT DEFAULT 'info'
                )
            """)
            
            # Products table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    category TEXT,
                    price REAL NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    stock_quantity INTEGER DEFAULT 0,
                    reorder_point INTEGER DEFAULT 0,
                    reorder_quantity INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    metadata TEXT
                )
            """)
            
            # Sales data table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sales_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    revenue REAL NOT NULL,
                    region TEXT,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                )
            """)
            
            # News cache table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS news_cache (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    content TEXT,
                    summary TEXT,
                    source TEXT,
                    source_url TEXT,
                    category TEXT,
                    published_at TEXT NOT NULL,
                    language TEXT,
                    sentiment_score REAL,
                    relevance_score REAL,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Sessions table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    token TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_account ON users(account)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_transactions_created ON transactions(created_at)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_product ON sales_data(product_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sales_timestamp ON sales_data(timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_news_category ON news_cache(category)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)")
            
            logger.info("Database initialized successfully")
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """Execute SQL query"""
        conn = self._get_connection()
        return conn.execute(query, params)
    
    def fetchone(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Fetch single row as dict"""
        cursor = self.execute(query, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def fetchall(self, query: str, params: tuple = ()) -> List[Dict]:
        """Fetch all rows as list of dicts"""
        cursor = self.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]
    
    def insert(self, table: str, data: Dict[str, Any]) -> int:
        """Insert single row"""
        columns = ", ".join(data.keys())
        placeholders = ", ".join(["?"] * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"
        
        with self.transaction() as conn:
            cursor = conn.execute(query, tuple(data.values()))
            return cursor.lastrowid
    
    def update(self, table: str, data: Dict[str, Any], where: str, where_params: tuple) -> int:
        """Update rows"""
        set_clause = ", ".join([f"{k} = ?" for k in data.keys()])
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        
        with self.transaction() as conn:
            cursor = conn.execute(query, tuple(data.values()) + where_params)
            return cursor.rowcount
    
    def delete(self, table: str, where: str, params: tuple) -> int:
        """Delete rows"""
        query = f"DELETE FROM {table} WHERE {where}"
        
        with self.transaction() as conn:
            cursor = conn.execute(query, params)
            return cursor.rowcount


# Global instance
db = DatabaseManager()
