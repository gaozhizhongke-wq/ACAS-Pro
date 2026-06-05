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
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable, Union, Sequence
from contextlib import contextmanager
from dataclasses import asdict
from urllib.parse import urlparse

try:
    import aiosqlite
    _HAS_AIOSQLITE = True
except ImportError:
    _HAS_AIOSQLITE = False

from .logging import get_logger

# Lazy-loaded logger and config
def _get_logger() -> Any:
    return get_logger(__name__)

def _get_config() -> Any:
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
        'last_sync', 'content_count', 'total_views',
        # Added for session management and audit logging
        'sessions', 'audit_log', 'event_type', 'ip_address', 'severity'
    }

    def __new__(cls) -> Any:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> Any:
        # Check the global _db_instance, NOT self._initialized.
        global _db_instance
        if _db_instance is not None and self is _db_instance and self._initialized:
            return
        self._db_url = os.environ.get('DATABASE_URL', '')
        self._is_postgres = 'postgresql' in self._db_url.lower() or 'postgres' in self._db_url.lower()

        if self._is_postgres:
            self._init_postgres()
            self._init_postgres_db()
        else:
            self._init_sqlite()
            self._init_sqlite_db()

        self._initialized = True
        _get_logger().info(f"DatabaseManager initialized ({'PostgreSQL' if self._is_postgres else 'SQLite'})")

    def _init_sqlite(self) -> Any:
        """Initialize SQLite backend"""
        cfg = _get_config()
        self._db_path = cfg.database.path if hasattr(cfg, 'database') else 'data/acas.db'
        self._local = threading.local()
        self._pool = None
        # Ensure directory exists and set secure permissions
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        if sys.platform != 'win32':
            import stat
            os.chmod(Path(self._db_path).parent, stat.S_IRWXU)  # 0o700
        self._init_sqlite_db()

    def _init_postgres(self) -> Any:
        """Initialize PostgreSQL backend with connection pooling"""
        try:
            import psycopg2
            from psycopg2.pool import ThreadedConnectionPool
            from psycopg2.extras import RealDictCursor

            conn_info = urlparse(self._db_url)
            db_name = conn_info.path[1:] if conn_info.path else 'acas'

            self._pool = ThreadedConnectionPool(
                minconn=5,
                maxconn=50,
                host=conn_info.hostname,
                port=conn_info.port or 5432,
                database=db_name,
                user=conn_info.username,
                password=conn_info.password,
                cursor_factory=RealDictCursor,
                # Connection settings for production
                connect_timeout=10,
                options='-c statement_timeout=30000'  # 30s query timeout
            )
            self._local = None  # Not used for PostgreSQL

            # Verify connection works
            conn = self._pool.getconn()
            try:
                cursor = conn.cursor()
                cursor.execute("SELECT version()")
                version = cursor.fetchone()['version']
                _get_logger().info(f"PostgreSQL connected: {version}")
                cursor.close()
            finally:
                self._pool.putconn(conn)

        except ImportError:
            _get_logger().warning("psycopg2 not installed, falling back to SQLite. Run: pip install psycopg2-binary")
            self._is_postgres = False
            self._init_sqlite()
            return
        except Exception as e:
            _get_logger().warning(f"PostgreSQL connection failed, falling back to SQLite: {e}")
            self._is_postgres = False
            self._init_sqlite()
            return

    def _init_sqlite_db(self) -> Any:
        """Initialize SQLite schema"""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        with self._get_sqlite_connection() as conn:
            conn.executescript(self._get_sqlite_schema())

    def _init_postgres_db(self) -> Any:
        """Initialize PostgreSQL schema"""
        if self._is_postgres and self._pool:
            conn = self._pool.getconn()
            try:
                cursor = conn.cursor()
                try:
                    cursor.execute(self._get_postgres_schema())
                    conn.commit()
                    _get_logger().info("PostgreSQL schema initialized")
                except Exception as e:
                    _get_logger().warning(f"PostgreSQL schema init (may already exist): {e}")
                    conn.rollback()
                finally:
                    cursor.close()
            finally:
                self._pool.putconn(conn)

    def _get_sqlite_connection(self) -> Any:
        """Get SQLite connection with auto-cleanup"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            self._local.connection = sqlite3.connect(
                self._db_path,
                check_same_thread=False,
                isolation_level=None
            )
            self._local.connection.row_factory = sqlite3.Row
            self._local.connection.execute("PRAGMA journal_mode=WAL")
            self._local.connection.execute("PRAGMA synchronous=NORMAL")
            # Set file permissions on first creation
            if sys.platform != 'win32':
                import stat
                os.chmod(self._db_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
        return self._local.connection
    
    def close(self) -> None:
        """Close database connections (call on shutdown)"""
        if not self._is_postgres and hasattr(self._local, 'connection') and self._local.connection:
            try:
                self._local.connection.close()
            except Exception:
                pass
            self._local.connection = None
        elif self._is_postgres and self._pool:
            self._pool.closeall()

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
        """PostgreSQL schema definition (SQLite schema with PostgreSQL-specific types)"""
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
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
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
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
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
                created_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS orders (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id),
                product_id TEXT REFERENCES products(id),
                quantity INTEGER NOT NULL,
                total_amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                shipping_address TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS inventory (
                id TEXT PRIMARY KEY,
                product_id TEXT REFERENCES products(id),
                quantity INTEGER DEFAULT 0,
                reserved_quantity INTEGER DEFAULT 0,
                reorder_point INTEGER DEFAULT 10,
                reorder_quantity INTEGER DEFAULT 100,
                warehouse_location TEXT,
                last_updated TIMESTAMP DEFAULT NOW()
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
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW(),
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
                start_date TIMESTAMP,
                end_date TIMESTAMP,
                targeting TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS audience_segments (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id),
                name TEXT NOT NULL,
                segment_type TEXT,
                size INTEGER DEFAULT 0,
                criteria TEXT,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS festival_calendar (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                festival_type TEXT,
                date TEXT NOT NULL,
                region TEXT,
                description TEXT,
                marketing_tips TEXT,
                created_at TIMESTAMP DEFAULT NOW()
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
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            );

            CREATE TABLE IF NOT EXISTS chat_history (
                id TEXT PRIMARY KEY,
                user_id TEXT REFERENCES users(id),
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                model TEXT,
                tokens_used INTEGER,
                created_at TIMESTAMP DEFAULT NOW()
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
                created_at TIMESTAMP DEFAULT NOW()
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
    def transaction(self) -> Any:
        """Transaction context manager"""
        if self._is_postgres:
            conn = self._pool.getconn()
            cursor = conn.cursor()
            try:
                cursor.execute("BEGIN")
                yield cursor
                conn.commit()
            except Exception as e:
                _get_logger().exception(f"Error in transaction: {e}")
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
                _get_logger().exception(f"Error in transaction: {e}")
                conn.execute("ROLLBACK")
                _get_logger().error(f"Transaction failed: {e}")
                raise

    @staticmethod
    def _translate_insert_or_replace(query: str) -> str:
        """Translate SQLite INSERT OR REPLACE to PostgreSQL INSERT ... ON CONFLICT DO UPDATE SET ..."""
        import re
        # Match INSERT OR REPLACE INTO table (cols) VALUES (...)
        # Use balanced-parenthesis parsing for VALUES to handle datetime strings
        m = re.match(
            r'(\s*)INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)\s*\(([^)]+)\)\s*VALUES\s*\(',
            query, re.IGNORECASE | re.DOTALL
        )
        if not m:
            return query  # fallback
        indent, table, cols_str = m.group(1), m.group(2), m.group(3)
        vals_start = m.end()
        # Count parentheses to find the closing ) of VALUES(...)
        depth = 1
        i = vals_start
        while i < len(query) and depth > 0:
            if query[i] == '(':
                depth += 1
            elif query[i] == ')':
                depth -= 1
            i += 1
        vals_str = query[vals_start:i-1]
        cols = [c.strip() for c in cols_str.split(',')]
        pk_col = cols[0]
        update_cols = cols[1:]
        set_clause = ', '.join(f'{c} = EXCLUDED.{c}' for c in update_cols)
        return f'{indent}INSERT INTO {table} ({cols_str}) VALUES ({vals_str}) ON CONFLICT ({pk_col}) DO UPDATE SET {set_clause}'

    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute query and return results. Auto-commits write operations on PostgreSQL."""
        if self._is_postgres:
            # Auto-translate SQLite ? placeholders to PostgreSQL %s
            if '?' in query:
                query = query.replace('?', '%s')
            # SQLite AUTOINCREMENT is invalid in PostgreSQL
            if 'AUTOINCREMENT' in query:
                query = query.replace('AUTOINCREMENT', '')
            # SQLite datetime('now') → PostgreSQL NOW()
            if "datetime('now')" in query:
                query = query.replace("datetime('now')", 'NOW()')
            # SQLite INSERT OR REPLACE → PostgreSQL INSERT ... ON CONFLICT DO UPDATE
            if 'INSERT OR REPLACE' in query.upper():
                import re
                query = self._translate_insert_or_replace(query)
            conn = self._pool.getconn()
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                # Auto-commit for write operations (INSERT/UPDATE/DELETE)
                is_write = query.strip().upper().startswith(('INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP'))
                if is_write:
                    conn.commit()
                if cursor.description:
                    import datetime as _dt
                    rows = []
                    for row in cursor.fetchall():
                        d = dict(row)
                        # Normalize datetime values to ISO strings (SQLite compat)
                        for k, v in d.items():
                            if isinstance(v, _dt.datetime):
                                d[k] = v.isoformat()
                            elif isinstance(v, _dt.date):
                                d[k] = v.isoformat()
                            elif isinstance(v, _dt.time):
                                d[k] = v.isoformat()
                            elif isinstance(v, (bytes, bytearray)):
                                d[k] = v.decode('utf-8', errors='replace')
                        rows.append(d)
                    return rows
                return []
            except Exception:
                conn.rollback()
                raise
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

    # Compatibility aliases - web_app.py and user_service.py call fetchone/fetchall
    def fetchone(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Alias for execute_one()"""
        return self.execute_one(query, params)

    def fetch_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Alias for execute_one() - underscore variant for consistency"""
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

    @staticmethod
    def _build_where_clause(
        conditions: Union[Dict[str, Any], List[tuple], None],
        placeholder: str = '?'
    ) -> tuple:
        """
        Build parameterized WHERE clause from structured conditions.

        Args:
            conditions: One of:
                - Dict[str, Any]: {"column": value} → all AND-ed with =
                - List[tuple]: [("column", "op", value), ...] for flexible operators
                - None: no WHERE clause
            placeholder: '?' for SQLite, '%s' for PostgreSQL

        Returns:
            (where_sql: str, params: tuple)
            If conditions is None, returns ("1=1", ()) for safety.

        Raises:
            ValueError: If condition format is invalid.
        """
        if conditions is None:
            return "1=1", ()

        if isinstance(conditions, dict):
            if not conditions:
                return "1=1", ()
            clauses = []
            params = []
            for col, val in conditions.items():
                # Validate column name
                # (caller should validate, but defense-in-depth)
                if not col.replace('_', '').isalnum():
                    raise ValueError(f"Invalid WHERE column name: {col}")
                clauses.append(f"{col} = {placeholder}")
                params.append(val)
            return " AND ".join(clauses), tuple(params)

        if isinstance(conditions, (list, tuple)):
            if not conditions:
                return "1=1", ()
            clauses = []
            params = []
            for cond in conditions:
                if not isinstance(cond, (list, tuple)) or len(cond) != 3:
                    raise ValueError(
                        f"Invalid condition format: {cond}. "
                        "Expected ('column', 'operator', value)."
                    )
                col, op, val = cond
                if not col.replace('_', '').isalnum():
                    raise ValueError(f"Invalid WHERE column name: {col}")
                # Whitelist allowed operators to prevent injection
                allowed_ops = {'=', '!=', '<', '>', '<=', '>=', 'LIKE', 'IN', 'IS'}
                if op.upper() not in allowed_ops:
                    raise ValueError(
                        f"Invalid WHERE operator: {op}. "
                        f"Allowed: {', '.join(sorted(allowed_ops))}"
                    )
                if op.upper() == 'IS':
                    # IS NULL / IS NOT NULL - no parameter
                    clauses.append(f"{col} IS {val}")
                elif op.upper() == 'IN':
                    # IN requires tuple value
                    if not isinstance(val, (list, tuple)):
                        raise ValueError("IN operator requires list/tuple value")
                    in_placeholders = ', '.join([placeholder] * len(val))
                    clauses.append(f"{col} IN ({in_placeholders})")
                    params.extend(val)
                else:
                    clauses.append(f"{col} {op} {placeholder}")
                    params.append(val)
            return " AND ".join(clauses), tuple(params)

        raise ValueError(
            f"Invalid conditions type: {type(conditions).__name__}. "
            "Expected dict, list, or None."
        )

    def update(self, table: str, data: Dict[str, Any],
                 where: Union[Dict[str, Any], List[tuple], None] = None) -> bool:
        """
        Update records with structured WHERE conditions.

        Args:
            table: Table name (validated against whitelist)
            data: Dict of column -> value to update
            where: Structured conditions (dict or list of tuples).
                   Dict: {"id": user_id} → WHERE id = ?
                   List: [("status", "!=", "deleted")] → WHERE status != ?
                   None: Update all rows (use with extreme caution!)

        Returns:
            True if execution succeeded

        Examples:
            db.update("users", {"name": "Alice"}, {"id": 42})
            db.update("users", {"active": True}, [("status", "!=", "deleted")])
        """
        table = self._validate_identifier(table)
        columns = [self._validate_identifier(c) for c in data.keys()]
        values = list(data.values())

        placeholder = '%s' if self._is_postgres else '?'
        set_clause = ', '.join([f"{c} = {placeholder}" for c in columns])

        where_sql, where_params = self._build_where_clause(where, placeholder)

        query = f"UPDATE {table} SET {set_clause} WHERE {where_sql}"
        self.execute(query, tuple(values) + where_params)
        return True

    def delete(self, table: str, where: Union[Dict[str, Any], List[tuple], None] = None) -> bool:
        """
        Delete records with structured WHERE conditions.

        Args:
            table: Table name (validated against whitelist)
            where: Structured conditions (same format as update()).
                   {"id": value} → WHERE id = ?
                   None: Delete all rows (use with extreme caution!)

        Returns:
            True if execution succeeded

        Examples:
            db.delete("users", {"id": 42})
            db.delete("logs", [("created_at", "<", cutoff_date)])
        """
        table = self._validate_identifier(table)
        placeholder = '%s' if self._is_postgres else '?'

        where_sql, where_params = self._build_where_clause(where, placeholder)

        query = f"DELETE FROM {table} WHERE {where_sql}"
        self.execute(query, where_params)
        return True

    # ── Async methods (SQLite only) ───────────────────────────────────────

    async def execute_async(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute query asynchronously (SQLite only)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        if self._is_postgres:
            # Fallback to sync for PostgreSQL
            return self.execute(query, params)
        
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            async with conn.execute(query, params or ()) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    async def execute_one_async(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Execute query and return first row asynchronously (SQLite only)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        if self._is_postgres:
            return self.execute_one(query, params)
        
        async with aiosqlite.connect(self._db_path) as conn:
            conn.row_factory = sqlite3.Row
            async with conn.execute(query, params or ()) as cursor:
                row = await cursor.fetchone()
                return dict(row) if row else None

    async def insert_async(self, table: str, data: Dict[str, Any]) -> str:
        """Insert record asynchronously (SQLite only)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        if self._is_postgres:
            return self.insert(table, data)
        
        table = self._validate_identifier(table)
        columns = [self._validate_identifier(c) for c in data.keys()]
        values = list(data.values())
        placeholders = ', '.join(['?'] * len(columns))
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        
        async with aiosqlite.connect(self._db_path) as conn:
            async with conn.execute(query, values) as cursor:
                await conn.commit()
                return str(cursor.lastrowid)

    async def update_async(self, table: str, data: Dict[str, Any],
                          where: Union[Dict[str, Any], List[tuple], None] = None) -> bool:
        """Update records asynchronously (SQLite only)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        if self._is_postgres:
            return self.update(table, data, where)
        
        table = self._validate_identifier(table)
        columns = [self._validate_identifier(c) for c in data.keys()]
        values = list(data.values())
        set_clause = ', '.join([f"{c} = ?" for c in columns])
        where_sql, where_params = self._build_where_clause(where, '?')
        query = f"UPDATE {table} SET {set_clause} WHERE {where_sql}"
        
        async with aiosqlite.connect(self._db_path) as conn:
            await conn.execute(query, tuple(values) + where_params)
            await conn.commit()
            return True

    async def delete_async(self, table: str,
                          where: Union[Dict[str, Any], List[tuple], None] = None) -> bool:
        """Delete records asynchronously (SQLite only)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        if self._is_postgres:
            return self.delete(table, where)
        
        table = self._validate_identifier(table)
        where_sql, where_params = self._build_where_clause(where, '?')
        query = f"DELETE FROM {table} WHERE {where_sql}"
        
        async with aiosqlite.connect(self._db_path) as conn:
            await conn.execute(query, where_params)
            await conn.commit()
            return True

    async def fetchall_async(self, query: str, params: tuple = None) -> List[Dict]:
        """Alias for execute_async"""
        return await self.execute_async(query, params)

    async def fetchone_async(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Alias for execute_one_async"""
        return await self.execute_one_async(query, params)

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
    """Get database manager singleton (lazy-loaded, DI-aware)"""
    global _db_instance
    if _db_instance is None:
        # Try DI container first
        from .di_container import get_container
        container = get_container()
        if container.is_registered(DatabaseManager):
            _db_instance = container.resolve(DatabaseManager)
        else:
            _db_instance = DatabaseManager()
    return _db_instance


def reset_db() -> Any:
    """Reset the global database singleton (for testing)"""
    global _db_instance
    old = _db_instance
    _db_instance = None
    # Dispose old pool to release connections
    if old is not None:
        try:
            old._pool.dispose()
        except Exception:
            pass


# Backward compatibility - deprecated, use get_db()
db = get_db()
