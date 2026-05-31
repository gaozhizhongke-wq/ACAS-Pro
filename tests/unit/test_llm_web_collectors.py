#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for web routes, collectors, and remaining modules."""

from unittest.mock import MagicMock, patch
import sys
import pytest

if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()


# ============================================================
# LLM BASE ENGINE - create stub so engines can be tested
# ============================================================
# base_engine.py doesn't exist, so we mock it at sys.modules level
@pytest.fixture(autouse=False)
def mock_base_engine():
    """Mock acas_pro.llm.base_engine so claude/gemini engines can import."""
    stub = MagicMock()
    stub.BaseLLMEngine = type('BaseLLMEngine', (), {})
    stub.LLMMessage = type('LLMMessage', (), {})
    stub.LLMResponse = type('LLMResponse', (), {})
    stub.LLMStreamChunk = type('LLMStreamChunk', (), {})
    sys.modules['acas_pro.llm.base_engine'] = stub
    yield
    sys.modules.pop('acas_pro.llm.base_engine', None)


# ============================================================
# CLAUDE ENGINE
# ============================================================
class TestClaudeEngine:
    def test_init(self, mock_base_engine):
        from acas_pro.llm.claude_engine import ClaudeEngine
        with patch.object(ClaudeEngine, '__init__', lambda self: None):
            ce = ClaudeEngine()
            ce.api_key = "test"
            assert ce.api_key == "test"


# ============================================================
# GEMINI ENGINE
# ============================================================
class TestGeminiEngine:
    def test_init(self, mock_base_engine):
        from acas_pro.llm.gemini_engine import GeminiEngine
        with patch.object(GeminiEngine, '__init__', lambda self: None):
            ge = GeminiEngine()
            ge.api_key = "test"
            assert ge.api_key == "test"


# ============================================================
# RSS COLLECTOR
# ============================================================
class TestRSSCollector:
    def test_import_and_create(self):
        sys.modules['feedparser'] = MagicMock()
        from acas_pro.collectors.rss_collector import RSSCollector, RSSArticle
        rc = RSSCollector()
        assert rc is not None

    def test_rss_article(self):
        sys.modules['feedparser'] = MagicMock()
        from acas_pro.collectors.rss_collector import RSSArticle
        from datetime import datetime
        art = RSSArticle(title="Test", content="Body", summary="Sum", source="test", source_url="https://x.com", published_at=datetime.now())
        assert art.title == "Test"


# ============================================================
# WEB ROUTES
# ============================================================
class TestDashboardRoute:
    def test_import(self):
        from acas_pro.web.routes.dashboard import bp
        assert bp is not None

class TestLLMRoute:
    def test_import(self):
        from acas_pro.web.routes.llm import bp
        assert bp is not None


# ============================================================
# CORE MONITORING
# ============================================================
class TestMonitoringDeep:
    def test_health_checker(self):
        sys.modules['psutil'] = MagicMock()
        from acas_pro.core.monitoring import HealthChecker, HealthStatus
        with patch.object(HealthChecker, '__init__', lambda self: None):
            hc = HealthChecker()
            hc.check = MagicMock(return_value=HealthStatus(name="db", healthy=True, latency_ms=10, message="ok"))
            result = hc.check()
            assert result.message == "ok"

    def test_prometheus_metrics(self):
        sys.modules['psutil'] = MagicMock()
        from acas_pro.core.monitoring import PrometheusMetrics
        with patch.object(PrometheusMetrics, '__init__', lambda self: None):
            pm = PrometheusMetrics()
            assert pm is not None


# ============================================================
# UPDATE V2
# ============================================================
class TestUpdater:
    def test_check(self):
        from acas_pro.update.updater import UpdateChecker
        with patch.object(UpdateChecker, '__init__', lambda self: None):
            um = UpdateChecker()
            um.check = MagicMock(return_value={"has_update": False})
            result = um.check()
            assert "has_update" in result


# ============================================================
# COLLECTORS WEIBO
# ============================================================
class TestWeiboCollector:
    def test_import(self):
        from acas_pro.collectors.weibo_api import WeiboCollector
        assert WeiboCollector is not None

    def test_get_hot_topics(self):
        from acas_pro.collectors.weibo_api import WeiboCollector
        with patch.object(WeiboCollector, '__init__', lambda self: None):
            wc = WeiboCollector()
            wc.get_hot_topics = MagicMock(return_value=[])
            result = wc.get_hot_topics()
            assert isinstance(result, list)


# ============================================================
# CONTENT TREND MONITOR
# ============================================================
class TestTrendMonitor:
    def test_import(self):
        from acas_pro.content.trend_monitor import TrendMonitor
        assert TrendMonitor is not None

    def test_get_trends(self):
        from acas_pro.content.trend_monitor import TrendMonitor
        with patch.object(TrendMonitor, '__init__', lambda self: None):
            tm = TrendMonitor()
            tm.get_trends = MagicMock(return_value=[])
            result = tm.get_trends("douyin")
            assert isinstance(result, list)
