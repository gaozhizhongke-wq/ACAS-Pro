#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Prometheus Metrics
Production monitoring and observability
"""

import time
from functools import wraps
from typing import Callable
from flask import request, g
from ..core.logging import get_logger

logger = get_logger(__name__)

try:
    from prometheus_client import (
        Counter,
        Histogram,
        Gauge,
        Info,
        generate_latest,
        CONTENT_TYPE_LATEST,
    )

    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

    # Dummy classes for when prometheus is not installed
    class Counter:
        def __init__(self, *args, **kwargs):
            pass

        def inc(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

    class Histogram:
        def __init__(self, *args, **kwargs):
            pass

        def observe(self, *args, **kwargs):
            pass

        def time(self):
            return self

        def labels(self, *args, **kwargs):
            return self

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    class Gauge:
        def __init__(self, *args, **kwargs):
            pass

        def set(self, *args, **kwargs):
            pass

        def inc(self, *args, **kwargs):
            pass

        def dec(self, *args, **kwargs):
            pass

        def labels(self, *args, **kwargs):
            return self

    class Info:
        def __init__(self, *args, **kwargs):
            pass

        def info(self, *args, **kwargs):
            pass

    CONTENT_TYPE_LATEST = "text/plain"

    def generate_latest(*args):
        return b"prometheus not installed"


# Application info
APP_INFO = Info("acas_app", "ACAS Pro application info")

# Request metrics
REQUEST_COUNT = Counter(
    "acas_http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"]
)

REQUEST_DURATION = Histogram(
    "acas_http_request_duration_seconds",
    "HTTP request duration",
    ["method", "endpoint"],
)

# Business metrics
ACTIVE_USERS = Gauge("acas_active_users", "Number of active users")
TOTAL_USERS = Gauge("acas_total_users", "Total registered users")
LLM_REQUESTS = Counter(
    "acas_llm_requests_total", "Total LLM API requests", ["provider", "model", "status"]
)

LLM_LATENCY = Histogram(
    "acas_llm_request_duration_seconds",
    "LLM API request duration",
    ["provider", "model"],
)

# Database metrics
DB_CONNECTIONS = Gauge("acas_db_connections", "Database connection pool size")
DB_ERRORS = Counter("acas_db_errors_total", "Total database errors")

# Queue metrics (if using Redis queue)
QUEUE_SIZE = Gauge("acas_queue_size", "Background queue size", ["queue_name"])
QUEUE_JOBS = Counter(
    "acas_queue_jobs_total", "Total queue jobs", ["queue_name", "status"]
)


class MetricsMiddleware:
    """Flask middleware for collecting metrics"""

    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)

    def init_app(self, app) -> None:
        """Initialize metrics middleware"""

        @app.before_request
        def before_request() -> None:
            g.start_time = time.time()

        @app.after_request
        def after_request(response) -> None:
            if hasattr(g, "start_time"):
                duration = time.time() - g.start_time

                # Get endpoint name (handle static files)
                endpoint = request.endpoint or "static"
                if endpoint == "static":
                    endpoint = request.path

                # Record metrics
                REQUEST_DURATION.labels(
                    method=request.method, endpoint=endpoint
                ).observe(duration)

                REQUEST_COUNT.labels(
                    method=request.method,
                    endpoint=endpoint,
                    status=response.status_code,
                ).inc()

            return response


def monitor_llm(provider: str, model: str) -> None:
    """Decorator to monitor LLM calls"""

    def decorator(f: Callable) -> None:
        @wraps(f)
        def wrapper(*args, **kwargs) -> None:
            start = time.time()
            try:
                result = f(*args, **kwargs)
                LLM_REQUESTS.labels(
                    provider=provider, model=model, status="success"
                ).inc()
                return result
            except Exception as e:
                logger.exception(f"Error in wrapper: {e}")
                LLM_REQUESTS.labels(
                    provider=provider, model=model, status="error"
                ).inc()
                raise
            finally:
                LLM_LATENCY.labels(provider=provider, model=model).observe(
                    time.time() - start
                )

        return wrapper

    return decorator


def get_metrics() -> None:
    """Get Prometheus metrics output"""
    return generate_latest()


def init_app_info(version: str = "2.0.0", environment: str = "production") -> None:
    """Initialize application info metrics"""
    APP_INFO.info({"version": version, "environment": environment})
