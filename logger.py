#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro 日志系统
生产级：分级日志、文件轮转、异步写入
"""

import sys
import json
import logging
import logging.handlers
from datetime import datetime
from datetime import timezone
from functools import wraps
from pathlib import Path

# 日志目录
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# 日志格式
DETAIL_FORMAT = '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
SIMPLE_FORMAT = '%(asctime)s | %(levelname)s | %(message)s'

class JSONFormatter(logging.Formatter):
    """JSON 格式日志，便于日志分析"""
    def format(self, record):
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        if hasattr(record, 'extra_data'):
            log_data['extra'] = record.extra_data
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        return json.dumps(log_data, ensure_ascii=False)


def setup_logger(name: str, level=logging.INFO, json_format=False):
    """配置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加 handler
    if logger.handlers:
        return logger
    
    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_format = JSONFormatter() if json_format else logging.Formatter(SIMPLE_FORMAT)
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # 文件输出 (按大小轮转，10MB * 5)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / f"{name}.log",
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_format = JSONFormatter() if json_format else logging.Formatter(DETAIL_FORMAT)
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
    # 错误日志单独文件
    error_handler = logging.handlers.RotatingFileHandler(
        LOG_DIR / f"{name}.error.log",
        maxBytes=10*1024*1024,
        backupCount=5,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(file_format)
    logger.addHandler(error_handler)
    
    return logger


# 全局日志实例
app_logger = setup_logger('acas_pro', logging.INFO)
api_logger = setup_logger('acas_api', logging.INFO)
db_logger = setup_logger('acas_db', logging.INFO)


def log_execution(logger=None, level=logging.INFO):
    """装饰器：记录函数执行时间和异常"""
    def decorator(func):
        log = logger or app_logger
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = datetime.now(timezone.utc)
            func_name = func.__name__
            
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now(timezone.utc) - start).total_seconds()
                log.log(level, f"[{func_name}] 执行成功 | 耗时: {duration:.3f}s")
                return result
            except Exception as e:
                duration = (datetime.now(timezone.utc) - start).total_seconds()
                log.error(f"[{func_name}] 执行失败 | 耗时: {duration:.3f}s | 错误: {str(e)}", 
                         exc_info=True)
                raise
        
        return wrapper
    return decorator


def log_api_call(func):
    """装饰器：记录 API 调用"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        from flask import request
        
        start = datetime.now(timezone.utc)
        endpoint = request.endpoint or 'unknown'
        method = request.method
        path = request.path
        
        try:
            result = func(*args, **kwargs)
            duration = (datetime.now(timezone.utc) - start).total_seconds()
            api_logger.info(f"[{method}] {path} | {endpoint} | {duration:.3f}s | 200")
            return result
        except Exception as e:
            duration = (datetime.now(timezone.utc) - start).total_seconds()
            api_logger.error(f"[{method}] {path} | {endpoint} | {duration:.3f}s | 500 | {str(e)}")
            raise
    
    return wrapper


class PerformanceMonitor:
    """性能监控上下文管理器"""
    def __init__(self, name: str, logger=None):
        self.name = name
        self.logger = logger or app_logger
        self.start = None
    
    def __enter__(self):
        self.start = datetime.now(timezone.utc)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now(timezone.utc) - self.start).total_seconds()
        if exc_type:
            self.logger.error(f"[{self.name}] 失败 | 耗时: {duration:.3f}s | {exc_val}")
        else:
            self.logger.info(f"[{self.name}] 成功 | 耗时: {duration:.3f}s")


# 快捷方法
def info(msg, extra=None):
    app_logger.info(msg, extra={'extra_data': extra} if extra else None)

def warning(msg, extra=None):
    app_logger.warning(msg, extra={'extra_data': extra} if extra else None)

def error(msg, extra=None):
    app_logger.error(msg, extra={'extra_data': extra} if extra else None)

def debug(msg, extra=None):
    app_logger.debug(msg, extra={'extra_data': extra} if extra else None)
