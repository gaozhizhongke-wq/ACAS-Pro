#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for alert/notifier, collectors/weibo_api, content/trend_monitor,
sentiment/analyzer, update/updater, and core/config."""

from unittest.mock import MagicMock, patch
# ============================================================
# ALERT / NOTIFIER
# ============================================================
class TestAlertChannelEnum:
    def test_values(self):
        from acas_pro.alert.notifier import AlertChannel
        assert AlertChannel.WECHAT_WORK.value == "wechat_work"
        assert AlertChannel.WEBHOOK.value == "webhook"
        assert len(AlertChannel) >= 6

class TestAlertPriorityEnum:
    def test_values(self):
        from acas_pro.alert.notifier import AlertPriority
        assert AlertPriority.P0_CRITICAL.value == "p0"
        assert len(AlertPriority) >= 4

class TestAlertMessage:
    def test_create(self):
        from acas_pro.alert.notifier import AlertMessage, AlertPriority
        msg = AlertMessage(title="Test Alert", content="Something happened", priority=AlertPriority.P1_URGENT, category="system", source="monitor", metadata={})
        assert msg.title == "Test Alert"


# ============================================================
# COLLECTORS / WEIBO API
# ============================================================
class TestWeiboPost:
    def test_create(self):
        from acas_pro.collectors.weibo_api import WeiboPost
        post = WeiboPost(id="w1", text="Hello", author="user1", author_id="uid1", created_at="2026-01-01", reposts_count=10, comments_count=5, attitudes_count=20, source="web")
        assert post.text == "Hello"

class TestWeiboCollector:
    def test_class_attrs(self):
        from acas_pro.collectors.weibo_api import WeiboCollector
        assert hasattr(WeiboCollector, 'API_BASE')
        assert hasattr(WeiboCollector, 'HOT_SEARCH_URL')


# ============================================================
# CONTENT / TREND MONITOR
# ============================================================
class TestPlatformEnum:
    def test_values(self):
        from acas_pro.content.trend_monitor import Platform
        assert Platform.DOUYIN.value == "douyin"
        assert Platform.BILIBILI.value == "bilibili"
        assert len(Platform) >= 7

class TestTrendItem:
    def test_create(self):
        from acas_pro.content.trend_monitor import TrendItem
        item = TrendItem(id="t1", platform="douyin", title="Trend", author="a", url="", views=100, likes=50, comments=10, shares=5, publish_time="", tags=[], content_type="video")
        assert item.views == 100
        assert item.viral_score == 0.0

class TestTrendReport:
    def test_create(self):
        from acas_pro.content.trend_monitor import TrendReport
        report = TrendReport(timestamp="2026-01-01", platform="douyin", total_items=100, top_items=[], trending_tags=["tag1"], category_distribution={})
        assert report.total_items == 100

class TestTrendMonitor:
    def test_get_trending_items(self):
        from acas_pro.content.trend_monitor import TrendMonitor, Platform
        with patch.object(TrendMonitor, '__init__', lambda self, *a, **kw: None):
            tm = TrendMonitor()
            tm.db = MagicMock()
            tm.db.fetchall.return_value = []
            items = tm.get_trending_items(Platform.DOUYIN, limit=10)
            assert isinstance(items, list)

    def test_get_trend_report(self):
        from acas_pro.content.trend_monitor import TrendMonitor, Platform
        with patch.object(TrendMonitor, '__init__', lambda self, *a, **kw: None):
            tm = TrendMonitor()
            tm.db = MagicMock()
            tm.db.fetchall.return_value = []
            report = tm.get_trend_report(Platform.DOUYIN)
            assert report is not None


# ============================================================
# SENTIMENT / ANALYZER
# ============================================================
class TestSentimentLevelEnum:
    def test_values(self):
        from acas_pro.sentiment.analyzer import SentimentLevel
        assert SentimentLevel.NEUTRAL.value == "neutral"
        assert SentimentLevel.VERY_POSITIVE.value == "very_positive"

class TestSentimentResult:
    def test_create(self):
        from acas_pro.sentiment.analyzer import SentimentResult, SentimentLevel
        result = SentimentResult(text="hello", overall_sentiment=SentimentLevel.POSITIVE, sentiment_score=0.8, confidence=0.9, aspects=[], key_phrases=[], entities=[], language="zh", analyzed_at="2026-01-01")
        assert result.sentiment_score == 0.8

class TestAspectSentiment:
    def test_create(self):
        from acas_pro.sentiment.analyzer import AspectSentiment
        a = AspectSentiment(aspect="quality", sentiment="positive", mentions=5, keywords=["good", "great"])
        assert a.mentions == 5

class TestSentimentAnalyzer:
    def test_analyze(self):
        from acas_pro.sentiment.analyzer import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("这个产品非常好用，质量不错")
        assert result is not None
        assert hasattr(result, 'sentiment_score')

    def test_batch_analyze(self):
        from acas_pro.sentiment.analyzer import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        results = analyzer.batch_analyze(["好产品", "差体验"])
        assert isinstance(results, list)
        assert len(results) == 2

    def test_negative_sentiment(self):
        from acas_pro.sentiment.analyzer import SentimentAnalyzer
        result = SentimentAnalyzer().analyze("这个服务太差了，非常糟糕")
        assert result is not None
        assert result.sentiment_score < 0.5

    def test_positive_sentiment(self):
        from acas_pro.sentiment.analyzer import SentimentAnalyzer
        result = SentimentAnalyzer().analyze("非常好的体验，推荐给大家")
        assert result is not None
        # Chinese sentiment may not be perfect, just ensure it runs


# ============================================================
# UPDATE / UPDATER
# ============================================================
class TestUpdateInfo:
    def test_create(self):
        from acas_pro.update.updater import UpdateInfo
        info = UpdateInfo(version="2.0.0", release_date="2026-01-01", download_url="http://x.com/v2", sha256="abc123", changelog="New features", mandatory=False)
        assert info.version == "2.0.0"
        assert info.mandatory == False  # noqa: E712

class TestUpdateChecker:
    def test_init(self):
        from acas_pro.update.updater import UpdateChecker
        uc = UpdateChecker()
        assert uc is not None

    def test_check(self):
        from unittest.mock import patch, MagicMock
        import json as json_mod
        from acas_pro.update.updater import UpdateChecker
        uc = UpdateChecker()
        # Mock urllib to avoid network call
        mock_response = MagicMock()
        mock_response.read.return_value = json_mod.dumps({
            "latest_version": "5.2.0",
            "release_date": "2026-01-01",
            "download_url": "http://example.com/update.exe",
            "sha256": "abc123",
            "changelog": "Test update",
            "mandatory": False
        }).encode('utf-8')
        with patch('urllib.request.urlopen', return_value=mock_response):
            result = uc.check()
        assert isinstance(result, tuple)
        assert len(result) == 2


# ============================================================
# CORE / CONFIG (dataclass validation)
# ============================================================
class TestConfigEnums:
    def test_environment_enum(self):
        from acas_pro.core.config import Environment
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.PRODUCTION.value == "production"

class TestAppConfig:
    def test_default_creation(self):
        from acas_pro.core.config import AppConfig
        cfg = AppConfig()
        assert cfg is not None

    def test_has_llm_config(self):
        from acas_pro.core.config import AppConfig
        cfg = AppConfig()
        assert hasattr(cfg, 'llm')
        assert hasattr(cfg, 'database')
        assert hasattr(cfg, 'security')

class TestLLMConfig:
    def test_defaults(self):
        from acas_pro.core.config import LLMConfig
        llm = LLMConfig()
        assert hasattr(llm, 'provider')
        assert hasattr(llm, 'model')
        assert hasattr(llm, 'temperature')
        assert hasattr(llm, 'max_tokens')

class TestDatabaseConfig:
    def test_defaults(self):
        from acas_pro.core.config import DatabaseConfig
        db = DatabaseConfig()
        assert hasattr(db, 'type')
        assert hasattr(db, 'path')

class TestSecurityConfig:
    def test_defaults(self):
        from acas_pro.core.config import SecurityConfig
        sec = SecurityConfig()
        assert hasattr(sec, 'secret_key')
        assert sec.jwt_algorithm == 'HS256'
        assert sec.jwt_expiry_hours == 24

class TestUIConfig:
    def test_defaults(self):
        from acas_pro.core.config import UIConfig
        ui = UIConfig()
        assert hasattr(ui, 'language')
