#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro Flask 中间件
生产级：请求追踪、性能监控、安全防护
"""

import time
import uuid
import traceback
from functools import wraps
from datetime import datetime
from datetime import timezone

from flask import request, g, jsonify

from logger import api_logger, app_logger


class RequestMiddleware:
    """请求处理中间件"""
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化中间件"""
        
        @app.before_request
        def before_request():
            """请求前处理"""
            g.request_id = str(uuid.uuid4())[:8]
            g.start_time = time.time()
            
            # 记录请求信息
            api_logger.info(
                f"[{g.request_id}] {request.method} {request.path} | "
                f"IP: {request.remote_addr} | "
                f"UA: {request.user_agent.string[:50]}..."
            )
        
        @app.after_request
        def after_request(response):
            """请求后处理"""
            duration = time.time() - g.start_time
            
            # 添加响应头
            response.headers['X-Request-ID'] = g.request_id
            response.headers['X-Response-Time'] = f"{duration:.3f}s"
            
            # 记录响应
            status = response.status_code
            level = 'info' if status < 400 else 'warning' if status < 500 else 'error'
            
            getattr(api_logger, level)(
                f"[{g.request_id}] {request.method} {request.path} | "
                f"Status: {status} | Time: {duration:.3f}s"
            )
            
            return response
        
        @app.errorhandler(Exception)
        def handle_error(error):
            """全局错误处理"""
            duration = time.time() - g.get('start_time', time.time())
            request_id = g.get('request_id', 'unknown')
            
            # 记录详细错误
            api_logger.error(
                f"[{request_id}] 未处理异常 | {request.method} {request.path} | "
                f"Time: {duration:.3f}s\n{traceback.format_exc()}"
            )
            
            # 返回标准错误响应
            response = {
                'success': False,
                'error': {
                    'code': 'INTERNAL_ERROR',
                    'message': '服务器内部错误',
                    'request_id': request_id
                },
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            return jsonify(response), 500


class RateLimiter:
    """简单速率限制器（基于内存）"""
    
    def __init__(self, max_requests=100, window=60):
        """
        max_requests: 时间窗口内最大请求数
        window: 时间窗口（秒）
        """
        self.max_requests = max_requests
        self.window = window
        self.requests = {}  # {ip: [(timestamp, count), ...]}
    
    def is_allowed(self, ip: str) -> bool:
        """检查是否允许请求"""
        now = time.time()
        
        # 清理过期记录
        if ip in self.requests:
            self.requests[ip] = [
                (ts, cnt) for ts, cnt in self.requests[ip]
                if now - ts < self.window
            ]
        
        # 计算当前窗口内的请求数
        current_count = sum(
            cnt for ts, cnt in self.requests.get(ip, [])
        )
        
        if current_count >= self.max_requests:
            return False
        
        # 记录请求
        if ip not in self.requests:
            self.requests[ip] = []
        self.requests[ip].append((now, 1))
        
        return True
    
    def get_remaining(self, ip: str) -> int:
        """获取剩余可用请求数"""
        now = time.time()
        current_count = sum(
            cnt for ts, cnt in self.requests.get(ip, [])
            if now - ts < self.window
        )
        return max(0, self.max_requests - current_count)


class SecurityHeaders:
    """安全响应头中间件"""
    
    SECURITY_HEADERS = {
        'X-Content-Type-Options': 'nosniff',
        'X-Frame-Options': 'DENY',
        'X-XSS-Protection': '1; mode=block',
        'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
        'Content-Security-Policy': "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        'Referrer-Policy': 'strict-origin-when-cross-origin'
    }
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        @app.after_request
        def add_security_headers(response):
            for header, value in self.SECURITY_HEADERS.items():
                response.headers[header] = value
            return response


def require_json(f):
    """装饰器：要求请求必须是 JSON"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if request.method in ['POST', 'PUT', 'PATCH']:
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': {'code': 'INVALID_CONTENT_TYPE', 'message': 'Content-Type 必须是 application/json'}
                }), 400
        return f(*args, **kwargs)
    return decorated


def validate_json(schema: dict):
    """装饰器：验证 JSON 请求体"""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            data = request.get_json()
            errors = []
            
            for field, field_type in schema.items():
                if field not in data:
                    errors.append(f"缺少必需字段: {field}")
                elif not isinstance(data[field], field_type):
                    errors.append(f"字段 {field} 类型错误，期望 {field_type.__name__}")
            
            if errors:
                return jsonify({
                    'success': False,
                    'error': {'code': 'VALIDATION_ERROR', 'message': '; '.join(errors)}
                }), 400
            
            return f(*args, **kwargs)
        return decorated
    return decorator


# 性能指标收集
class MetricsCollector:
    """性能指标收集器"""
    
    def __init__(self):
        self.metrics = {
            'requests_total': 0,
            'requests_by_endpoint': {},
            'response_times': [],
            'errors_total': 0,
            'errors_by_type': {}
        }
    
    def record_request(self, endpoint: str, duration: float, status_code: int):
        """记录请求指标"""
        self.metrics['requests_total'] += 1
        
        if endpoint not in self.metrics['requests_by_endpoint']:
            self.metrics['requests_by_endpoint'][endpoint] = {'count': 0, 'errors': 0}
        self.metrics['requests_by_endpoint'][endpoint]['count'] += 1
        
        if status_code >= 400:
            self.metrics['requests_by_endpoint'][endpoint]['errors'] += 1
            self.metrics['errors_total'] += 1
        
        self.metrics['response_times'].append(duration)
        # 只保留最近 1000 条
        self.metrics['response_times'] = self.metrics['response_times'][-1000:]
    
    def get_summary(self) -> dict:
        """获取指标摘要"""
        times = self.metrics['response_times']
        return {
            'requests_total': self.metrics['requests_total'],
            'errors_total': self.metrics['errors_total'],
            'error_rate': self.metrics['errors_total'] / max(self.metrics['requests_total'], 1),
            'avg_response_time': sum(times) / len(times) if times else 0,
            'p95_response_time': sorted(times)[int(len(times)*0.95)] if times else 0,
            'endpoints': self.metrics['requests_by_endpoint']
        }


# 全局指标收集器
metrics = MetricsCollector()
