#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
速率限制模块 - 生产级 API 限流实现

版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
All Rights Reserved.
"""

import time
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
from functools import wraps
from enum import Enum

from flask import request, jsonify, g

logger = logging.getLogger(__name__)


class RateLimitTier(Enum):
    """限流等级"""
    ANONYMOUS = "anonymous"    # 未认证用户
    STANDARD = "standard"      # 普通用户
    PREMIUM = "premium"        # 高级用户
    ADMIN = "admin"            # 管理员
    SERVICE = "service"        # 内部服务


@dataclass
class RateLimitConfig:
    """速率限制配置"""
    requests: int      # 请求次数
    window: int        # 时间窗口（秒）
    burst: int = 0     # 突发容量
    
    
# 默认限流配置
DEFAULT_LIMITS: Dict[RateLimitTier, RateLimitConfig] = {
    RateLimitTier.ANONYMOUS: RateLimitConfig(requests=30, window=60, burst=5),
    RateLimitTier.STANDARD: RateLimitConfig(requests=100, window=60, burst=10),
    RateLimitTier.PREMIUM: RateLimitConfig(requests=1000, window=60, burst=50),
    RateLimitTier.ADMIN: RateLimitConfig(requests=5000, window=60, burst=100),
    RateLimitTier.SERVICE: RateLimitConfig(requests=10000, window=60, burst=200),
}


@dataclass
class RateLimitEntry:
    """限流记录条目"""
    count: int = 0
    reset_time: float = 0.0
    history: list = field(default_factory=list)  # 最近请求时间戳


class RateLimiter:
    """
    速率限制器 - 滑动窗口算法
    
    特性:
    - 按用户/IP 分级限流
    - 滑动窗口计数
    - 突发流量处理
    - 分布式支持（预留 Redis 接口）
    """
    
    def __init__(self):
        self._storage: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._configs = DEFAULT_LIMITS.copy()
        self._cleanup_interval = 3600  # 1小时清理一次
        self._last_cleanup = time.time()
    
    def _get_client_id(self) -> str:
        """获取客户端标识"""
        # 优先使用用户ID
        if hasattr(g, 'user_id') and g.user_id:
            return f"user:{g.user_id}"
        
        # 否则使用 IP + User-Agent 指纹
        ip = request.remote_addr or "unknown"
        ua = request.headers.get('User-Agent', '')[:50]  # 取前50字符
        return f"ip:{ip}:{hash(ua) % 10000}"
    
    def _get_tier(self) -> RateLimitTier:
        """获取当前用户的限流等级"""
        if hasattr(g, 'user_role'):
            role = g.user_role
            if role == "admin":
                return RateLimitTier.ADMIN
            elif role == "service":
                return RateLimitTier.SERVICE
            elif role == "premium":
                return RateLimitTier.PREMIUM
            else:
                return RateLimitTier.STANDARD
        return RateLimitTier.ANONYMOUS
    
    def _cleanup_expired(self):
        """清理过期记录"""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        
        expired_keys = []
        for key, entry in self._storage.items():
            if now > entry.reset_time + 3600:  # 过期1小时
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._storage[key]
        
        if expired_keys:
            logger.debug(f"清理了 {len(expired_keys)} 条过期限流记录")
        
        self._last_cleanup = now
    
    def is_allowed(self, client_id: Optional[str] = None, 
                   tier: Optional[RateLimitTier] = None) -> Tuple[bool, Dict]:
        """
        检查是否允许请求
        
        Returns:
            (是否允许, 限流信息)
        """
        self._cleanup_expired()
        
        if client_id is None:
            client_id = self._get_client_id()
        
        if tier is None:
            tier = self._get_tier()
        
        config = self._configs.get(tier, self._configs[RateLimitTier.STANDARD])
        now = time.time()
        
        entry = self._storage[client_id]
        
        # 检查是否需要重置窗口
        if now > entry.reset_time:
            entry.count = 0
            entry.reset_time = now + config.window
            entry.history = []
        
        # 滑动窗口：清理窗口外的历史记录
        window_start = now - config.window
        entry.history = [t for t in entry.history if t > window_start]
        
        # 计算当前窗口内的请求数
        current_count = len(entry.history)
        
        # 检查是否超过限制（考虑突发）
        effective_limit = config.requests + config.burst
        
        if current_count >= effective_limit:
            retry_after = int(entry.reset_time - now)
            info = {
                "allowed": False,
                "limit": config.requests,
                "remaining": 0,
                "reset_time": entry.reset_time,
                "retry_after": max(1, retry_after),
                "tier": tier.value
            }
            return False, info
        
        # 记录本次请求
        entry.history.append(now)
        entry.count += 1
        
        remaining = max(0, config.requests - current_count - 1)
        
        info = {
            "allowed": True,
            "limit": config.requests,
            "remaining": remaining,
            "reset_time": entry.reset_time,
            "tier": tier.value
        }
        
        return True, info
    
    def limit(self, tier: Optional[RateLimitTier] = None):
        """
        装饰器：速率限制
        
        使用示例:
            @rate_limiter.limit()
            def api_endpoint():
                return jsonify({"data": "..."})
        """
        def decorator(f):
            @wraps(f)
            def decorated(*args, **kwargs):
                allowed, info = self.is_allowed(tier=tier)
                
                # 设置响应头
                headers = {
                    'X-RateLimit-Limit': str(info['limit']),
                    'X-RateLimit-Remaining': str(info['remaining']),
                    'X-RateLimit-Reset': str(int(info['reset_time']))
                }
                
                if not allowed:
                    logger.warning(f"限流触发: {self._get_client_id()}, tier={info['tier']}")
                    response = jsonify({
                        "success": False,
                        "error": {
                            "code": "RATE_LIMITED",
                            "message": f"请求过于频繁，请 {info['retry_after']} 秒后重试",
                            "retry_after": info['retry_after']
                        }
                    })
                    response.status_code = 429
                    response.headers['Retry-After'] = str(info['retry_after'])
                    for k, v in headers.items():
                        response.headers[k] = v
                    return response
                
                response = f(*args, **kwargs)
                
                # 如果是 Response 对象，添加限流头
                if hasattr(response, 'headers'):
                    for k, v in headers.items():
                        response.headers[k] = v
                
                return response
            
            return decorated
        return decorator
    
    def exempt(self, f):
        """装饰器：豁免限流（用于健康检查等）"""
        f._rate_limit_exempt = True
        return f


# 全局限流器实例
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """获取全局限流器"""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter


# 便捷装饰器
def rate_limit(tier: Optional[RateLimitTier] = None):
    """速率限制装饰器"""
    return get_rate_limiter().limit(tier)


def rate_limit_exempt(f):
    """豁免限流装饰器"""
    return get_rate_limiter().exempt(f)
