#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Monitoring Module Tests
Tests for health checks, Prometheus metrics, and request tracking
"""

import pytest
import time
from datetime import datetime
from unittest.mock import patch, MagicMock

from acas_pro.core.monitoring import (
    HealthChecker, HealthStatus,
    PrometheusMetrics, RequestTracker
)


# ============================================
# HealthChecker Tests
# ============================================

class TestHealthChecker:
    """Health check system tests"""

    def test_register_check(self):
        """Test registering a health check"""
        checker = HealthChecker()

        def mock_check():
            return {"healthy": True, "message": "OK"}

        checker.register("test_service", mock_check)
        assert "test_service" in checker._checks

    def test_run_single_check(self):
        """Test running a single health check"""
        checker = HealthChecker()

        def passing_check():
            return {"healthy": True, "message": "All good"}

        checker.register("passing", passing_check)
        result = checker.check("passing")

        assert result.healthy is True
        assert result.name == "passing"
        assert result.message == "All good"
        assert result.latency_ms >= 0

    def test_run_failing_check(self):
        """Test running a failing health check"""
        checker = HealthChecker()

        def failing_check():
            return {"healthy": False, "message": "Connection refused"}

        checker.register("failing", failing_check)
        result = checker.check("failing")

        assert result.healthy is False
        assert "refused" in result.message

    def test_run_check_with_exception(self):
        """Test health check that throws exception"""
        checker = HealthChecker()

        def error_check():
            raise ConnectionError("Cannot connect to database")

        checker.register("error", error_check)
        result = checker.check("error")

        assert result.healthy is False
        assert "Cannot connect" in result.message

    def test_run_all_checks(self):
        """Test running all registered checks"""
        checker = HealthChecker()

        checker.register("db", lambda: {"healthy": True})
        checker.register("cache", lambda: {"healthy": True})
        checker.register("disk", lambda: {"healthy": False, "message": "Low space"})

        results = checker.check()

        assert isinstance(results, dict)
        assert len(results) == 3
        assert results["db"].healthy is True
        assert results["disk"].healthy is False

    def test_check_nonexistent(self):
        """Test checking non-existent service"""
        checker = HealthChecker()
        result = checker.check("nonexistent")

        assert result.healthy is False
        assert "not found" in result.message.lower()

    def test_liveness_probe(self):
        """Test liveness probe structure"""
        checker = HealthChecker()

        result = checker.liveness()

        assert result["status"] == "alive"
        assert "timestamp" in result
        assert "version" in result

    def test_readiness_probe_all_healthy(self):
        """Test readiness probe when all checks pass"""
        checker = HealthChecker()

        checker.register("database", lambda: {"healthy": True})
        checker.register("cache", lambda: {"healthy": True})

        result = checker.readiness()

        assert result["status"] == "ready"
        assert "checks" in result
        assert "database" in result["checks"]
        assert "cache" in result["checks"]

    def test_readiness_probe_unhealthy(self):
        """Test readiness probe when critical checks fail"""
        checker = HealthChecker()

        checker.register("database", lambda: {"healthy": False, "message": "Down"})
        checker.register("cache", lambda: {"healthy": True})

        result = checker.readiness()

        assert result["status"] == "not_ready"
        assert result["checks"]["database"]["healthy"] is False

    def test_health_check_latency_tracking(self):
        """Test that health check tracks latency"""
        checker = HealthChecker()

        def slow_check():
            time.sleep(0.01)
            return {"healthy": True}

        checker.register("slow", slow_check)
        result = checker.check("slow")

        assert result.latency_ms > 0
        # Should be at least 10ms due to sleep
        assert result.latency_ms >= 8  # Allow some tolerance

    def test_bool_return_check(self):
        """Test health check that returns bool"""
        checker = HealthChecker()

        checker.register("simple", lambda: True)
        result = checker.check("simple")

        assert result.healthy is True

    def test_invalid_return_check(self):
        """Test health check that returns invalid type"""
        checker = HealthChecker()

        checker.register("invalid", lambda: 42)
        result = checker.check("invalid")

        assert result.healthy is False

    def test_last_check_cache(self):
        """Test that last check result is cached"""
        checker = HealthChecker()

        checker.register("cache_test", lambda: {"healthy": True})
        checker.check("cache_test")

        assert "cache_test" in checker._last_check
        assert checker._last_check["cache_test"].healthy is True


# ============================================
# PrometheusMetrics Tests
# ============================================

class TestPrometheusMetrics:
    """Prometheus metrics export tests"""

    def test_counter_increment(self):
        """Test counter increment"""
        metrics = PrometheusMetrics()

        metrics.counter("http_requests_total", labels={"method": "GET"})
        metrics.counter("http_requests_total", labels={"method": "GET"})

        output = metrics.export()
        assert "http_requests_total" in output
        # Should have counted to 2
        assert "2" in output

    def test_counter_with_labels(self):
        """Test counter with multiple labels"""
        metrics = PrometheusMetrics()

        metrics.counter("requests_total", labels={"method": "GET", "path": "/health"})
        metrics.counter("requests_total", labels={"method": "POST", "path": "/login"})

        output = metrics.export()
        assert 'method="GET"' in output
        assert 'method="POST"' in output
        assert 'path="/health"' in output

    def test_gauge_set(self):
        """Test gauge value setting"""
        metrics = PrometheusMetrics()

        metrics.gauge("active_connections", 42)
        output = metrics.export()

        assert "active_connections" in output
        assert "42" in output

    def test_gauge_overwrite(self):
        """Test gauge value overwrite"""
        metrics = PrometheusMetrics()

        metrics.gauge("temperature", 25.5)
        metrics.gauge("temperature", 30.0)

        output = metrics.export()
        assert "30.0" in output

    def test_histogram_observation(self):
        """Test histogram observation recording"""
        metrics = PrometheusMetrics()

        for duration in [0.1, 0.2, 0.3, 0.5, 1.0]:
            metrics.histogram("request_duration_seconds", duration)

        output = metrics.export()
        assert "request_duration_seconds" in output
        assert "_count 5" in output
        assert "_sum" in output

    def test_histogram_percentiles(self):
        """Test histogram percentile calculation"""
        metrics = PrometheusMetrics()

        # Add 100 observations
        for i in range(100):
            metrics.histogram("latency", i * 0.01, labels={"endpoint": "/api"})

        output = metrics.export()
        assert 'quantile="0.5"' in output
        assert 'quantile="0.95"' in output
        assert 'quantile="0.99"' in output

    def test_histogram_max_observations(self):
        """Test histogram keeps max 1000 observations"""
        metrics = PrometheusMetrics()

        for i in range(1500):
            metrics.histogram("test_metric", i * 0.001)

        # Should only keep last 1000
        key = next(iter(metrics._histograms))
        assert len(metrics._histograms[key]) <= 1000

    def test_export_namespace_prefix(self):
        """Test that export adds namespace prefix"""
        metrics = PrometheusMetrics(namespace="acas")

        metrics.counter("test_metric")
        output = metrics.export()

        assert "acas_test_metric" in output

    def test_export_type_annotations(self):
        """Test Prometheus TYPE annotations in export"""
        metrics = PrometheusMetrics()

        metrics.counter("my_counter")
        metrics.gauge("my_gauge", 42)

        output = metrics.export()
        assert "# TYPE" in output
        assert "counter" in output
        assert "gauge" in output

    def test_thread_safety(self):
        """Test metrics thread safety"""
        import threading

        metrics = PrometheusMetrics()
        errors = []

        def increment_many():
            try:
                for _ in range(100):
                    metrics.counter("thread_test")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=increment_many) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0

        # Total should be 500
        key = next(iter(metrics._counters))
        assert metrics._counters[key] == 500

    def test_system_metrics_collection(self):
        """Test system metrics collection"""
        metrics = PrometheusMetrics()

        # Should not raise
        metrics.collect_system_metrics()

        output = metrics.export()
        assert "cpu_percent" in output
        assert "memory_percent" in output

    def test_empty_export(self):
        """Test export with no metrics"""
        metrics = PrometheusMetrics()

        output = metrics.export()
        assert output.strip() == "" or output.strip() == "\n"


# ============================================
# RequestTracker Tests
# ============================================

class TestRequestTracker:
    """Request tracking and tracing tests"""

    def test_start_request(self):
        """Test starting request tracking"""
        tracker = RequestTracker()

        request_id = tracker.start_request("req-123", "GET", "/api/v1/users")

        assert request_id == "req-123"

    def test_auto_generate_request_id(self):
        """Test auto-generated request ID"""
        tracker = RequestTracker()

        request_id = tracker.start_request("", "GET", "/health")

        assert request_id is not None
        assert len(request_id) > 0

    def test_end_request(self):
        """Test ending request tracking"""
        tracker = RequestTracker()

        tracker.start_request("req-1", "POST", "/api/v1/login")
        result = tracker.end_request(200)

        assert result["status_code"] == 200
        assert result["method"] == "POST"
        assert "duration_ms" in result
        assert result["duration_ms"] >= 0

    def test_end_request_with_error(self):
        """Test ending request with error"""
        tracker = RequestTracker()

        tracker.start_request("req-2", "GET", "/api/v1/broken")
        result = tracker.end_request(500, error="Internal Server Error")

        assert result["status_code"] == 500
        assert result["error"] == "Internal Server Error"

    def test_end_request_without_start(self):
        """Test ending request without starting"""
        tracker = RequestTracker()

        result = tracker.end_request(200)

        assert result == {}

    def test_request_duration_tracking(self):
        """Test request duration measurement"""
        tracker = RequestTracker()

        tracker.start_request("req-3", "GET", "/slow")
        time.sleep(0.05)
        result = tracker.end_request(200)

        assert result["duration_ms"] >= 40  # At least 40ms with tolerance

    def test_request_log_history(self):
        """Test request log keeps history"""
        tracker = RequestTracker()

        for i in range(10):
            tracker.start_request(f"req-{i}", "GET", f"/api/{i}")
            tracker.end_request(200)

        assert len(tracker._request_log) == 10

    def test_request_log_max_size(self):
        """Test request log max size (1000)"""
        tracker = RequestTracker()

        for i in range(1100):
            tracker.start_request(f"req-{i}", "GET", "/api")
            tracker.end_request(200)

        assert len(tracker._request_log) <= 1000

    def test_get_request_id(self):
        """Test getting current request ID"""
        tracker = RequestTracker()

        assert tracker.get_request_id() is None

        tracker.start_request("my-req", "GET", "/test")
        assert tracker.get_request_id() == "my-req"

        tracker.end_request(200)
        assert tracker.get_request_id() is None

    def test_request_with_user_context(self):
        """Test request tracking with user context"""
        tracker = RequestTracker()

        tracker.start_request(
            "req-user", "GET", "/api/v1/profile",
            user_id="U12345", ip_address="192.168.1.1"
        )
        result = tracker.end_request(200)

        assert result["user_id"] == "U12345"
        assert result["ip_address"] == "192.168.1.1"

    def test_concurrent_requests(self):
        """Test tracking concurrent requests"""
        tracker = RequestTracker()
        results = []

        # Simulate overlapping requests (not truly concurrent in single tracker)
        tracker.start_request("req-a", "GET", "/a")
        tracker.start_request("req-b", "GET", "/b")  # Overwrites req-a
        result_b = tracker.end_request(200)

        assert result_b["path"] == "/b"


# ============================================
# HealthStatus Dataclass Tests
# ============================================

class TestHealthStatus:
    """HealthStatus data structure tests"""

    def test_health_status_creation(self):
        """Test creating HealthStatus"""
        status = HealthStatus(
            name="test",
            healthy=True,
            message="OK",
            latency_ms=1.5
        )

        assert status.name == "test"
        assert status.healthy is True
        assert status.latency_ms == 1.5

    def test_health_status_defaults(self):
        """Test HealthStatus default values"""
        status = HealthStatus(name="test", healthy=False)

        assert status.message == ""
        assert status.latency_ms == 0.0
        assert status.details == {}


# ============================================
# Integration Tests
# ============================================

class TestMonitoringIntegration:
    """Monitoring module integration tests"""

    def test_full_health_check_flow(self):
        """Test complete health check flow"""
        checker = HealthChecker()

        # Register multiple checks
        checker.register("database", lambda: {"healthy": True, "message": "Connected"})
        checker.register("cache", lambda: {"healthy": True, "message": "Redis OK"})
        checker.register("disk", lambda: {"healthy": True, "message": "Space OK"})

        # Check liveness
        liveness = checker.liveness()
        assert liveness["status"] == "alive"

        # Check readiness
        readiness = checker.readiness()
        assert readiness["status"] == "ready"
        assert len(readiness["checks"]) == 3

    def test_metrics_and_tracking_integration(self):
        """Test metrics and request tracking together"""
        metrics = PrometheusMetrics()
        tracker = RequestTracker()

        # Simulate request
        req_id = tracker.start_request("req-1", "GET", "/api/v1/forecast")
        metrics.counter("http_requests_total", labels={"method": "GET", "path": "/api/v1/forecast"})

        # Simulate processing
        time.sleep(0.01)

        # End request
        result = tracker.end_request(200)
        metrics.histogram("request_duration_seconds", result["duration_ms"] / 1000)

        # Verify metrics
        output = metrics.export()
        assert "http_requests_total" in output
        assert "request_duration_seconds" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
