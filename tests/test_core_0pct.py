"""Tests for core/monitoring.py (177 stmts, 0%) with proper dependency mocks."""
import sys
from unittest.mock import MagicMock, patch
import pytest


def _setup_monitoring_env():
    """Set up mocks needed for monitoring module import."""
    patches = []

    # Mock config
    mock_config = MagicMock()
    mock_config.version = "1.0.0"
    patches.append(patch('acas_pro.core.config.get_config', return_value=mock_config))
    patches.append(patch('acas_pro.core.config.config', mock_config))

    # Mock logging
    mock_logger = MagicMock()
    patches.append(patch('acas_pro.core.logging.get_logger', return_value=mock_logger))

    # Clear module cache so monitoring reimports fresh
    mods_to_clear = ['acas_pro.core.monitoring']
    for m in list(sys.modules.keys()):
        if 'acas_pro.core.monitoring' in m:
            mods_to_clear.append(m)
    saved = {}
    for m in mods_to_clear:
        if m in sys.modules:
            saved[m] = sys.modules.pop(m)

    for p in patches:
        p.start()

    return patches, saved


def _teardown(patches, saved):
    for p in patches:
        p.stop()
    sys.modules.update(saved)


class TestHealthStatus:
    def test_creation(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import HealthStatus
            hs = HealthStatus(name="test", healthy=True)
            assert hs.name == "test"
            assert hs.healthy is True
            assert hs.message == ""
            assert hs.latency_ms == 0.0
            assert hs.details == {}
        finally:
            _teardown(patches, saved)

    def test_with_params(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import HealthStatus
            hs = HealthStatus(name="x", healthy=False, message="bad", latency_ms=50.0, details={"k": "v"})
            assert hs.message == "bad"
            assert hs.details == {"k": "v"}
        finally:
            _teardown(patches, saved)


class TestHealthChecker:
    def test_register_and_check_bool(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import HealthChecker
            hc = HealthChecker()
            hc.register("test", lambda: True)
            result = hc.check("test")
            assert result.healthy is True
        finally:
            _teardown(patches, saved)

    def test_check_dict_result(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import HealthChecker
            hc = HealthChecker()
            hc.register("d", lambda: {"healthy": True, "message": "ok", "details": {"x": 1}})
            result = hc.check("d")
            assert result.healthy is True
            assert result.message == "ok"
            assert result.details == {"x": 1}
        finally:
            _teardown(patches, saved)

    def test_check_not_found(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import HealthChecker
            hc = HealthChecker()
            result = hc.check("missing")
            assert result.healthy is False
            assert "not found" in result.message
        finally:
            _teardown(patches, saved)

    def test_check_exception(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import HealthChecker
            hc = HealthChecker()
            hc.register("err", lambda: 1/0)
            result = hc.check("err")
            assert result.healthy is False
        finally:
            _teardown(patches, saved)

    def test_check_invalid_type(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import HealthChecker
            hc = HealthChecker()
            hc.register("str", lambda: "wrong")
            result = hc.check("str")
            assert result.healthy is False
            assert "Invalid" in result.message
        finally:
            _teardown(patches, saved)

    def test_check_all(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import HealthChecker
            hc = HealthChecker()
            hc.register("c1", lambda: True)
            hc.register("c2", lambda: {"healthy": False})
            results = hc.check()
            assert "c1" in results
            assert results["c2"].healthy is False
        finally:
            _teardown(patches, saved)

    def test_liveness(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import HealthChecker
            hc = HealthChecker()
            result = hc.liveness()
            assert result["status"] == "alive"
            assert "version" in result
            assert "timestamp" in result
        finally:
            _teardown(patches, saved)

    def test_readiness_all_ok(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import HealthChecker
            hc = HealthChecker()
            hc.register("database", lambda: True)
            hc.register("cache", lambda: True)
            result = hc.readiness()
            assert result["status"] == "ready"
        finally:
            _teardown(patches, saved)

    def test_readiness_not_ready(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import HealthChecker
            hc = HealthChecker()
            hc.register("database", lambda: False)
            hc.register("cache", lambda: True)
            result = hc.readiness()
            assert result["status"] == "not_ready"
        finally:
            _teardown(patches, saved)


class TestPrometheusMetrics:
    def test_counter(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import PrometheusMetrics
            pm = PrometheusMetrics("test")
            pm.counter("req", 5)
            pm.counter("req", 3)
            assert pm._counters["req"] == 8
        finally:
            _teardown(patches, saved)

    def test_counter_with_labels(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import PrometheusMetrics
            pm = PrometheusMetrics()
            pm.counter("req", 1, {"method": "GET", "path": "/"})
            assert 1 in [v for v in pm._counters.values()]
        finally:
            _teardown(patches, saved)

    def test_gauge(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import PrometheusMetrics
            pm = PrometheusMetrics()
            pm.gauge("mem", 1024.5)
            assert pm._gauges["mem"] == 1024.5
        finally:
            _teardown(patches, saved)

    def test_histogram(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import PrometheusMetrics
            pm = PrometheusMetrics()
            for i in range(100):
                pm.histogram("lat", float(i))
            assert len(pm._histograms["lat"]) == 100
        finally:
            _teardown(patches, saved)

    def test_histogram_trimming(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import PrometheusMetrics
            pm = PrometheusMetrics()
            for i in range(1500):
                pm.histogram("h", float(i))
            assert len(pm._histograms["h"]) == 1000
        finally:
            _teardown(patches, saved)

    def test_make_key_no_labels(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import PrometheusMetrics
            pm = PrometheusMetrics()
            assert pm._make_key("test") == "test"
        finally:
            _teardown(patches, saved)

    def test_make_key_with_labels(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import PrometheusMetrics
            pm = PrometheusMetrics()
            key = pm._make_key("test", {"a": "1", "b": "2"})
            assert 'a="1"' in key
            assert 'b="2"' in key
        finally:
            _teardown(patches, saved)

    def test_export_counters(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import PrometheusMetrics
            pm = PrometheusMetrics("ns")
            pm.counter("req", 10)
            exp = pm.export()
            assert "counter" in exp
            assert "ns_req" in exp
        finally:
            _teardown(patches, saved)

    def test_export_gauges(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import PrometheusMetrics
            pm = PrometheusMetrics("ns")
            pm.gauge("mem", 512)
            exp = pm.export()
            assert "gauge" in exp
            assert "ns_mem" in exp
        finally:
            _teardown(patches, saved)

    def test_export_histogram(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import PrometheusMetrics
            pm = PrometheusMetrics("ns")
            for v in [0.1, 0.5, 1.0, 2.0, 5.0]:
                pm.histogram("lat", v)
            exp = pm.export()
            assert "summary" in exp
            assert "quantile" in exp
        finally:
            _teardown(patches, saved)

    def test_export_empty(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import PrometheusMetrics
            pm = PrometheusMetrics()
            exp = pm.export()
            assert isinstance(exp, str)
        finally:
            _teardown(patches, saved)

    def test_collect_system_metrics(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import PrometheusMetrics
            pm = PrometheusMetrics()
            pm.collect_system_metrics()
            assert len(pm._gauges) > 0
        finally:
            _teardown(patches, saved)


class TestRequestTracker:
    def test_start_auto_id(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import RequestTracker
            rt = RequestTracker()
            rid = rt.start_request("", "GET", "/api")
            assert rid is not None
            assert rt.get_request_id() == rid
        finally:
            _teardown(patches, saved)

    def test_start_with_id(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import RequestTracker
            rt = RequestTracker()
            rid = rt.start_request("myid", "POST", "/api")
            assert rid == "myid"
        finally:
            _teardown(patches, saved)

    def test_end_request(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import RequestTracker
            rt = RequestTracker()
            rt.start_request("r1", "GET", "/api")
            result = rt.end_request(200)
            assert result["status_code"] == 200
            assert result["request_id"] == "r1"
            assert "duration_ms" in result
        finally:
            _teardown(patches, saved)

    def test_end_with_error(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import RequestTracker
            rt = RequestTracker()
            rt.start_request("r2", "POST", "/api")
            result = rt.end_request(500, error="fail")
            assert result["error"] == "fail"
        finally:
            _teardown(patches, saved)

    def test_end_without_start(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import RequestTracker
            rt = RequestTracker()
            assert rt.end_request(200) == {}
        finally:
            _teardown(patches, saved)

    def test_get_id_none(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import RequestTracker
            rt = RequestTracker()
            assert rt.get_request_id() is None
        finally:
            _teardown(patches, saved)

    def test_log_keeps_1000(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import RequestTracker
            rt = RequestTracker()
            for i in range(1100):
                rt.start_request(f"r{i}", "GET", "/")
                rt.end_request(200)
            assert len(rt._request_log) == 1000
        finally:
            _teardown(patches, saved)


class TestDefaultHealthChecks:
    def test_check_cache(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import _check_cache
            result = _check_cache()
            assert result["healthy"] is True
        finally:
            _teardown(patches, saved)

    def test_check_disk_space(self):
        patches, saved = _setup_monitoring_env()
        try:
            from acas_pro.core.monitoring import _check_disk_space
            result = _check_disk_space()
            assert isinstance(result, dict)
            assert "healthy" in result
        finally:
            _teardown(patches, saved)
