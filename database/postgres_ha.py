#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PostgreSQL 高可用模块 - 主从复制 + 读写分离

版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
All Rights Reserved.
"""

import os
import time
import logging
import random
from typing import Optional, List, Dict, Any, Callable
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError

logger = logging.getLogger(__name__)


class NodeRole(Enum):
    """数据库节点角色"""
    MASTER = "master"
    REPLICA = "replica"
    UNKNOWN = "unknown"


@dataclass
class DBNode:
    """数据库节点配置"""
    host: str
    port: int
    database: str
    username: str
    password: str
    role: NodeRole = NodeRole.UNKNOWN
    weight: int = 1  # 负载均衡权重
    is_healthy: bool = True
    last_check: float = 0
    
    @property
    def connection_string(self) -> str:
        return f"postgresql://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"


class PostgresHAManager:
    """PostgreSQL 高可用管理器"""
    
    def __init__(self):
        self.master: Optional[DBNode] = None
        self.replicas: List[DBNode] = []
        self.engines: Dict[str, Any] = {}
        self.session_makers: Dict[str, Any] = {}
        
        self._load_config()
        self._init_engines()
    
    def _load_config(self):
        """加载数据库配置"""
        # 主库配置
        master_host = os.getenv('DB_MASTER_HOST', 'localhost')
        master_port = int(os.getenv('DB_MASTER_PORT', '5432'))
        
        self.master = DBNode(
            host=master_host,
            port=master_port,
            database=os.getenv('DB_NAME', 'acas_pro'),
            username=os.getenv('DB_USER', 'acas'),
            password=os.getenv('DB_PASSWORD', 'changeme'),
            role=NodeRole.MASTER,
            weight=0  # 主库不用于读
        )
        
        # 从库配置（支持多个）
        replica_hosts = os.getenv('DB_REPLICA_HOSTS', '').split(',')
        replica_ports = os.getenv('DB_REPLICA_PORTS', '').split(',')
        
        for i, host in enumerate(replica_hosts):
            if not host.strip():
                continue
            
            port = int(replica_ports[i]) if i < len(replica_ports) and replica_ports[i] else 5432
            
            replica = DBNode(
                host=host.strip(),
                port=port,
                database=self.master.database,
                username=self.master.username,
                password=self.master.password,
                role=NodeRole.REPLICA,
                weight=1
            )
            self.replicas.append(replica)
        
        logger.info(f"数据库配置加载: 1 主库, {len(self.replicas)} 从库")
    
    def _init_engines(self):
        """初始化数据库引擎"""
        # 主库引擎 - 用于写操作
        self.engines['master'] = self._create_engine(self.master)
        self.session_makers['master'] = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engines['master']
        )
        
        # 从库引擎 - 用于读操作
        for i, replica in enumerate(self.replicas):
            engine_key = f"replica_{i}"
            self.engines[engine_key] = self._create_engine(replica)
            self.session_makers[engine_key] = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engines[engine_key]
            )
    
    def _create_engine(self, node: DBNode):
        """创建数据库引擎"""
        engine = create_engine(
            node.connection_string,
            poolclass=QueuePool,
            pool_size=int(os.getenv('DB_POOL_SIZE', '10')),
            max_overflow=int(os.getenv('DB_MAX_OVERFLOW', '20')),
            pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30')),
            pool_recycle=int(os.getenv('DB_POOL_RECYCLE', '3600')),
            pool_pre_ping=True,
            echo=False
        )
        
        # 添加连接事件监听
        @event.listens_for(engine, "connect")
        def on_connect(dbapi_conn, connection_record):
            node.last_check = time.time()
            node.is_healthy = True
        
        @event.listens_for(engine, "checkout")
        def on_checkout(dbapi_conn, connection_record, connection_proxy):
            node.last_check = time.time()
        
        return engine
    
    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        results = {
            "master": {"healthy": False, "latency_ms": 0},
            "replicas": []
        }
        
        # 检查主库
        start = time.time()
        try:
            with self.engines['master'].connect() as conn:
                conn.execute(text("SELECT 1"))
            results["master"]["healthy"] = True
            results["master"]["latency_ms"] = int((time.time() - start) * 1000)
            self.master.is_healthy = True
        except Exception as e:
            logger.error(f"主库健康检查失败: {e}")
            self.master.is_healthy = False
        
        # 检查从库
        for i, replica in enumerate(self.replicas):
            engine_key = f"replica_{i}"
            start = time.time()
            try:
                with self.engines[engine_key].connect() as conn:
                    conn.execute(text("SELECT 1"))
                replica.is_healthy = True
                results["replicas"].append({
                    "host": replica.host,
                    "port": replica.port,
                    "healthy": True,
                    "latency_ms": int((time.time() - start) * 1000)
                })
            except Exception as e:
                logger.error(f"从库 {replica.host}:{replica.port} 健康检查失败: {e}")
                replica.is_healthy = False
                results["replicas"].append({
                    "host": replica.host,
                    "port": replica.port,
                    "healthy": False,
                    "error": str(e)
                })
        
        return results
    
    def get_read_engine(self) -> Any:
        """获取读操作引擎（负载均衡）"""
        healthy_replicas = [r for r in self.replicas if r.is_healthy]
        
        if healthy_replicas:
            # 加权随机选择
            total_weight = sum(r.weight for r in healthy_replicas)
            point = random.uniform(0, total_weight)
            current = 0
            
            for replica in healthy_replicas:
                current += replica.weight
                if point <= current:
                    idx = self.replicas.index(replica)
                    return self.engines[f"replica_{idx}"]
        
        # 没有健康从库，使用主库
        logger.warning("没有健康从库，读操作回退到主库")
        return self.engines['master']
    
    def get_write_engine(self) -> Any:
        """获取写操作引擎（主库）"""
        if not self.master.is_healthy:
            raise OperationalError("主库不可用，无法执行写操作")
        return self.engines['master']
    
    @contextmanager
    def session(self, readonly: bool = False):
        """
        获取数据库会话
        
        Args:
            readonly: 是否为只读操作（使用从库）
        """
        if readonly:
            engine = self.get_read_engine()
            session_key = None
            for k, v in self.engines.items():
                if v == engine:
                    session_key = k
                    break
        else:
            engine = self.get_write_engine()
            session_key = 'master'
        
        session = self.session_makers[session_key]()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
    
    def execute_read(self, sql: str, params: Optional[Dict] = None) -> List[Any]:
        """执行读操作"""
        engine = self.get_read_engine()
        with engine.connect() as conn:
            result = conn.execute(text(sql), params or {})
            return result.fetchall()
    
    def execute_write(self, sql: str, params: Optional[Dict] = None) -> int:
        """执行写操作"""
        engine = self.get_write_engine()
        with engine.connect() as conn:
            with conn.begin():
                result = conn.execute(text(sql), params or {})
                return result.rowcount
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stats = {
            "master": {
                "host": self.master.host,
                "port": self.master.port,
                "healthy": self.master.is_healthy
            },
            "replicas": [
                {
                    "host": r.host,
                    "port": r.port,
                    "healthy": r.is_healthy,
                    "weight": r.weight
                }
                for r in self.replicas
            ],
            "readonly_nodes": len([r for r in self.replicas if r.is_healthy])
        }
        return stats


class DatabaseRouter:
    """数据库路由 - 自动读写分离"""
    
    def __init__(self, ha_manager: PostgresHAManager):
        self.ha = ha_manager
    
    def route_read(self, model_name: str = None) -> str:
        """路由读操作"""
        return "replica"
    
    def route_write(self, model_name: str = None) -> str:
        """路由写操作"""
        return "master"


# 全局实例
_ha_manager = None


def get_ha_manager() -> PostgresHAManager:
    """获取 HA 管理器单例"""
    global _ha_manager
    if _ha_manager is None:
        _ha_manager = PostgresHAManager()
    return _ha_manager


def with_read_session(func: Callable) -> Callable:
    """读操作会话装饰器"""
    def wrapper(*args, **kwargs):
        ha = get_ha_manager()
        with ha.session(readonly=True) as session:
            kwargs['session'] = session
            return func(*args, **kwargs)
    return wrapper


def with_write_session(func: Callable) -> Callable:
    """写操作会话装饰器"""
    def wrapper(*args, **kwargs):
        ha = get_ha_manager()
        with ha.session(readonly=False) as session:
            kwargs['session'] = session
            return func(*args, **kwargs)
    return wrapper


if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="PostgreSQL HA 管理工具")
    parser.add_argument("command", choices=["health", "stats", "test", "failover"])
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    ha = get_ha_manager()
    
    if args.command == "health":
        print(json.dumps(ha.health_check(), indent=2))
    
    elif args.command == "stats":
        print(json.dumps(ha.get_stats(), indent=2))
    
    elif args.command == "test":
        print("测试读写分离...")
        
        # 测试读操作
        try:
            result = ha.execute_read("SELECT version()")
            print(f"✓ 读操作成功: {result[0][0][:50]}...")
        except Exception as e:
            print(f"✗ 读操作失败: {e}")
        
        # 测试写操作
        try:
            # 创建测试表
            ha.execute_write("""
                CREATE TABLE IF NOT EXISTS ha_test (
                    id SERIAL PRIMARY KEY,
                    test_data VARCHAR(100),
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """)
            
            # 插入测试数据
            rows = ha.execute_write(
                "INSERT INTO ha_test (test_data) VALUES (:data)",
                {"data": f"HA Test {time.time()}"}
            )
            print(f"✓ 写操作成功: 插入 {rows} 行")
            
            # 清理
            ha.execute_write("DROP TABLE IF EXISTS ha_test")
            
        except Exception as e:
            print(f"✗ 写操作失败: {e}")
    
    elif args.command == "failover":
        print("模拟故障转移...")
        print("注意: 实际故障转移需要外部工具如 Patroni 或 repmgr")
        print("当前实现仅支持读操作自动切换到健康从库")
