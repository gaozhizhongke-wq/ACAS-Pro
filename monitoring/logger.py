#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
结构化日志模块 - JSON 格式输出

版权所有 (C) 2024-2026 高智中科（北京）科技有限公司
All Rights Reserved.
"""

import os
import sys
import json
import logging
import traceback
import uuid
from datetime import datetime
from datetime import timezone
from typing import Optional, Dict, Any, Union
from contextvars import ContextVar
from pythonjsonlogger import jsonlogger

# 请求追踪 ID
request_id_ctx = ContextVar('request_id', default=None)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """自定义 JSON 日志格式化器"""
    
    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)
        
        # 添加时间戳
        log_record['timestamp'] = datetime.now(timezone.utc).isoformat() + 'Z'
        log_record['level'] = record.levelname
        log_record['logger'] = record.name
        
        # 添加请求追踪 ID
        request_id = request_id_ctx.get()
        if request_id:
            log_record['request_id'] = request_id
        
        # 添加服务信息
        log_record['service'] = 'acas-pro'
        log_record['version'] = '2.1.0'
        
        # 添加环境信息
        log_record['environment'] = os.getenv('ENVIRONMENT', 'production')
        
        # 处理异常信息
        if record.exc_info:
            log_record['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'stacktrace': traceback.format_exception(*record.exc_info)
            }


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str = "acas-pro"):
        self.name = name
        self.logger = logging.getLogger(name)
        self._setup_logger()
    
    def _setup_logger(self):
        """配置日志记录器"""
        # 设置日志级别
        level = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.logger.setLevel(getattr(logging, level, logging.INFO))
        
        # 清除现有处理器
        self.logger.handlers = []
        
        # 控制台输出
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        
        # JSON 格式化
        formatter = CustomJsonFormatter(
            '%(timestamp)s %(level)s %(name)s %(message)s'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # 文件输出（生产环境）
        log_dir = os.getenv('LOG_DIR', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            filename=f"{log_dir}/acas-pro.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=10,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        # 错误日志单独文件
        error_handler = logging.handlers.RotatingFileHandler(
            filename=f"{log_dir}/acas-pro-error.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=10,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.logger.addHandler(error_handler)
    
    def set_request_id(self, request_id: Optional[str] = None) -> str:
        """设置请求追踪 ID"""
        if request_id is None:
            request_id = str(uuid.uuid4())[:8]
        request_id_ctx.set(request_id)
        return request_id
    
    def _log(
        self,
        level: int,
        message: str,
        extra: Optional[Dict[str, Any]] = None,
        exc_info: bool = False
    ):
        """内部日志方法"""
        extra = extra or {}
        
        # 构建结构化数据
        structured_data = {
            'message': message,
            **extra
        }
        
        self.logger.log(level, json.dumps(structured_data, ensure_ascii=False), exc_info=exc_info)
    
    def debug(self, message: str, **extra):
        """调试日志"""
        self._log(logging.DEBUG, message, extra)
    
    def info(self, message: str, **extra):
        """信息日志"""
        self._log(logging.INFO, message, extra)
    
    def warning(self, message: str, **extra):
        """警告日志"""
        self._log(logging.WARNING, message, extra)
    
    def error(self, message: str, exc_info: bool = False, **extra):
        """错误日志"""
        self._log(logging.ERROR, message, extra, exc_info=exc_info)
    
    def critical(self, message: str, exc_info: bool = False, **extra):
        """严重错误日志"""
        self._log(logging.CRITICAL, message, extra, exc_info=exc_info)
    
    def audit(
        self,
        action: str,
        user_id: Optional[str] = None,
        resource: Optional[str] = None,
        result: str = "success",
        details: Optional[Dict] = None
    ):
        """
        审计日志
        
        Args:
            action: 操作类型 (login, logout, create, update, delete, ...)
            user_id: 用户 ID
            resource: 操作资源
            result: 操作结果 (success, failure, denied)
            details: 详细信息
        """
        audit_data = {
            'audit': True,
            'action': action,
            'user_id': user_id,
            'resource': resource,
            'result': result,
            'details': details or {},
            'ip_address': details.get('ip_address') if details else None,
            'user_agent': details.get('user_agent') if details else None
        }
        
        self._log(logging.INFO, f"AUDIT: {action}", audit_data)
    
    def performance(
        self,
        operation: str,
        duration_ms: float,
        success: bool = True,
        **extra
    ):
        """性能日志"""
        perf_data = {
            'performance': True,
            'operation': operation,
            'duration_ms': round(duration_ms, 2),
            'success': success,
            **extra
        }
        
        self._log(logging.INFO, f"PERF: {operation}", perf_data)
    
    def security(
        self,
        event: str,
        severity: str = "medium",
        **extra
    ):
        """安全事件日志"""
        security_data = {
            'security': True,
            'event': event,
            'severity': severity,
            **extra
        }
        
        level = logging.WARNING if severity in ['medium', 'low'] else logging.ERROR
        self._log(level, f"SECURITY: {event}", security_data)


# 全局实例
_structured_logger = None


def get_logger() -> StructuredLogger:
    """获取结构化日志记录器单例"""
    global _structured_logger
    if _structured_logger is None:
        _structured_logger = StructuredLogger()
    return _structured_logger


class LoggingMiddleware:
    """Flask 日志中间件"""
    
    def __init__(self, app=None):
        self.app = app
        self.logger = get_logger()
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """初始化 Flask 应用"""
        from flask import request, g
        import time
        
        @app.before_request
        def before_request():
            # 生成请求 ID
            request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())[:8]
            self.logger.set_request_id(request_id)
            g.start_time = time.time()
            g.request_id = request_id
            
            # 记录请求开始
            self.logger.info(
                "Request started",
                method=request.method,
                path=request.path,
                query_string=request.query_string.decode(),
                remote_addr=request.remote_addr,
                user_agent=request.user_agent.string if request.user_agent else None
            )
        
        @app.after_request
        def after_request(response):
            duration = (time.time() - g.start_time) * 1000
            
            # 记录请求完成
            self.logger.info(
                "Request completed",
                method=request.method,
                path=request.path,
                status_code=response.status_code,
                duration_ms=round(duration, 2),
                content_length=response.content_length,
                request_id=g.request_id
            )
            
            # 添加请求 ID 到响应头
            response.headers['X-Request-ID'] = g.request_id
            
            return response
        
        @app.errorhandler(Exception)
        def handle_exception(error):
            self.logger.error(
                "Request failed",
                method=request.method,
                path=request.path,
                error_type=type(error).__name__,
                error_message=str(error),
                exc_info=True
            )
            raise error


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="结构化日志工具")
    parser.add_argument("command", choices=["test", "demo"])
    
    args = parser.parse_args()
    
    logger = get_logger()
    
    if args.command == "test":
        logger.debug("调试信息", module="test", detail="something")
        logger.info("普通信息", user="admin", action="login")
        logger.warning("警告信息", resource="cpu", usage=85)
        
        try:
            1 / 0
        except:
            logger.error("发生错误", exc_info=True)
        
        logger.critical("严重错误", system="database", status="down")
        
        # 审计日志
        logger.audit(
            action="user_login",
            user_id="user_123",
            resource="auth_system",
            result="success",
            details={"ip_address": "192.168.1.1", "method": "password"}
        )
        
        # 性能日志
        logger.performance(
            operation="database_query",
            duration_ms=45.5,
            table="users",
            rows_returned=10
        )
        
        # 安全日志
        logger.security(
            event="suspicious_login_attempt",
            severity="high",
            source_ip="10.0.0.99",
            attempts=5
        )
    
    elif args.command == "demo":
        from flask import Flask
        
        app = Flask(__name__)
        LoggingMiddleware(app)
        
        @app.route('/')
        def hello():
            logger.info("处理首页请求")
            return {"message": "Hello"}
        
        @app.route('/error')
        def error():
            raise ValueError("测试错误")
        
        print("日志演示服务器启动: http://localhost:5000")
        print("访问 / 查看正常日志")
        print("访问 /error 查看错误日志")
        app.run(debug=True)
