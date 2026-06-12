#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Database Connection Pool
Enterprise-grade connection management with read/write splitting
"""

import os
import threading
import time
from contextlib import contextmanager
from typing import Optional, List, Dict, Any, Generator
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlparse
import logging

# Database drivers
try:
    import psycopg2  # noqa: F401
    from psycopg2 import pool, extras  # noqa: F401
    from psycopg2.extensions import connection as PgConnection  # noqa: F401
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

try:
    import sqlite3
    SQLITE_AVAILABLE = True
except ImportError:
    SQLITE_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('acas.db')


@dataclass
class DBConfig:
    """数据库配置"""
    host: str = 'localhost'
    port: int = 5432
    database: str = 'acas_pro'
    user: str = 'acas_user'
    password: str = ''
    ssl_mode: str = 'prefer'
    
    # Pool settings
    pool_size: int = 10
    max_overflow: int = 20
    pool_timeout: int = 30
    min_connections: int = 5
    max_connections: int = 20
    connection_timeout: int = 30
    idle_timeout: int = 300
    max_lifetime: int = 3600


class ConnectionWrapper:
    """连接包装器 - 增强功能"""
    
    def __init__(self, conn, pool_manager, is_primary: bool = True):
        self._conn = conn
        self._pool = pool_manager
        self._is_primary = is_primary
        self._created_at = datetime.now(timezone.utc)
        self._last_used = datetime.now(timezone.utc)
        self._use_count = 0
        self._is_closed = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
    
    def __getattr__(self, name):
        return getattr(self._conn, name)
    
    def close(self):
        """归还连接到池"""
        if not self._is_closed:
            self._pool._return_connection(self, self._is_primary)
            self._is_closed = True
    
    def is_expired(self) -> bool:
        """检查连接是否过期"""
        age = (datetime.now(timezone.utc) - self._created_at).total_seconds()
        return age > self._pool.config.max_lifetime
    
    def mark_used(self):
        """标记使用"""
        self._last_used = datetime.now(timezone.utc)
        self._use_count += 1


class DatabasePoolManager:
    """
    数据库连接池管理器
    
    Features:
    - 读写分离
    - 连接池管理
    - 健康检查
    - 自动故障转移
    """
    
    def __init__(self, config: DBConfig = None):
        self.config = config or DBConfig()
        
        # Primary (write) pool
        self._primary_pool = None
        self._primary_available = True
        
        # Replica (read) pool
        self._replica_pools: List[Any] = []
        self._current_replica = 0
        
        # Connection tracking
        self._active_connections: Dict[int, ConnectionWrapper] = {}
        self._lock = threading.RLock()
        
        # Stats
        self._stats = {
            'total_connections': 0,
            'active_connections': 0,
            'waiting_requests': 0,
            'failed_connections': 0,
            'queries_executed': 0
        }
        
        # Initialize
        self._initialize_pools()
    
    def _initialize_pools(self):
        """初始化连接池"""
        if not POSTGRES_AVAILABLE:
            logger.warning("psycopg2 not available, using SQLite fallback")
            self._init_sqlite()
            return
        
        # Primary pool
        try:
            self._primary_pool = pool.ThreadedConnectionPool(
                minconn=self.config.min_connections,
                maxconn=self.config.max_connections,
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                sslmode=self.config.ssl_mode,
                connect_timeout=self.config.connection_timeout
            )
            logger.info(f"✓ Primary pool initialized: {self.config.host}")
        except Exception as e:
            logger.error(f"✗ Primary pool failed: {e}")
            self._primary_available = False
            raise
        
        # Replica pools (from environment)
        replica_hosts = os.environ.get('DB_REPLICA_HOSTS', '').split(',')
        for i, host in enumerate(replica_hosts):
            if not host.strip():
                continue
            try:
                replica_pool = pool.ThreadedConnectionPool(
                    minconn=2,
                    maxconn=10,
                    host=host.strip(),
                    port=self.config.port,
                    database=self.config.database,
                    user=self.config.user,
                    password=self.config.password,
                    sslmode=self.config.ssl_mode,
                    connect_timeout=self.config.connection_timeout,
                    options='-c default_transaction_read_only=on'
                )
                self._replica_pools.append(replica_pool)
                logger.info(f"✓ Replica pool {i+1} initialized: {host}")
            except Exception as e:
                logger.warning(f"⚠ Replica pool {i+1} failed: {e}")
    
    def _init_sqlite(self):
        """初始化SQLite (降级)"""
        if not SQLITE_AVAILABLE:
            raise RuntimeError("No database driver available")
        
        os.makedirs('data', exist_ok=True)
        self._sqlite_path = 'data/acas_pro.db'
        logger.info(f"✓ SQLite initialized: {self._sqlite_path}")
    
    def _get_primary_connection(self) -> ConnectionWrapper:
        """获取主库连接 (写操作)"""
        with self._lock:
            if not self._primary_available:
                raise RuntimeError("Primary database unavailable")
            
            # SQLite模式
            if self._primary_pool is None and hasattr(self, '_sqlite_path'):
                conn = sqlite3.connect(self._sqlite_path)
                return ConnectionWrapper(conn, self, is_primary=True)
            
            try:
                conn = self._primary_pool.getconn()
                wrapper = ConnectionWrapper(conn, self, is_primary=True)
                self._active_connections[id(wrapper)] = wrapper
                return wrapper
            except Exception:
                self._stats['failed_connections'] += 1
                raise
    
    def _get_replica_connection(self) -> ConnectionWrapper:
        """获取从库连接 (读操作)"""
        with self._lock:
            if not self._replica_pools:
                # 没有从库，使用主库
                return self._get_primary_connection()
            
            # 轮询选择从库
            attempts = len(self._replica_pools)
            for _ in range(attempts):
                pool_idx = self._current_replica % len(self._replica_pools)
                self._current_replica += 1
                
                try:
                    conn = self._replica_pools[pool_idx].getconn()
                    wrapper = ConnectionWrapper(conn, self, is_primary=False)
                    self._active_connections[id(wrapper)] = wrapper
                    return wrapper
                except Exception:
                    logger.warning(f"Replica {pool_idx} failed, trying next...")
                    continue
            
            # 所有从库失败，使用主库
            logger.warning("All replicas failed, falling back to primary")
            return self._get_primary_connection()
    
    def _return_connection(self, wrapper: ConnectionWrapper, is_primary: bool):
        """归还连接到池"""
        with self._lock:
            conn_id = id(wrapper)
            if conn_id in self._active_connections:
                del self._active_connections[conn_id]
            
            try:
                if is_primary and self._primary_pool:
                    self._primary_pool.putconn(wrapper._conn)
                elif not is_primary and self._replica_pools:
                    # 找到对应的池
                    for pool in self._replica_pools:
                        try:
                            pool.putconn(wrapper._conn)
                            break
                        except Exception:
                            continue
            except Exception as e:
                logger.error(f"Failed to return connection: {e}")
    
    @contextmanager
    def get_connection(self, readonly: bool = False) -> Generator[ConnectionWrapper, None, None]:
        """
        获取数据库连接
        
        Args:
            readonly: 是否为只读操作 (使用从库)
        """
        conn = None
        try:
            if readonly and self._replica_pools:
                conn = self._get_replica_connection()
            else:
                conn = self._get_primary_connection()
            
            conn.mark_used()
            yield conn
            
        except Exception:
            if conn:
                conn.close()
            raise
        finally:
            if conn:
                conn.close()
    
    def execute(self, query: str, params: tuple = None, 
                readonly: bool = False, fetch: bool = False) -> Any:
        """
        执行SQL
        
        Args:
            query: SQL语句
            params: 参数
            readonly: 是否只读
            fetch: 是否获取结果
        """
        with self.get_connection(readonly=readonly) as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                
                if fetch:
                    result = cursor.fetchall()
                else:
                    result = cursor.rowcount
                
                if not readonly:
                    conn.commit()
                
                self._stats['queries_executed'] += 1
                return result
                
            except Exception:
                if not readonly:
                    conn.rollback()
                raise
            finally:
                cursor.close()
    
    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """批量执行"""
        with self.get_connection(readonly=False) as conn:
            cursor = conn.cursor()
            try:
                cursor.executemany(query, params_list)
                conn.commit()
                return cursor.rowcount
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        status = {
            'primary': {'status': 'unknown', 'latency_ms': 0},
            'replicas': [],
            'pool_stats': {
                'active': len(self._active_connections),
                'total_created': self._stats['total_connections']
            }
        }
        
        # Check primary
        try:
            start = time.time()
            with self.get_connection(readonly=False) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                cursor.close()
            status['primary'] = {
                'status': 'healthy',
                'latency_ms': int((time.time() - start) * 1000)
            }
        except Exception as e:
            status['primary'] = {'status': 'unhealthy', 'error': str(e)}
        
        # Check replicas
        for i, pool in enumerate(self._replica_pools):
            try:
                start = time.time()
                conn = pool.getconn()
                cursor = conn.cursor()
                cursor.execute('SELECT 1')
                cursor.close()
                pool.putconn(conn)
                status['replicas'].append({
                    'index': i,
                    'status': 'healthy',
                    'latency_ms': int((time.time() - start) * 1000)
                })
            except Exception as e:
                status['replicas'].append({
                    'index': i,
                    'status': 'unhealthy',
                    'error': str(e)
                })
        
        return status
    
    def close_all(self):
        """关闭所有连接"""
        with self._lock:
            if self._primary_pool:
                self._primary_pool.closeall()
            for pool in self._replica_pools:
                pool.closeall()
            logger.info("All database connections closed")


# 全局实例
_pool_manager: Optional[DatabasePoolManager] = None

def _parse_database_url(url: str) -> dict:
    """解析 DATABASE_URL (postgresql://user:pass@host:port/dbname) 为 DBConfig 参数"""
    parsed = urlparse(url)
    return {
        'host': parsed.hostname or 'localhost',
        'port': parsed.port or 5432,
        'database': parsed.path.lstrip('/') or 'acas_pro',
        'user': parsed.username or 'acas_user',
        'password': parsed.password or '',
    }


def get_db_pool() -> DatabasePoolManager:
    """获取连接池"""
    global _pool_manager
    if _pool_manager is None:
        # 优先使用 DATABASE_URL（与 .env / 12-factor 兼容）
        database_url = os.environ.get('DATABASE_URL', '')
        if database_url and database_url.startswith('postgresql'):
            url_params = _parse_database_url(database_url)
            config = DBConfig(**url_params)
        else:
            config = DBConfig(
                host=os.environ.get('DB_HOST', 'localhost'),
                port=int(os.environ.get('DB_PORT', '5432')),
                database=os.environ.get('DB_NAME', 'acas_pro'),
                user=os.environ.get('DB_USER', 'acas_user'),
                password=os.environ.get('DB_PASSWORD', ''),
                ssl_mode=os.environ.get('DB_SSL_MODE', 'prefer')
            )
        _pool_manager = DatabasePoolManager(config)
    return _pool_manager


if __name__ == '__main__':
    # 测试
    print("="*60)
    print("ACAS Pro - Database Pool Test")
    print("="*60)
    
    # 使用SQLite进行测试
    pool = DatabasePoolManager()
    
    # 创建测试表
    print("\n[1] Creating test table...")
    pool.execute('''
        CREATE TABLE IF NOT EXISTS test_users (
            id INTEGER PRIMARY KEY,
            email TEXT UNIQUE,
            name TEXT
        )
    ''')
    print("    ✓ Table created")
    
    # 插入数据
    print("\n[2] Inserting data...")
    pool.execute(
        "INSERT OR REPLACE INTO test_users (id, email, name) VALUES (?, ?, ?)",
        (1, 'test@acas.pro', 'Test User')
    )
    print("    ✓ Data inserted")
    
    # 查询数据
    print("\n[3] Querying data...")
    result = pool.execute(
        "SELECT * FROM test_users WHERE id = ?",
        (1,),
        readonly=True,
        fetch=True
    )
    print(f"    ✓ Result: {result}")
    
    # 健康检查
    print("\n[4] Health check...")
    health = pool.health_check()
    print(f"    Status: {health}")
    
    pool.close_all()
    
    print("\n" + "="*60)
    print("Database pool test completed")
