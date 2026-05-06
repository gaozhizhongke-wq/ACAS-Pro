#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Cache Manager
Multi-tier caching with Redis and local LRU
"""

import os
import json
import hashlib
import threading
import time
from typing import Any, Optional, Dict, List, Callable
from dataclasses import dataclass, field
from functools import wraps
from collections import OrderedDict
from enum import Enum
import logging

# Redis client
try:
    import redis
    from redis.sentinel import Sentinel
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('acas.cache')


class CacheStrategy(Enum):
    """缓存策略"""
    LRU = "lru"
    TTL = "ttl"
    LFU = "lfu"


@dataclass
class CacheConfig:
    """缓存配置"""
    # Redis settings
    redis_host: str = 'localhost'
    redis_port: int = 6379
    redis_password: str = ''
    redis_db: int = 0
    
    # Sentinel settings
    sentinel_hosts: List[tuple] = field(default_factory=list)
    sentinel_master_name: str = 'mymaster'
    
    # Cache settings
    default_ttl: int = 300  # 5 minutes
    max_key_size: int = 512 * 1024  # 512KB
    
    # Local cache
    local_cache_size: int = 1000
    local_cache_ttl: int = 60  # 1 minute


class LocalLRUCache:
    """本地LRU缓存 (L1)"""
    
    def __init__(self, maxsize: int = 1000, ttl: int = 60):
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: OrderedDict = OrderedDict()
        self._expires: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def _is_expired(self, key: str) -> bool:
        """检查是否过期"""
        if key not in self._expires:
            return True
        return time.time() > self._expires[key]
    
    def get(self, key: str) -> Optional[Any]:
        """获取值"""
        with self._lock:
            if key in self._cache:
                if self._is_expired(key):
                    del self._cache[key]
                    del self._expires[key]
                    self._misses += 1
                    return None
                
                # 移到末尾 (最近使用)
                self._cache.move_to_end(key)
                self._hits += 1
                return self._cache[key]
            
            self._misses += 1
            return None
    
    def set(self, key: str, value: Any, ttl: int = None):
        """设置值"""
        ttl = ttl or self.ttl
        
        with self._lock:
            # 如果已存在，移到末尾
            if key in self._cache:
                self._cache.move_to_end(key)
            
            # 添加新值
            self._cache[key] = value
            self._expires[key] = time.time() + ttl
            
            # 超出容量，删除最旧的
            while len(self._cache) > self.maxsize:
                oldest = next(iter(self._cache))
                del self._cache[oldest]
                del self._expires[oldest]
    
    def delete(self, key: str) -> bool:
        """删除值"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._expires[key]
                return True
            return False
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._expires.clear()
    
    def stats(self) -> Dict:
        """统计信息"""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0
        
        return {
            'size': len(self._cache),
            'maxsize': self.maxsize,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': f"{hit_rate:.2%}"
        }


