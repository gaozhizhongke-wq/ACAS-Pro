#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Unified Database Layer
Supports both SQLite (development) and PostgreSQL (production)
"""

import os
import re
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable
from contextlib import contextmanager
from dataclasses import asdict
from urllib.parse import urlparse

from .logging import get_logger

# Lazy-loaded logger and config
def _get_logger():
    return get_logger(__name__)

def _get_config():
    from .config import get_config
    return get_config()


class DatabaseManager:
    """
    Unified database manager supporting SQLite and PostgreSQL
    Auto-detects database type from DATABASE_URL environment variable
    """
    
    _instance = None
    _lock = threading.Lock()
    
    # SQL injection whitelist for identifiers
    _VALID_IDENTIFIERS = {
        'users', 'products', 'transactions', 'orders', 'inventory',
        'accounts', 'campaigns', 'audience_segments', 'festival_calendar',
        'content_templates', 'chat_history', 'audit_logs', 'api_keys',
        'id', 'account', 'password_hash', 'email', 'phone', 'status',
        'created_at', 'updated_at', 'name', 'type', 'value',
        'user_id', 'product_id', 'order_id', 'amount', 'quantity',
        'platform', 'content', 'metadata', 'timestamp', 'api_key',
        'key_hash', 'permissions', 'expires_at', 'last_used_at',
        # Missing identifiers used by web_app.py queries
        'stock_quantity', 'reorder_point', 'reorder_quantity',
        'total_amount', 'revenue', 'deficit', 'low_stock',
        'followers', 'engagement_rate', 'account_name', 'account_id',
        'importance', 'month', 'day', 'duration_days', 'themes',
        'keywords', 'is_active', 'festival_type',
        # Missing identifiers used in actual database
        'currency', 'metadata', 'last_login', 'login_count',
        'failed_login_count', 'locked_until', 'password_hash', 'wallet_balance',
        'wallet_currency', 'model_preference', 'account_type',
        'reserved_quantity', 'warehouse_location', 'last_updated',
        'campaign_id', 'segment_type', 'criteria', 'size',
        'template_content', 'variables', 'usage_count',
        'session_id', 'tokens_used', 'action', 'resource_type',
        'description', 'region', 'category', 'tags', 'price', 'cost',
        'currency', 'shipping_address', 'start_date', 'end_date',
        'targeting', 'budget', 'spent', 'avatar_url', 'balance',
        'last_sync', 'content_count', 'total_views'
    }
    
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
        
        self._db_url = os.environ.get('DATABASE_URL', '')
        self._is_postgres = 'postgresql' in self._db_url.lower() or 'postgres' in self._db_url.lower()
        
        if self._is_postgres:
            self._init_postgres()
        else:
            self._init_sqlite()
        
        self._initialized = True
        _get_logger().info(f"DatabaseManager initialized ({'PostgreSQL' if self._is_postgres else 'SQLite'})")
    
    def _init_sqlite(self):
        """Initialize SQLite backend"""
        cfg = _get_config()
        self._db_path = cfg.database.path if hasattr(cfg, 'database') else 'data/acas.db'
        self._local = threading.local()
        self._pool = None
        self._init_sqlite_db()
    
    def _init_postgres(self):
        """Initialize PostgreSQL backend"""
        try:
            import psycopg2
            from psycopg2.pool import ThreadedConnectionPool
            from psycopg2.extras import RealDictCursor
            
            conn_info = urlparse(self._db_url)
            self._pool = ThreadedConnectionPool(
                minconn=5,
                maxconn=50,
                host=conn_info.hostname,
                port=conn_info.port or 5432,
                database=conn_info.path[1:],
                user=conn_info.username,
                password=conn_info.password,
                cursor_factory=RealDictCursor
            )
            self._local = None  # Not used for PostgreSQL
        except ImportError:
            logger.error("psycopg2 not installed. Run: pip install psycopg2-binary")
            raise
    
    def _init_sqlite_db(self):
        """Initialize SQLite schema"""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._get_sqlite_connection() as conn:
            conn.executescript(self._get_sqlite_schema())
    
    def _get_sqlite_connection(self):
        """Get SQLite connection"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                isolation_level=None
            )
            self._local.connection.row_factory = sqlite3.Row
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA synchronous=NORMAL")
        return self._local.connection
    
    def _get_sqlite_schema(self) -> str:
        """SQLite schema definition"""
        return '''
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
                created_at TEXT NOT NULL
            );
            
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id),
                name TEXT NOT NULL,
                description TEXT,
                price REAL,
                cost REAL,
                currency TEXT DEFAULT 'CNY',
                stock_quantity INTEGER DEFAULT 0,
                category TEXT,
                tags TEXT,
                reorder_point INTEGER DEFAULT 10,
                reorder_quantity INTEGER DEFAULT 100,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                updated_at TEXT,
                metadata TEXT
            );
            
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id),
                product_id TEXT REFERENCES products(id),
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT DEFAULT 'CNY',
                status TEXT DEFAULT 'pending',
                platform TEXT,
                metadata TEXT,
                created_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id),
                product_id TEXT REFERENCES products(id),
                quantity INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                shipping_address TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS inventory (
                id TEXT PRIMARY KEY,
                product_id TEXT REFERENCES products(id),
                quantity INTEGER DEFAULT 0,
                reserved_quantity INTEGER DEFAULT 0,
                reorder_point INTEGER DEFAULT 10,
                reorder_quantity INTEGER DEFAULT 100,
                warehouse_location TEXT,
                last_updated TEXT
            );
            
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id),
                platform TEXT NOT NULL,
                account_id TEXT NOT NULL,
                account_name TEXT,
                followers INTEGER DEFAULT 0,
                engagement_rate REAL DEFAULT 0,
                status TEXT DEFAULT 'active',
                credentials TEXT,
                created_at TEXT,
                updated_at TEXT,
                UNIQUE(user_id, platform, account_id)
            );
            
            CREATE TABLE IF NOT EXISTS campaigns (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id),
                name TEXT NOT NULL,
                platform TEXT,
                budget REAL,
                spent REAL DEFAULT 0,
                status TEXT DEFAULT 'draft',
                start_date TEXT,
                end_date TEXT,
                targeting TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS audience_segments (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id),
                name TEXT NOT NULL,
                segment_type TEXT,
                size INTEGER DEFAULT 0,
                criteria TEXT,
                created_at TEXT,
                updated_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS festival_calendar (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                festival_type TEXT,
                date TEXT NOT NULL,
                region TEXT,
                description TEXT,
                marketing_tips TEXT,
                created_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS content_templates (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id),
                name TEXT NOT NULL,
                content_type TEXT,
                platform TEXT,
                template_content TEXT NOT NULL,
                variables TEXT,
                usage_count INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS chat_history (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id),
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model TEXT,
                tokens_used INTEGER,
                created_at TEXT
            );
            
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id),
                action TEXT NOT NULL,
                resource_type TEXT,
                resource_id TEXT,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TEXT
            );
            
            CREATE INDEX IF NOT EXISTS idx_users_account ON users(account);
            CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
            CREATE INDEX IF NOT EXISTS idx_chat_history_session ON chat_history(session_id);
        '''
    
    def _validate_identifier(self, identifier: str) -> str:
        """Validate SQL identifier to prevent injection"""
        if identifier not in self._VALID_IDENTIFIERS:
            if not identifier.replace('_', '').isalnum():
                raise ValueError(f"Invalid SQL identifier: {identifier}")
        return identifier
    
    @contextmanager
    def transaction(self):
        """Transaction context manager"""
        if self._is_postgres:
            conn = self._pool.getconn()
            cursor = conn.cursor()
            try:
                cursor.execute("BEGIN")
                yield cursor
                conn.commit()
            except Exception as e:
                import logging; logging.getLogger(__name__).error("Unhandled exception: " + str(e))
                conn.rollback()
                _get_logger().error(f"Transaction failed: {e}")
                raise
            finally:
                cursor.close()
                self._pool.putconn(conn)
        else:
            conn = self._get_sqlite_connection()
            conn.execute("BEGIN IMMEDIATE")
            try:
                yield conn
                conn.execute("COMMIT")
            except Exception as e:
                import logging; logging.getLogger(__name__).error("Unhandled exception: " + str(e))
                conn.execute("ROLLBACK")
                _get_logger().error(f"Transaction failed: {e}")
                raise
    
    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute query and return results"""
        if self._is_postgres:
            conn = self._pool.getconn()
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                if cursor.description:
                    return [dict(row) for row in cursor.fetchall()]
                return []
            finally:
                cursor.close()
                self._pool.putconn(conn)
        else:
            conn = self._get_sqlite_connection()
            cursor = conn.execute(query, params or ())
            if cursor.description:
                return [dict(row) for row in cursor.fetchall()]
            return []
    
    def execute_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Execute query and return single result"""
        results = self.execute(query, params)
        return results[0] if results else None

    # Compatibility aliases �?web_app.py and user_service.py call fetchone/fetchall
    def fetchone(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Alias for execute_one()"""
        return self.execute_one(query, params)

    def fetchall(self, query: str, params: tuple = None) -> List[Dict]:
        """Alias for execute()"""
        return self.execute(query, params)

    def insert(self, table: str, data: Dict[str, Any]) -> str:
        """Insert data with SQL injection protection"""
        table = self._validate_identifier(table)
        columns = [self._validate_identifier(c) for c in data.keys()]
        values = list(data.values())
        
        if self._is_postgres:
            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(['%s'] * len(values))}) RETURNING id"
            result = self.execute_one(query, tuple(values))
            return result['id'] if result else None
        else:
            placeholders = ', '.join(['?'] * len(values))
            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
            conn = self._get_sqlite_connection()
            cursor = conn.execute(query, values)
            return str(cursor.lastrowid)
    
    def update(self, table: str, data: Dict[str, Any],
                 where_clause: str = None, where_params: tuple = None) -> bool:
        """
        Update record with flexible WHERE clause.
        
        Args:
            table: Table name (validated against whitelist)
            data: Dict of column -> value to update
            where_clause: SQL WHERE clause (e.g. "id = ?")
            where_params: Tuple of parameters for WHERE clause
            
        Returns:
            True if execution succeeded
        """
        table = self._validate_identifier(table)
        columns = [self._validate_identifier(c) for c in data.keys()]
        values = list(data.values())
        
        set_clause = ', '.join([f"{c} = ?" if not self._is_postgres else f"{c} = %s" for c in columns])
        
        if where_clause and where_params:
            # New flexible form: db.update("users", data, "id = ?", (uid,))
            if self._is_postgres:
                placeholders = ['%s'] * len(columns)
            else:
                placeholders = ['?'] * len(columns)
            query = f"UPDATE {table} SET {', '.join([f'{c} = {p}' for c, p in zip(columns, placeholders)])} WHERE {where_clause}"
        else:
            # Fallback: UPDATE ... WHERE id = ? (legacy single-id form)
            # This path is no longer used by callers �?kept for potential migrations
            raise ValueError(
                "db.update() requires explicit where_clause and where_params. "
                "Use: db.update('table', data, 'id = ?', (id_value,))"
            )
        
        self.execute(query, tuple(values) + (where_params or ()))
        return True
    
    def delete(self, table: str, id_value: str = None, where_clause: str = None, where_params: tuple = None) -> bool:
        """Delete record by id or custom WHERE clause"""
        table = self._validate_identifier(table)
        placeholder = '%s' if self._is_postgres else '?'
        if where_clause and where_params:
            query = f"DELETE FROM {table} WHERE {where_clause}"
            self.execute(query, where_params)
        elif id_value is not None:
            query = f"DELETE FROM {table} WHERE id = {placeholder}"
            self.execute(query, (id_value,))
        else:
            raise ValueError("delete() requires either id_value or where_clause+where_params")
        return True
    
    def health_check(self) -> Dict[str, Any]:
        """Database health check"""
        try:
            if self._is_postgres:
                result = self.execute_one("SELECT version(), now()")
                return {
                    'status': 'healthy',
                    'database': 'postgresql',
                    'version': result['version'].split()[1] if result else 'unknown'
                }
            else:
                self.execute("SELECT 1")
                return {
                    'status': 'healthy',
                    'database': 'sqlite',
                    'path': str(self._db_path)
                }
        except Exception as e:
            _get_logger().error(f"Health check failed: {e}")
            return {'status': 'unhealthy', 'error': str(e)}


# Lazy-loaded global instance
_db_instance: Optional['DatabaseManager'] = None


def get_db() -> 'DatabaseManager':
    """Get database manager singleton (lazy-loaded)"""
    global _db_instance
    if _db_instance is None:
        _db_instance = DatabaseManager()
    return _db_instance


# Backward compatibility - deprecated, use get_db()
db = get_db()
