import re

with open('src/acas_pro/core/database.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add aiosqlite import
old_imports = '''import os
import re
import json
import sqlite3
import threading
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable, Union, Sequence
from contextlib import contextmanager
from dataclasses import asdict
from urllib.parse import urlparse

from .logging import get_logger'''

new_imports = '''import os
import re
import json
import sqlite3
import threading
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

from .logging import get_logger'''

content = content.replace(old_imports, new_imports)

# 2. Add async methods at the end of DatabaseManager class (before health_check)
old_health_check = '''    def health_check(self) -> Dict[str, Any]:
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
            return {'status': 'unhealthy', 'error': str(e)}'''

new_health_check = '''    # ── Async methods (SQLite only) ───────────────────────────────────────

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
            return {'status': 'unhealthy', 'error': str(e)}'''

content = content.replace(old_health_check, new_health_check)

with open('src/acas_pro/core/database.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('OK: DatabaseManager async methods added')
