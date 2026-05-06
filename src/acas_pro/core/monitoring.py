#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Production Monitoring
Health checks, metrics, and observability
"""

import time
import json
import psutil
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import threading

from .config import config
from .logging import get_logger

logger = get_logger(__name__)


@dataclass
class HealthStatus:
    """Health check status"""
    name: str
    healthy: bool
    message: str = ""
    latency_ms: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)


class HealthChecker:
    """
    Health check system
    
    Endpoints:
    - /health - Liveness probe (is app running?)
    - /ready - Readiness probe (can app handle requests?)
    """
    
    def __init__(self):
        self._checks: Dict[str, callable] = {}
        self._last_check: Dict[str, HealthStatus] = {}
        self._lock = threading.Lock()
    
    def register(self, name: str, check_func: callable):
        """Register a health check function"""
        self._checks[name] = check_func
        logger.info(f"Registered health check: {name}")
    
    def check(self, name: str = None) -> HealthStatus:
        """Run a specific health check"""
        if name and name in self._checks:
            return self._run_check(name, self._checks[name])
        elif name:
            return HealthStatus(name=name, healthy=False, message="Check not found")
        
        # Run all checks
        results = {}
        for check_name, check_func in self._checks.items():
            results[check_name] = self._run_check(check_name, check_func)
        
        return results
    
    def _run_check(self, name: str, check_func: callable) -> HealthStatus:
        """Execute a single health check"""
        start = time.time()
        try:
            result = check_func()
            latency = (time.time() - start) * 1000
            
            if isinstance(result, bool):
                status = HealthStatus(name=name, healthy=result, latency_ms=latency)
            elif isinstance(result, dict):
                status = HealthStatus(
                    name=name,
                    healthy=result.get('healthy', False),
                    message=result.get('message', ''),
                    latency_ms=latency,
                    details=result.get('details', {})
                )
            else:
                status = HealthStatus(name=name, healthy=False, message="Invalid check result")
            
            with self._lock:
                self._last_check[name] = status
            
            return status
        except Exception as e:
            latency = (time.time() - start) * 1000
            status = HealthStatus(name=name, healthy=False, message=str(e), latency_ms=latency)
            with self._lock:
                self._last_check[name] = status
            return status
    
    def liveness(self) -> Dict[str, Any]:
        """
        Liveness probe - is the application running?
        
        Kubernetes uses this to decide if container should be restarted.
        """
        return {
            "status": "alive",
            "timestamp": datetime.utcnow().isoformat(),
            "version": config.version
        }
    
    def readiness(self) -> Dict[str, Any]:
        """
        Readiness probe - can the application handle requests?
        
        Kubernetes uses this to decide if traffic should be routed.
        """
        results = self.check()
        
        # Check if all critical services are healthy
        all_healthy = all(
            r.healthy for r in results.values()
            if r.name in ['database', 'cache']  # Critical services
        )
        
        return {
            "status": "ready" if all_healthy else "not_ready",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {
                name: {
                    "healthy": status.healthy,
                    "message": status.message,
                    "latency_ms": round(status.latency_ms, 2)
                }
                for name, status in results.items()
            }
        }


class PrometheusMetrics:
    """
    Prometheus-compatible metrics exporter
    
    Metrics format:
    - Counter: monotonically increasing (requests_total, errors_total)
    - Gauge: point-in-time value (active_connections, memory_usage)
    - Histogram: distribution (request_duration_seconds)
    """
    
    def __init__(self, namespace: str = "acas"):
        self.namespace = namespace
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = defaultdict(list)
        self._lock = threading.Lock()
    
    def counter(self, name: str, value: int = 1, labels: Dict[str, str] = None):
        """Increment a counter"""
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] += value
    
    def gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        """Set a gauge value"""
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value
    
    def histogram(self, name: str, value: float, labels: Dict[str, str] = None):
        """Record a histogram observation"""
        key = self._make_key(name, labels)
        with self._lock:
            self._histograms[key].append(value)
            # Keep only last 1000 observations
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]
    
    def _make_key(self, name: str, labels: Dict[str, str] = None) -> str:
        """Create metric key with labels"""
        if labels:
            label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name
    
    def export(self) -> str:
        """
        Export metrics in Prometheus text format
        
        Example:
        # HELP acas_http_requests_total Total HTTP requests
        # TYPE acas_http_requests_total counter
        acas_http_requests_total{method="GET",path="/api/health"} 123
        """
        lines = []
        
        # Counters
        for key, value in sorted(self._counters.items()):
            name = key.split('{')[0]
            lines.append(f"# TYPE {self.namespace}_{name} counter")
            lines.append(f"{self.namespace}_{key} {value}")
        
        # Gauges
        for key, value in sorted(self._gauges.items()):
            name = key.split('{')[0]
            lines.append(f"# TYPE {self.namespace}_{name} gauge")
            lines.append(f"{self.namespace}_{key} {value}")
        
        # Histograms (simplified - just p50, p95, p99)
        for key, values in sorted(self._histograms.items()):
            if not values:
                continue
            name = key.split('{')[0]
            sorted_values = sorted(values)
            n = len(sorted_values)
            
            lines.append(f"# TYPE {self.namespace}_{name} summary")
            lines.append(f"{self.namespace}_{key}_count {n}")
            lines.append(f"{self.namespace}_{key}_sum {sum(values):.6f}")
            
            # Percentiles
            p50 = sorted_values[int(n * 0.50)] if n > 0 else 0
            p95 = sorted_values[int(n * 0.95)] if n > 0 else 0
            p99 = sorted_values[int(n * 0.99)] if n > 0 else 0
            
            lines.append(f"{self.namespace}_{key}{key[len(name):]} {{quantile=\"0.5\"}} {p50:.6f}")
            lines.append(f"{self.namespace}_{key}{key[len(name):]} {{quantile=\"0.95\"}} {p95:.6f}")
            lines.append(f"{self.namespace}_{key}{key[len(name):]} {{quantile=\"0.99\"}} {p99:.6f}")
        
        return "\n".join(lines) + "\n"
    
    def collect_system_metrics(self):
        """Collect system-level metrics"""
        # CPU
        self.gauge("cpu_percent", psutil.cpu_percent())
        self.gauge("cpu_count", psutil.cpu_count())
        
        # Memory
        mem = psutil.virtual_memory()
        self.gauge("memory_total_bytes", mem.total)
        self.gauge("memory_available_bytes", mem.available)
        self.gauge("memory_used_bytes", mem.used)
        self.gauge("memory_percent", mem.percent)
        
        # Disk
        disk = psutil.disk_usage('/')
        self.gauge("disk_total_bytes", disk.total)
        self.gauge("disk_used_bytes", disk.used)
        self.gauge("disk_percent", disk.percent)
        
        # Process
        proc = psutil.Process()
        self.gauge("process_memory_bytes", proc.memory_info().rss)
        self.gauge("process_cpu_percent", proc.cpu_percent())
        self.gauge("process_threads", proc.num_threads())
        self.gauge("process_open_files", len(proc.open_files()) if hasattr(proc, 'open_files') else 0)


class RequestTracker:
    """
    Request tracking with request ID for distributed tracing
    
    Integrates with:
    - Structured logging
    - Error tracking (Sentry)
    - APM tools
    """
    
    def __init__(self):
        self._current_request: Dict[str, Any] = {}
        self._request_log: List[Dict[str, Any]] = []
    
    def start_request(self, request_id: str, method: str, path: str, 
                      user_id: str = None, ip_address: str = None) -> str:
        """Start tracking a request"""
        import uuid
        if not request_id:
            request_id = str(uuid.uuid4())
        
        self._current_request = {
            "request_id": request_id,
            "method": method,
            "path": path,
            "user_id": user_id,
            "ip_address": ip_address,
            "start_time": time.time(),
            "start_timestamp": datetime.utcnow().isoformat()
        }
        
        return request_id
    
    def end_request(self, status_code: int, error: str = None) -> Dict[str, Any]:
        """End tracking a request"""
        if not self._current_request:
            return {}
        
        duration_ms = (time.time() - self._current_request["start_time"]) * 1000
        
        result = {
            **self._current_request,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "error": error,
            "end_timestamp": datetime.utcnow().isoformat()
        }
        
        # Add to log (keep last 1000)
        self._request_log.append(result)
        if len(self._request_log) > 1000:
            self._request_log = self._request_log[-1000:]
        
        self._current_request = {}
        return result
    
    def get_request_id(self) -> Optional[str]:
        """Get current request ID"""
        return self._current_request.get("request_id")


# Global instances
health_checker = HealthChecker()
metrics = PrometheusMetrics()
request_tracker = RequestTracker()


# Register default health checks
def _check_database() -> Dict[str, Any]:
    """Check database connectivity"""
    try:
        from .database import db
        # Simple query to test connection
        db.execute("SELECT 1")
        return {"healthy": True, "message": "Database connected"}
    except Exception as e:
        return {"healthy": False, "message": str(e)}


def _check_cache() -> Dict[str, Any]:
    """Check cache (Redis) if configured"""
    # TODO: Add Redis check when cache is implemented
    return {"healthy": True, "message": "Cache not configured"}


def _check_disk_space() -> Dict[str, Any]:
    """Check disk space"""
    try:
        disk = psutil.disk_usage('/')
        if disk.percent > 90:
            return {"healthy": False, "message": f"Disk usage {disk.percent}%"}
        return {"healthy": True, "message": f"Disk usage {disk.percent}%", "details": {"percent": disk.percent}}
    except Exception as e:
        return {"healthy": False, "message": str(e)}


# Register on module load
health_checker.register("database", _check_database)
health_checker.register("cache", _check_cache)
health_checker.register("disk", _check_disk_space)
