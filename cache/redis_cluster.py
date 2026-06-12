#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Redis 集群管理模块

版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
All Rights Reserved.
"""

import os
import json
import logging
import hashlib
from typing import Optional, Any, List, Dict, Callable
from functools import wraps
from datetime import datetime, timedelta

from redis.cluster import RedisCluster
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class CacheStrategy:
    """缓存策略枚举"""
    LRU = "lru"           # 最近最少使用
    LFU = "lfu"           # 最不经常使用
    TTL = "ttl"           # 过期时间
    WRITE_THROUGH = "write_through"   # 直写
    WRITE_BACK = "write_back"         # 回写


class RedisClusterManager:
    """Redis 集群管理器"""
    
    def __init__(self, startup_nodes: Optional[List[Dict]] = None):
        """
        初始化 Redis 集群连接
        
        Args:
            startup_nodes: 集群节点列表，如 [{"host": "localhost", "port": 7000}]
        """
        self.startup_nodes = startup_nodes or self._get_default_nodes()
        self.client = None
        self._connect()
    
    def _get_default_nodes(self) -> List[Dict]:
        """获取默认集群节点配置"""
        # 从环境变量读取，或使用默认配置
        redis_url = os.getenv('REDIS_URL', '')
        
        if redis_url:
            # 解析 redis://host:port 格式
            parts = redis_url.replace('redis://', '').split(':')
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 6379
            return [{"host": host, "port": port}]
        
        # 默认 6 节点集群配置
        return [
            {"host": "localhost", "port": 7000},
            {"host": "localhost", "port": 7001},
            {"host": "localhost", "port": 7002},
            {"host": "localhost", "port": 7003},
            {"host": "localhost", "port": 7004},
            {"host": "localhost", "port": 7005},
        ]
    
    def _connect(self):
        """建立集群连接"""
        try:
            self.client = RedisCluster(
                startup_nodes=self.startup_nodes,
                decode_responses=True,
                skip_full_coverage_check=True,
                max_connections_per_node=20,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            logger.info(f"Redis 集群连接成功: {len(self.startup_nodes)} 个节点")
        except Exception as e:
            logger.error(f"Redis 集群连接失败: {e}")
            self.client = None
    
    def is_connected(self) -> bool:
        """检查连接状态"""
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except Exception:
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if not self.client:
            return None
        try:
            value = self.client.get(key)
            if value:
                try:
                    return json.loads(value)
                except Exception:
                    return value
            return None
        except RedisError as e:
            logger.error(f"Redis GET 失败 [{key}]: {e}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False
    ) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            nx: 仅当 key 不存在时才设置
        """
        if not self.client:
            return False
        
        try:
            # JSON 序列化
            if not isinstance(value, (str, bytes)):
                value = json.dumps(value, default=str)
            
            return self.client.set(key, value, ex=ttl, nx=nx)
        except RedisError as e:
            logger.error(f"Redis SET 失败 [{key}]: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.client:
            return False
        try:
            return bool(self.client.delete(key))
        except RedisError as e:
            logger.error(f"Redis DELETE 失败 [{key}]: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """检查 key 是否存在"""
        if not self.client:
            return False
        try:
            return bool(self.client.exists(key))
        except RedisError:
            return False
    
    def expire(self, key: str, seconds: int) -> bool:
        """设置过期时间"""
        if not self.client:
            return False
        try:
            return bool(self.client.expire(key, seconds))
        except RedisError:
            return False
    
    def ttl(self, key: str) -> int:
        """获取剩余过期时间"""
        if not self.client:
            return -2
        try:
            return self.client.ttl(key)
        except RedisError:
            return -2
    
    def incr(self, key: str, amount: int = 1) -> Optional[int]:
        """原子递增"""
        if not self.client:
            return None
        try:
            return self.client.incr(key, amount)
        except RedisError as e:
            logger.error(f"Redis INCR 失败 [{key}]: {e}")
            return None
    
    def decr(self, key: str, amount: int = 1) -> Optional[int]:
        """原子递减"""
        if not self.client:
            return None
        try:
            return self.client.decr(key, amount)
        except RedisError as e:
            logger.error(f"Redis DECR 失败 [{key}]: {e}")
            return None
    
    def hset(self, key: str, field: str, value: Any) -> bool:
        """哈希表设置"""
        if not self.client:
            return False
        try:
            if not isinstance(value, (str, bytes)):
                value = json.dumps(value, default=str)
            return bool(self.client.hset(key, field, value))
        except RedisError as e:
            logger.error(f"Redis HSET 失败 [{key}:{field}]: {e}")
            return False
    
    def hget(self, key: str, field: str) -> Optional[Any]:
        """哈希表获取"""
        if not self.client:
            return None
        try:
            value = self.client.hget(key, field)
            if value:
                try:
                    return json.loads(value)
                except Exception:
                    return value
            return None
        except RedisError as e:
            logger.error(f"Redis HGET 失败 [{key}:{field}]: {e}")
            return None
    
    def hgetall(self, key: str) -> Dict[str, Any]:
        """获取整个哈希表"""
        if not self.client:
            return {}
        try:
            data = self.client.hgetall(key)
            result = {}
            for k, v in data.items():
                try:
                    result[k] = json.loads(v)
                except Exception:
                    result[k] = v
            return result
        except RedisError as e:
            logger.error(f"Redis HGETALL 失败 [{key}]: {e}")
            return {}
    
    def lpush(self, key: str, *values) -> int:
        """列表左侧插入"""
        if not self.client:
            return 0
        try:
            serialized = [json.dumps(v, default=str) if not isinstance(v, (str, bytes)) else v for v in values]
            return self.client.lpush(key, *serialized)
        except RedisError as e:
            logger.error(f"Redis LPUSH 失败 [{key}]: {e}")
            return 0
    
    def lrange(self, key: str, start: int, end: int) -> List[Any]:
        """获取列表范围"""
        if not self.client:
            return []
        try:
            values = self.client.lrange(key, start, end)
            result = []
            for v in values:
                try:
                    result.append(json.loads(v))
                except Exception:
                    result.append(v)
            return result
        except RedisError as e:
            logger.error(f"Redis LRANGE 失败 [{key}]: {e}")
            return []
    
    def set_add(self, key: str, *members) -> int:
        """集合添加元素"""
        if not self.client:
            return 0
        try:
            serialized = [json.dumps(m, default=str) if not isinstance(m, (str, bytes)) else m for m in members]
            return self.client.sadd(key, *serialized)
        except RedisError as e:
            logger.error(f"Redis SADD 失败 [{key}]: {e}")
            return 0
    
    def set_members(self, key: str) -> set:
        """获取集合所有成员"""
        if not self.client:
            return set()
        try:
            members = self.client.smembers(key)
            result = set()
            for m in members:
                try:
                    result.add(json.loads(m))
                except Exception:
                    result.add(m)
            return result
        except RedisError as e:
            logger.error(f"Redis SMEMBERS 失败 [{key}]: {e}")
            return set()
    
    def keys(self, pattern: str = "*") -> List[str]:
        """查找匹配的 keys（慎用，大数据集性能差）"""
        if not self.client:
            return []
        try:
            return list(self.client.scan_iter(match=pattern, count=1000))
        except RedisError as e:
            logger.error(f"Redis KEYS 失败 [{pattern}]: {e}")
            return []
    
    def flushdb(self) -> bool:
        """清空当前数据库（危险操作）"""
        if not self.client:
            return False
        try:
            self.client.flushdb()
            logger.warning("Redis 数据库已清空")
            return True
        except RedisError as e:
            logger.error(f"Redis FLUSHDB 失败: {e}")
            return False
    
    def info(self) -> Dict[str, Any]:
        """获取集群信息"""
        if not self.client:
            return {}
        try:
            info = {}
            for node in self.client.get_nodes():
                node_info = node.redis_connection.info()
                info[node.name] = node_info
            return info
        except RedisError as e:
            logger.error(f"Redis INFO 失败: {e}")
            return {}
    
    def get_cluster_nodes(self) -> List[Dict]:
        """获取集群节点信息"""
        if not self.client:
            return []
        try:
            nodes = []
            for node in self.client.get_nodes():
                nodes.append({
                    "name": node.name,
                    "host": node.host,
                    "port": node.port,
                    "server_type": node.server_type  # master/replica
                })
            return nodes
        except Exception as e:
            logger.error(f"获取集群节点失败: {e}")
            return []


class CacheManager:
    """多级缓存管理器"""
    
    def __init__(self, redis_manager: Optional[RedisClusterManager] = None):
        self.redis = redis_manager
        self.local_cache = {}  # L1: 本地内存缓存
        self.local_ttl = {}    # 本地缓存过期时间
        self.default_ttl = 300  # 默认 5 分钟
        self.local_max_size = 1000  # 本地缓存最大条目数
    
    def _make_key(self, prefix: str, *args) -> str:
        """生成缓存键"""
        key_parts = [prefix] + [str(arg) for arg in args if arg is not None]
        key = ":".join(key_parts)
        return hashlib.md5(key.encode()).hexdigest()[:16]
    
    def _local_cleanup(self):
        """清理过期本地缓存"""
        now = datetime.now()
        expired = [k for k, v in self.local_ttl.items() if now > v]
        for k in expired:
            self.local_cache.pop(k, None)
            self.local_ttl.pop(k, None)
        
        # LRU 清理
        if len(self.local_cache) > self.local_max_size:
            # 简单策略：删除最早的一半
            keys = list(self.local_cache.keys())
            for k in keys[:len(keys)//2]:
                self.local_cache.pop(k, None)
                self.local_ttl.pop(k, None)
    
    def get(
        self,
        key: str,
        fetch_func: Optional[Callable] = None,
        ttl: Optional[int] = None,
        use_local: bool = True
    ) -> Any:
        """
        获取缓存，支持多级缓存
        
        Args:
            key: 缓存键
            fetch_func: 数据获取函数（缓存未命中时调用）
            ttl: 过期时间
            use_local: 是否使用本地缓存
        """
        # L1: 本地缓存
        if use_local:
            self._local_cleanup()
            if key in self.local_cache:
                if datetime.now() < self.local_ttl.get(key, datetime.min):
                    return self.local_cache[key]
                else:
                    del self.local_cache[key]
                    del self.local_ttl[key]
        
        # L2: Redis 缓存
        if self.redis and self.redis.is_connected():
            value = self.redis.get(key)
            if value is not None:
                # 回填本地缓存
                if use_local:
                    self.local_cache[key] = value
                    self.local_ttl[key] = datetime.now() + timedelta(seconds=min(ttl or self.default_ttl, 60))
                return value
        
        # 缓存未命中，执行数据获取
        if fetch_func:
            value = fetch_func()
            self.set(key, value, ttl)
            return value
        
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存"""
        ttl = ttl or self.default_ttl
        
        # L1: 本地缓存
        if len(self.local_cache) < self.local_max_size:
            self.local_cache[key] = value
            self.local_ttl[key] = datetime.now() + timedelta(seconds=min(ttl, 60))
        
        # L2: Redis 缓存
        if self.redis and self.redis.is_connected():
            return self.redis.set(key, value, ttl)
        
        return True
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        # L1
        self.local_cache.pop(key, None)
        self.local_ttl.pop(key, None)
        
        # L2
        if self.redis:
            return self.redis.delete(key)
        
        return True
    
    def invalidate_pattern(self, pattern: str) -> int:
        """按模式删除缓存"""
        count = 0
        
        # L1
        keys_to_delete = [k for k in self.local_cache.keys() if pattern in k]
        for k in keys_to_delete:
            self.local_cache.pop(k, None)
            self.local_ttl.pop(k, None)
            count += 1
        
        # L2
        if self.redis:
            keys = self.redis.keys(f"*{pattern}*")
            for k in keys:
                if self.redis.delete(k):
                    count += 1
        
        return count
    
    def cache_decorator(
        self,
        prefix: str,
        ttl: Optional[int] = None,
        key_func: Optional[Callable] = None
    ):
        """缓存装饰器"""
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 生成缓存键
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = self._make_key(prefix, func.__name__, *args, **kwargs)
                
                # 尝试获取缓存
                result = self.get(cache_key)
                if result is not None:
                    return result
                
                # 执行函数
                result = func(*args, **kwargs)
                
                # 写入缓存
                self.set(cache_key, result, ttl)
                
                return result
            return wrapper
        return decorator
    
    def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        stats = {
            "local_cache_size": len(self.local_cache),
            "local_cache_ttl_count": len(self.local_ttl),
            "redis_connected": self.redis.is_connected() if self.redis else False
        }
        
        if self.redis and self.redis.is_connected():
            try:
                info = self.redis.info()
                stats["redis_nodes"] = len(info)
                stats["redis_cluster_nodes"] = self.redis.get_cluster_nodes()
            except Exception as e:
                stats["redis_error"] = str(e)
        
        return stats


# 全局实例
_redis_manager = None
_cache_manager = None


def get_redis_manager() -> Optional[RedisClusterManager]:
    """获取 Redis 管理器单例"""
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisClusterManager()
    return _redis_manager


def get_cache_manager() -> CacheManager:
    """获取缓存管理器单例"""
    global _cache_manager
    if _cache_manager is None:
        redis_mgr = get_redis_manager()
        _cache_manager = CacheManager(redis_mgr)
    return _cache_manager


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Redis 集群管理工具")
    parser.add_argument("command", choices=["info", "test", "flush", "nodes"])
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    manager = get_redis_manager()
    
    if args.command == "info":
        import json
        print(json.dumps(manager.info(), indent=2, default=str))
    
    elif args.command == "test":
        # 测试基本操作
        print("测试 Redis 连接...")
        
        test_key = "test:connection"
        test_value = {"timestamp": datetime.now().isoformat(), "test": True}
        
        if manager.set(test_key, test_value, ttl=60):
            print("✓ SET 成功")
        
        value = manager.get(test_key)
        if value == test_value:
            print("✓ GET 成功")
        
        if manager.delete(test_key):
            print("✓ DELETE 成功")
        
        print("\n测试完成")
    
    elif args.command == "flush":
        confirm = input("警告: 这将清空所有缓存！输入 'FLUSH' 确认: ")
        if confirm == "FLUSH":
            manager.flushdb()
        else:
            print("已取消")
    
    elif args.command == "nodes":
        import json
        print(json.dumps(manager.get_cluster_nodes(), indent=2))
