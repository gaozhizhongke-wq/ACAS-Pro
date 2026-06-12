#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prometheus 指标暴露模块

版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
All Rights Reserved.
"""

import time
import logging
from functools import wraps
from typing import Callable
from contextvars import ContextVar

from prometheus_client import (
    Counter, Histogram, Gauge, Info,
    generate_latest, CONTENT_TYPE_LATEST,
    CollectorRegistry, multiprocess
)

logger = logging.getLogger(__name__)

# 请求上下文
request_ctx = ContextVar('request_ctx', default={})

# 注册表
REGISTRY = CollectorRegistry()

# 多进程支持（生产环境）
if 'prometheus_multiproc_dir' in __import__('os').environ:
    multiprocess.MultiProcessCollector(REGISTRY)


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self, service_name: str = "acas-pro"):
        self.service_name = service_name
        self._init_metrics()
    
    def _init_metrics(self):
        """初始化指标"""
        # HTTP 请求指标
        self.http_requests_total = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status'],
            registry=REGISTRY
        )
        
        self.http_request_duration_seconds = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration in seconds',
            ['method', 'endpoint'],
            buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=REGISTRY
        )
        
        self.http_request_size_bytes = Histogram(
            'http_request_size_bytes',
            'HTTP request size in bytes',
            ['method', 'endpoint'],
            buckets=[100, 1000, 10000, 100000, 1000000],
            registry=REGISTRY
        )
        
        self.http_response_size_bytes = Histogram(
            'http_response_size_bytes',
            'HTTP response size in bytes',
            ['method', 'endpoint'],
            buckets=[100, 1000, 10000, 100000, 1000000],
            registry=REGISTRY
        )
        
        # 业务指标
        self.active_users = Gauge(
            'acas_active_users',
            'Number of active users',
            registry=REGISTRY
        )
        
        self.content_created_total = Counter(
            'acas_content_created_total',
            'Total content created',
            ['content_type'],
            registry=REGISTRY
        )
        
        self.api_calls_total = Counter(
            'acas_api_calls_total',
            'Total API calls',
            ['api_name', 'status'],
            registry=REGISTRY
        )
        
        self.database_connections = Gauge(
            'acas_database_connections',
            'Database connection pool status',
            ['pool_type', 'state'],
            registry=REGISTRY
        )
        
        self.cache_hits_total = Counter(
            'acas_cache_hits_total',
            'Total cache hits',
            ['cache_layer'],
            registry=REGISTRY
        )
        
        self.cache_misses_total = Counter(
            'acas_cache_misses_total',
            'Total cache misses',
            ['cache_layer'],
            registry=REGISTRY
        )
        
        self.task_queue_size = Gauge(
            'acas_task_queue_size',
            'Task queue size',
            ['queue_name'],
            registry=REGISTRY
        )
        
        self.task_duration_seconds = Histogram(
            'acas_task_duration_seconds',
            'Task processing duration',
            ['task_type'],
            buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
            registry=REGISTRY
        )
        
        # 系统指标
        self.memory_usage_bytes = Gauge(
            'acas_memory_usage_bytes',
            'Memory usage in bytes',
            ['type'],
            registry=REGISTRY
        )
        
        self.cpu_usage_percent = Gauge(
            'acas_cpu_usage_percent',
            'CPU usage percentage',
            registry=REGISTRY
        )
        
        # 服务信息
        self.service_info = Info(
            'acas_service',
            'Service information',
            registry=REGISTRY
        )
        self.service_info.info({
            'version': '2.1.0',
            'name': self.service_name
        })
    
    def record_http_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float,
        request_size: int = 0,
        response_size: int = 0
    ):
        """记录 HTTP 请求指标"""
        status_str = str(status)
        
        self.http_requests_total.labels(
            method=method,
            endpoint=endpoint,
            status=status_str
        ).inc()
        
        self.http_request_duration_seconds.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
        
        if request_size > 0:
            self.http_request_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(request_size)
        
        if response_size > 0:
            self.http_response_size_bytes.labels(
                method=method,
                endpoint=endpoint
            ).observe(response_size)
    
    def record_cache_hit(self, layer: str = "redis"):
        """记录缓存命中"""
        self.cache_hits_total.labels(cache_layer=layer).inc()
    
    def record_cache_miss(self, layer: str = "redis"):
        """记录缓存未命中"""
        self.cache_misses_total.labels(cache_layer=layer).inc()
    
    def record_content_created(self, content_type: str):
        """记录内容创建"""
        self.content_created_total.labels(content_type=content_type).inc()
    
    def record_api_call(self, api_name: str, success: bool = True):
        """记录 API 调用"""
        status = "success" if success else "failure"
        self.api_calls_total.labels(api_name=api_name, status=status).inc()
    
    def update_active_users(self, count: int):
        """更新活跃用户数"""
        self.active_users.set(count)
    
    def update_db_connections(self, pool_type: str, active: int, idle: int):
        """更新数据库连接数"""
        self.database_connections.labels(pool_type=pool_type, state="active").set(active)
        self.database_connections.labels(pool_type=pool_type, state="idle").set(idle)
    
    def update_task_queue_size(self, queue_name: str, size: int):
        """更新任务队列大小"""
        self.task_queue_size.labels(queue_name=queue_name).set(size)
    
    def time_task(self, task_type: str):
        """任务计时上下文管理器"""
        return self.task_duration_seconds.labels(task_type=task_type).time()
    
    def get_metrics(self) -> bytes:
        """获取 Prometheus 格式的指标数据"""
        return generate_latest(REGISTRY)


# 全局实例
_metrics = None


def get_metrics() -> MetricsCollector:
    """获取指标收集器单例"""
    global _metrics
    if _metrics is None:
        _metrics = MetricsCollector()
    return _metrics


def monitor_http(func: Callable) -> Callable:
    """HTTP 请求监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        metrics = get_metrics()
        
        try:
            result = func(*args, **kwargs)
            
            # 尝试提取请求信息
            method = "GET"
            endpoint = "/unknown"
            status = 200
            
            # 从 Flask 请求对象获取
            try:
                from flask import request
                if request:
                    method = request.method
                    endpoint = request.endpoint or request.path
            except Exception:
                pass
            
            duration = time.time() - start
            metrics.record_http_request(method, endpoint, status, duration)
            
            return result
        except Exception as e:
            duration = time.time() - start
            metrics.record_http_request(method, endpoint, 500, duration)
            raise e
    
    return wrapper


