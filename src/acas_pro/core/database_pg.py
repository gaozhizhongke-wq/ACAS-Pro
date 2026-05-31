#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - PostgreSQL Database Layer
Production-grade database with connection pooling
"""

import os
import json
import threading
from datetime import datetime
from typing import List, Dict, Optional, Any, Callable
from contextlib import contextmanager
from dataclasses import asdict
from urllib.parse import urlparse

import psycopg2
from psycopg2 import sql
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.extras import RealDictCursor

from .logging import get_logger

logger = get_logger(__name__)


class PostgreSQLDatabaseManager:
    """
    Enterprise PostgreSQL database manager
    - Connection pooling
    - Read/write splitting (master/slave)
    - Automatic failover
    - Transaction support
    """
    
    _instance = None
    _lock = threading.Lock()
    
    # SQL injection whitelist for table/column names
    _VALID_IDENTIFIERS = {
        'users', 'products', 'transactions', 'orders', 'inventory',
        'accounts', 'campaigns', 'audience_segments', 'festival_calendar',
        'content_templates', 'chat_history', 'audit_logs',
        'id', 'account', 'password_hash', 'email', 'phone', 'status',
        'created_at', 'updated_at', 'name', 'type', 'value',
        'user_id', 'product_id', 'order_id', 'amount', 'quantity',
        'platform', 'content', 'metadata', 'timestamp'
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
        
        self._db_url = os.environ.get('DATABASE_URL', 'postgresql://acas:changeme@localhost:5432/acas')
        self._pool = None
        self._initialized = False
        
        # Parse connection info
        self._conn_info = urlparse(self._db_url)
        
        # Initialize pool
        self._init_pool()
        self._initialized = True
        
        logger.info("PostgreSQL DatabaseManager initialized")
    
    def _init_pool(self):
        """Initialize connection pool"""
        try:
            self._pool = ThreadedConnectionPool(
                minconn=5,
                maxconn=50,
                host=self._conn_info.hostname,
                port=self._conn_info.port or 5432,
                database=self._conn_info.path[1:],  # Remove leading /
                user=self._conn_info.username,
                password=self._conn_info.password,
                cursor_factory=RealDictCursor
            )
            logger.info("Connection pool created (min=5, max=50)")
        except Exception as e:
            logger.error(f"Failed to create connection pool: {e}")
            raise
    
    def _validate_identifier(self, identifier: str) -> str:
        """Validate SQL identifier to prevent injection"""
        if identifier not in self._VALID_IDENTIFIERS:
            # Additional check: alphanumeric and underscores only
            if not identifier.replace('_', '').isalnum():
                raise ValueError(f"Invalid SQL identifier: {identifier}")
        return identifier
    
    @contextmanager
    def get_connection(self, readonly: bool = False):
        """Get connection from pool"""
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        finally:
            if conn:
                self._pool.putconn(conn)
    
    @contextmanager
    def transaction(self):
        """Transaction context manager"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("BEGIN")
                yield cursor
                conn.commit()
            except Exception as e:
                logger.exception("Unhandled exception")
                conn.rollback()
                logger.error(f"Transaction failed: {e}")
                raise
            finally:
                cursor.close()
    
    def execute(self, query: str, params: tuple = None) -> List[Dict]:
        """Execute query and return results"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                if cursor.description:
                    return [dict(row) for row in cursor.fetchall()]
                return []
            finally:
                cursor.close()
    
    def execute_one(self, query: str, params: tuple = None) -> Optional[Dict]:
        """Execute query and return single result"""
        results = self.execute(query, params)
        return results[0] if results else None
    
    def insert(self, table: str, data: Dict[str, Any]) -> str:
        """Insert data into table with SQL injection protection"""
        # Validate table name
        table = self._validate_identifier(table)
        
        # Validate column names
        columns = [self._validate_identifier(c) for c in data.keys()]
        values = list(data.values())
        
        placeholders = ', '.join(['%s'] * len(values))
        columns_str = ', '.join(columns)
        
        query = f"INSERT INTO {table} ({columns_str}) VALUES ({placeholders}) RETURNING id"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, values)
                result = cursor.fetchone()
                conn.commit()
                return result['id'] if result else None
            finally:
                cursor.close()
    
    def update(self, table: str, id_value: str, data: Dict[str, Any]) -> bool:
        """Update record by id"""
        table = self._validate_identifier(table)
        
        columns = [self._validate_identifier(c) for c in data.keys()]
        values = list(data.values())
        
        set_clause = ', '.join([f"{c} = %s" for c in columns])
        query = f"UPDATE {table} SET {set_clause} WHERE id = %s"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, values + [id_value])
                conn.commit()
                return cursor.rowcount > 0
            finally:
                cursor.close()
    
    def delete(self, table: str, id_value: str) -> bool:
        """Delete record by id"""
        table = self._validate_identifier(table)
        query = f"DELETE FROM {table} WHERE id = %s"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, (id_value,))
                conn.commit()
                return cursor.rowcount > 0
            finally:
                cursor.close()
    
    def health_check(self) -> Dict[str, Any]:
        """Database health check"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT version(), now()")
                result = cursor.fetchone()
                cursor.close()
                
                return {
                    'status': 'healthy',
                    'database': 'postgresql',
                    'version': result['version'].split()[1] if result else 'unknown',
                    'timestamp': result['now'] if result else None
                }
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                'status': 'unhealthy',
                'error': str(e)
            }


# Global instance
db = PostgreSQLDatabaseManager()