class CacheManager:
    """
    缓存管理器
    
    两级缓存:
    - L1: 本地LRU (进程内，微秒级)
    - L2: Redis (分布式，毫秒级)
    """
    
    def __init__(self, config: CacheConfig = None):
        self.config = config or CacheConfig()
        
        # L1: 本地缓存
        self._local = LocalLRUCache(
            maxsize=self.config.local_cache_size,
            ttl=self.config.local_cache_ttl
        )
        
        # L2: Redis
        self._redis = None
        self._redis_available = False
        self._init_redis()
    
    def _init_redis(self):
        """初始化Redis连接"""
        if not REDIS_AVAILABLE:
            logger.warning("redis-py not available, using local cache only")
            return
        
        try:
            # 尝试Sentinel模式
            if self.config.sentinel_hosts:
                sentinel = Sentinel(
                    self.config.sentinel_hosts,
                    socket_timeout=0.1,
                    password=self.config.redis_password
                )
                self._redis = sentinel.master_for(
                    self.config.sentinel_master_name,
                    socket_timeout=0.1
                )
            else:
                # 直连模式
                self._redis = redis.Redis(
                    host=self.config.redis_host,
                    port=self.config.redis_port,
                    password=self.config.redis_password or None,
                    db=self.config.redis_db,
                    socket_timeout=5,
                    socket_connect_timeout=5,
                    decode_responses=True
                )
            
            # 测试连接
            self._redis.ping()
            self._redis_available = True
            logger.info(f"✓ Redis connected: {self.config.redis_host}")
            
        except Exception as e:
            logger.warning(f"⚠ Redis unavailable: {e}, using local cache only")
            self._redis_available = False
    
    def _make_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [str(a) for a in args]
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_string = ":".join(key_parts)
        
        # 如果太长，使用哈希
        if len(key_string) > 200:
            return hashlib.md5(key_string.encode()).hexdigest()
        
        return key_string
    
    def _serialize(self, value: Any) -> str:
        """序列化值"""
        return json.dumps(value, default=str)
    
    def _deserialize(self, value: str) -> Any:
        """反序列化值"""
        return json.loads(value)
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        
        顺序: L1 -> L2 -> None
        """
        # 1. 尝试L1
        value = self._local.get(key)
        if value is not None:
            return value
        
        # 2. 尝试L2
        if self._redis_available:
            try:
                raw_value = self._redis.get(key)
                if raw_value:
                    value = self._deserialize(raw_value)
                    # 回填L1
                    self._local.set(key, value)
                    return value
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        return None
    
    def set(self, key: str, value: Any, ttl: int = None, 
            l1_only: bool = False) -> bool:
        """
        设置缓存值
        
        Args:
            key: 键
            value: 值
            ttl: 过期时间(秒)
            l1_only: 仅本地缓存
        """
        ttl = ttl or self.config.default_ttl
        
        # 1. 写入L1
        self._local.set(key, value, ttl=min(ttl, self.config.local_cache_ttl))
        
        # 2. 写入L2
        if not l1_only and self._redis_available:
            try:
                serialized = self._serialize(value)
                
                # 检查大小
                if len(serialized) > self.config.max_key_size:
                    logger.warning(f"Value too large for key {key}, skipping Redis")
                    return True
                
                self._redis.setex(key, ttl, serialized)
                return True
                
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        
        return True
    
    def delete(self, key: str) -> bool:
        """删除缓存值"""
        # 删除L1
        self._local.delete(key)
        
        # 删除L2
        if self._redis_available:
            try:
                self._redis.delete(key)
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        
        return True
    
    def clear(self, pattern: str = None):
        """清空缓存"""
        # 清空L1
        self._local.clear()
        
        # 清空L2
        if self._redis_available and pattern:
            try:
                keys = self._redis.keys(pattern)
                if keys:
                    self._redis.delete(*keys)
            except Exception as e:
                logger.error(f"Redis clear error: {e}")
    
    def get_or_set(self, key: str, factory: Callable, 
                   ttl: int = None) -> Any:
        """
        获取或设置缓存
        
        Args:
            key: 缓存键
            factory: 值工厂函数
            ttl: 过期时间
        """
        # 尝试获取
        value = self.get(key)
        if value is not None:
            return value
        
        # 生成值
        value = factory()
        
        # 写入缓存
        self.set(key, value, ttl)
        
        return value
    
    def cache_decorator(self, ttl: int = None, key_prefix: str = ""):
        """缓存装饰器"""
        def decorator(func: Callable):
            @wraps(func)
            def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = f"{key_prefix}:{self._make_key(func.__name__, *args, **kwargs)}"
                
                # 尝试获取缓存
                cached = self.get(cache_key)
                if cached is not None:
                    return cached
                
                # 执行函数
                result = func(*args, **kwargs)
                
                # 写入缓存
                self.set(cache_key, result, ttl)
                
                return result
            
            # 添加清除缓存方法
            wrapper.cache_clear = lambda: self.clear(f"{key_prefix}:*")
            
            return wrapper
        return decorator
    
    def invalidate_pattern(self, pattern: str):
        """按模式失效缓存"""
        # 清空L1 (无法精确匹配，全部清空)
        self._local.clear()
        
        # 清空L2
        if self._redis_available:
            try:
                keys = self._redis.keys(pattern)
                if keys:
                    self._redis.delete(*keys)
                    logger.info(f"Invalidated {len(keys)} keys matching {pattern}")
            except Exception as e:
                logger.error(f"Redis invalidate error: {e}")
    
    def stats(self) -> Dict:
        """缓存统计"""
        stats = {
            'local': self._local.stats(),
            'redis': {
                'available': self._redis_available
            }
        }
        
        if self._redis_available:
            try:
                info = self._redis.info()
                stats['redis'].update({
                    'used_memory_human': info.get('used_memory_human'),
                    'connected_clients': info.get('connected_clients'),
                    'total_keys': self._redis.dbsize()
                })
            except Exception as e:
                stats['redis']['error'] = str(e)
        
        return stats


# 全局实例
_cache_manager: Optional[CacheManager] = None

def get_cache() -> CacheManager:
    """获取缓存管理器"""
    global _cache_manager
    if _cache_manager is None:
        config = CacheConfig(
            redis_host=os.environ.get('REDIS_HOST', 'localhost'),
            redis_port=int(os.environ.get('REDIS_PORT', '6379')),
            redis_password=os.environ.get('REDIS_PASSWORD', ''),
            redis_db=int(os.environ.get('REDIS_DB', '0'))
        )
        _cache_manager = CacheManager(config)
    return _cache_manager


if __name__ == '__main__':
    # 测试
    print("="*60)
    print("ACAS Pro - Cache Manager Test")
    print("="*60)
    
    cache = CacheManager()
    
    # 基本操作
    print("\n[1] Basic operations...")
    cache.set("user:1", {"id": 1, "name": "Test"})
    value = cache.get("user:1")
    print(f"    Set/Get: {value}")
    
    # 过期测试
    print("\n[2] TTL test...")
    cache.set("temp", "value", ttl=1)
    print(f"    Before expire: {cache.get('temp')}")
    time.sleep(2)
    print(f"    After expire: {cache.get('temp')}")
    
    # 装饰器测试
    print("\n[3] Decorator test...")
    
    @cache.cache_decorator(ttl=60, key_prefix="api")
    def get_user(user_id: int):
        print(f"    (Fetching user {user_id} from DB)")
        return {"id": user_id, "name": f"User {user_id}"}
    
    user1 = get_user(1)
    print(f"    First call: {user1}")
    user2 = get_user(1)
    print(f"    Second call (cached): {user2}")
    
    # 统计
    print("\n[4] Stats...")
    stats = cache.stats()
    print(f"    Local: {stats['local']}")
    print(f"    Redis: {stats['redis']}")
    
    print("\n" + "="*60)
    print("Cache manager test completed")