def monitor_function(func: Callable) -> Callable:
    """函数执行监控装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        metrics = get_metrics()
        
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start
            
            # 记录到直方图
            metrics.task_duration_seconds.labels(
                task_type=func.__name__
            ).observe(duration)
            
            return result
        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行失败: {e}")
            raise
    
    return wrapper


class MetricsMiddleware:
    """Flask 指标中间件"""
    
    def __init__(self, app=None):
        self.app = app
        self.metrics = get_metrics()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化 Flask 应用"""
        from flask import request, g
        
        @app.before_request
        def before_request():
            g.start_time = time.time()
        
        @app.after_request
        def after_request(response):
            if hasattr(g, 'start_time'):
                duration = time.time() - g.start_time
                
                self.metrics.record_http_request(
                    method=request.method,
                    endpoint=request.endpoint or request.path,
                    status=response.status_code,
                    duration=duration,
                    request_size=request.content_length or 0,
                    response_size=response.content_length or 0
                )
            
            return response
        
        # 添加指标端点
        @app.route('/metrics')
        def metrics_endpoint():
            from flask import Response
            return Response(
                self.metrics.get_metrics(),
                mimetype=CONTENT_TYPE_LATEST
            )


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Prometheus 指标工具")
    parser.add_argument("command", choices=["test", "serve"])
    parser.add_argument("--port", type=int, default=9090)
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    metrics = get_metrics()
    
    if args.command == "test":
        print("测试指标收集...")
        
        # 模拟 HTTP 请求
        for i in range(10):
            metrics.record_http_request("GET", "/api/users", 200, 0.05 + i * 0.01)
            metrics.record_http_request("POST", "/api/content", 201, 0.1 + i * 0.02)
        
        # 模拟缓存
        metrics.record_cache_hit("redis")
        metrics.record_cache_miss("local")
        
        # 模拟业务指标
        metrics.record_content_created("article")
        metrics.update_active_users(42)
        
        print("指标数据:")
        print(metrics.get_metrics().decode()[:2000])
    
    elif args.command == "serve":
        from flask import Flask
        
        app = Flask(__name__)
        MetricsMiddleware(app)
        
        @app.route('/')
        def hello():
            return "ACAS Pro Metrics Server"
        
        @app.route('/api/test')
        def test():
            import random
            time.sleep(random.uniform(0.01, 0.1))
            return {"status": "ok"}
        
        print(f"指标服务器启动: http://localhost:{args.port}/metrics")
        app.run(host='0.0.0.0', port=args.port)
