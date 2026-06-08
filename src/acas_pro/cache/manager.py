# -*- coding: utf-8 -*-
"""
ACAS Pro - Redis Cache Layer
Simple caching with Redis fallback to in-memory dict
"""

import json
import hashlib
import time
from functools import wraps
from typing import Optional, Any, Callable, Union
from datetime import datetime, timedelta

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from acas_pro.core.config import config
from acas_pro.core.logging import get_logger

logger = get_logger(__name__)


class CacheManager:
    """缓存管理器 - Redis优先，内存回退"""
    
    def __init__(self, redis_url: Optional[str] = None, default_ttl: int = 300):
        self._memory_cache = {}  # {key: (value, expire_at)}
        self._default_ttl = default_ttl
        self._redis = None
        
        # 尝试连接Redis
        if REDIS_AVAILABLE and redis_url:
            try:
                self._redis = redis.from_url(redis_url, decode_responses=True)
                self._redis.ping()
                logger.info("Redis cache connected")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}, using memory cache")
                self._redis = None
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if self._redis:
            try:
                value = self._redis.get(key)
                if value:
                    return json.loads(value)
            except Exception as e:
                logger.warning(f"Redis get failed: {e}")
        
        # 内存回退
        if key in self._memory_cache:
            value, expire_at = self._memory_cache[key]
            if time.time() < expire_at:
                return value
            else:
                del self._memory_cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        ttl = ttl or self._default_ttl
        serialized = json.dumps(value, default=str)
        
        if self._redis:
            try:
                self._redis.setex(key, ttl, serialized)
                return True
            except Exception as e:
                logger.warning(f"Redis set failed: {e}")
        
        # 内存回退
        self._memory_cache[key] = (value, time.time() + ttl)
        return True
    
    def delete(self, key: str) -> bool:
        """删除缓存"""
        if self._redis:
            try:
                self._redis.delete(key)
            except Exception as e:
                logger.warning(f"Redis delete failed: {e}")
        
        self._memory_cache.pop(key, None)
        return True
    
    def clear(self) -> bool:
        """清空所有缓存"""
        if self._redis:
            try:
                self._redis.flushdb()
            except Exception as e:
                logger.warning(f"Redis flush failed: {e}")
        
        self._memory_cache.clear()
        return True
    
    def keys(self, pattern: str = "*") -> list:
        """获取匹配的key列表"""
        if self._redis:
            try:
                return list(self._redis.scan_iter(match=pattern))
            except Exception as e:
                logger.warning(f"Redis keys failed: {e}")
        
        # 内存模式简单匹配
        import fnmatch
        return [k for k in self._memory_cache.keys() if fnmatch.fnmatch(k, pattern)]


# 全局缓存实例
cache = CacheManager()


def cached(ttl: int = 300, key_prefix: str = "") -> None:
    """缓存装饰器
    
    Usage:
        @cached(ttl=60, key_prefix="trend")
        def get_trending_items(platform: str) -> list:
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> None:
            # 生成缓存key
            cache_key = _generate_cache_key(key_prefix, func.__name__, args, kwargs)
            
            # 尝试读取缓存
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 写入缓存
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cache set: {cache_key}")
            
            return result
        
        # 附加缓存控制方法
        wrapper.cache_clear = lambda: cache.delete(_generate_cache_key(key_prefix, func.__name__, (), {}))
        wrapper.cache_key = lambda *a, **k: _generate_cache_key(key_prefix, func.__name__, a, k)
        
        return wrapper
    return decorator


def _generate_cache_key(prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
    """生成缓存key"""
    key_data = f"{prefix}:{func_name}:{args}:{sorted(kwargs.items())}"
    return f"acas:{prefix}:{func_name}:{hashlib.md5(key_data.encode()).hexdigest()}"


# 常用缓存模式
def cache_model_list(model_name: str, ttl: int = 60) -> None:
    """模型列表缓存"""
    return cached(ttl=ttl, key_prefix=f"model:{model_name}:list")


def cache_api_response(endpoint: str, ttl: int = 30) -> None:
    """API响应缓存"""
    return cached(ttl=ttl, key_prefix=f"api:{endpoint}")


def cache_forecast_result(model_type: str, ttl: int = 600) -> None:
    """预测结果缓存（10分钟）"""
    return cached(ttl=ttl, key_prefix=f"forecast:{model_type}")


# 缓存预热工具
async def warm_cache(patterns: list[str]) -> None:
    """缓存预热 - 预加载常用数据"""
    logger.info(f"Cache warming started for {len(patterns)} patterns")
    # 实际实现由业务层填充
    pass
