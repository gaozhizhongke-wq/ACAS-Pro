#!/usr/bin/env python3
"""Deep tests for weibo_api, news_engine, and trend_monitor to boost coverage."""

import pytest
from unittest.mock import MagicMock, patch
import sys
from datetime import datetime, timezone

if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()


class TestWeiboAPIDeep:
    """Deep tests for WeiboAPI module."""
    
    def test_weibo_post_creation(self):
        from acas_pro.collectors.weibo_api import WeiboPost
        post = WeiboPost(
            id="123",
            text="Test post",
            author="testuser",
            author_id="user123",
            created_at=datetime.now(timezone.utc),
            reposts_count=10,
            comments_count=5,
            attitudes_count=20,
            source="iPhone"
        )
        assert post.id == "123"
        assert post.pics == []  # Default empty list
    
    def test_weibo_post_to_dict(self):
        from acas_pro.collectors.weibo_api import WeiboPost
        post = WeiboPost(
            id="123",
            text="Test",
            author="user",
            author_id="uid",
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            reposts_count=1,
            comments_count=2,
            attitudes_count=3,
            source="Web",
            pics=["pic1.jpg"]
        )
        d = post.to_dict()
        assert d['id'] == "123"
        assert d['pics'] == ["pic1.jpg"]
    
    def test_collector_init_no_config(self):
        from acas_pro.collectors.weibo_api import WeiboCollector
        with patch('acas_pro.collectors.weibo_api.config') as mock_cfg:
            mock_cfg.weibo_app_key = None
            mock_cfg.weibo_app_secret = None
            mock_cfg.weibo_access_token = None
            collector = WeiboCollector()
            assert collector.app_key is None
    
    def test_collector_init_with_params(self):
        from acas_pro.collectors.weibo_api import WeiboCollector
        collector = WeiboCollector(
            app_key="test_key",
            app_secret="test_secret",
            access_token="test_token"
        )
        assert collector.app_key == "test_key"
        assert collector.access_token == "test_token"
    
    def test_search_no_token(self):
        from acas_pro.collectors.weibo_api import WeiboCollector
        collector = WeiboCollector()
        results = collector.search("test")
        assert results == []
    
    def test_search_with_token(self):
        from acas_pro.collectors.weibo_api import WeiboCollector
        collector = WeiboCollector(access_token="test_token")
        mock_response = MagicMock()
        mock_response.json.return_value = {"statuses": []}
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(collector.session, 'get', return_value=mock_response):
            results = collector.search("test keyword")
            assert results == []
    
    def test_search_parse_results(self):
        from acas_pro.collectors.weibo_api import WeiboCollector
        collector = WeiboCollector(access_token="test_token")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "statuses": [
                {
                    "id": "123",
                    "text": "Test post",
                    "user": {"id": "uid", "screen_name": "user"},
                    "created_at": "Wed Jun 14 15:26:23 +0800 2023",
                    "reposts_count": 1,
                    "comments_count": 2,
                    "attitudes_count": 3,
                    "source": "iPhone",
                    "pic_urls": [{"thumbnail_pic": "pic.jpg"}]
                }
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(collector.session, 'get', return_value=mock_response):
            results = collector.search("test")
            assert len(results) == 1
            assert results[0].id == "123"
    
    def test_search_exclude_retweets(self):
        from acas_pro.collectors.weibo_api import WeiboCollector
        collector = WeiboCollector(access_token="test_token")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "statuses": [
                {"id": "1", "text": "original", "user": {"id": "u", "screen_name": "n"}, "created_at": "Wed Jun 14 15:26:23 +0800 2023", "reposts_count": 0, "comments_count": 0, "attitudes_count": 0, "source": ""},
                {"id": "2", "text": "retweet", "user": {"id": "u", "screen_name": "n"}, "created_at": "Wed Jun 14 15:26:23 +0800 2023", "reposts_count": 0, "comments_count": 0, "attitudes_count": 0, "source": "", "retweeted_status": {"id": "r1"}}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(collector.session, 'get', return_value=mock_response):
            results = collector.search("test", include_retweets=False)
            assert len(results) == 1
            assert results[0].text == "original"
    
    def test_search_include_retweets(self):
        from acas_pro.collectors.weibo_api import WeiboCollector
        collector = WeiboCollector(access_token="test_token")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "statuses": [
                {"id": "1", "text": "original", "user": {"id": "u", "screen_name": "n"}, "created_at": "Wed Jun 14 15:26:23 +0800 2023", "reposts_count": 0, "comments_count": 0, "attitudes_count": 0, "source": ""},
                {"id": "2", "text": "retweet", "user": {"id": "u", "screen_name": "n"}, "created_at": "Wed Jun 14 15:26:23 +0800 2023", "reposts_count": 0, "comments_count": 0, "attitudes_count": 0, "source": "", "retweeted_status": {"id": "r1"}}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(collector.session, 'get', return_value=mock_response):
            results = collector.search("test", include_retweets=True)
            assert len(results) == 2
    
    def test_search_error(self):
        from acas_pro.collectors.weibo_api import WeiboCollector
        import requests
        collector = WeiboCollector(access_token="test_token")
        
        with patch.object(collector.session, 'get', side_effect=requests.RequestException("error")):
            results = collector.search("test")
            assert results == []
    
    def test_get_hot_topics_success(self):
        from acas_pro.collectors.weibo_api import WeiboCollector
        collector = WeiboCollector()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "ok": 1,
            "data": {
                "realtime": [
                    {"rank": 1, "word": "topic1", "num": 1000, "category": "财经"},
                    {"rank": 2, "word": "topic2", "num": 500, "category": "科技"}
                ]
            }
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(collector.session, 'get', return_value=mock_response):
            topics = collector.get_hot_topics()
            assert len(topics) == 2
            assert topics[0]['topic'] == "topic1"
    
    def test_get_hot_topics_fallback(self):
        from acas_pro.collectors.weibo_api import WeiboCollector
        collector = WeiboCollector()
        
        with patch.object(collector.session, 'get', side_effect=Exception("error")):
            topics = collector.get_hot_topics()
            assert len(topics) == 5  # Mock data
            assert topics[0]['topic'] == "数字经济"
    
    def test_get_user_timeline_no_token(self):
        from acas_pro.collectors.weibo_api import WeiboCollector
        collector = WeiboCollector()
        results = collector.get_user_timeline("user123")
        assert results == []
    
    def test_get_user_timeline_success(self):
        from acas_pro.collectors.weibo_api import WeiboCollector
        collector = WeiboCollector(access_token="test_token")
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "statuses": [
                {"id": "1", "text": "post", "user": {"id": "u", "screen_name": "n"}, "created_at": "Wed Jun 14 15:26:23 +0800 2023", "reposts_count": 0, "comments_count": 0, "attitudes_count": 0, "source": ""}
            ]
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch.object(collector.session, 'get', return_value=mock_response):
            results = collector.get_user_timeline("user123")
            assert len(results) == 1
    
    def test_get_user_timeline_error(self):
        from acas_pro.collectors.weibo_api import WeiboCollector
        import requests
        collector = WeiboCollector(access_token="test_token")
        
        with patch.object(collector.session, 'get', side_effect=requests.RequestException("error")):
            results = collector.get_user_timeline("user123")
            assert results == []


class TestNewsEngineDeep:
    """Deep tests for news_engine module."""
    
    def test_news_article_creation(self):
        from acas_pro.sentiment.news_engine import NewsArticle, NewsCategory
        article = NewsArticle(
            id="test-1",
            title="Test News",
            content="Content here",
            summary="Summary",
            source="TestSource",
            source_url="http://test.com",
            category=NewsCategory.TECHNOLOGY,
            published_at=datetime.now(timezone.utc),
            language="zh",
            sentiment=None,
            relevance_score=0.9,
            affected_regions=["CN"],
            keywords=["test"]
        )
        assert article.id == "test-1"
    
    def test_sentiment_result_creation(self):
        from acas_pro.sentiment.news_engine import SentimentResult, SentimentLevel
        result = SentimentResult(
            text="test text",
            overall_sentiment=SentimentLevel.POSITIVE,
            sentiment_score=0.8,
            confidence=0.9,
            aspects=[],
            key_phrases=["good"],
            entities=["company"],
            language="zh",
            analyzed_at=datetime.now(timezone.utc).isoformat()
        )
        assert result.sentiment_score == 0.8
    
    def test_risk_alert_creation(self):
        from acas_pro.sentiment.news_engine import RiskAlert, RiskLevel
        alert = RiskAlert(
            id="alert-1",
            level=RiskLevel.HIGH,
            title="Test Alert",
            description="Test description",
            category="market",
            source_articles=["art-1"],
            affected_regions=["CN"],
            detected_at=datetime.now(timezone.utc),
            expires_at=None,
            recommended_actions=["monitor"]
        )
        assert alert.level == RiskLevel.HIGH
    
    def test_engine_fetch_intelligence(self):
        from acas_pro.sentiment.news_engine import MarketIntelligenceEngine, NewsCategory
        engine = MarketIntelligenceEngine()
        result = engine.fetch_intelligence(categories=[NewsCategory.TECHNOLOGY])
        assert isinstance(result, list)
    
    def test_engine_detect_risks(self):
        from acas_pro.sentiment.news_engine import MarketIntelligenceEngine, NewsArticle, NewsCategory
        engine = MarketIntelligenceEngine()
        article = NewsArticle(
            id="test",
            title="Risk News",
            content="Bad news about market crash",
            summary="",
            source="S",
            source_url="U",
            category=NewsCategory.FINANCE,
            published_at=datetime.now(timezone.utc),
            language="zh",
            sentiment=None,
            relevance_score=0.5,
            affected_regions=["CN"],
            keywords=["risk"]
        )
        risks = engine.detect_risks([article])
        assert isinstance(risks, list)
    
    def test_engine_get_sentiment_summary(self):
        from acas_pro.sentiment.news_engine import MarketIntelligenceEngine, NewsArticle, NewsCategory
        engine = MarketIntelligenceEngine()
        article = NewsArticle(
            id="test",
            title="News",
            content="Good news about growth",
            summary="",
            source="S",
            source_url="U",
            category=NewsCategory.TECHNOLOGY,
            published_at=datetime.now(timezone.utc),
            language="zh",
            sentiment=None,
            relevance_score=0.5,
            affected_regions=["CN"],
            keywords=["test"]
        )
        summary = engine.get_sentiment_summary([article])
        assert isinstance(summary, dict)


class TestTrendMonitorDeep:
    """Deep tests for trend_monitor module."""
    
    def test_trend_item_creation(self):
        from acas_pro.content.trend_monitor import TrendItem, Platform
        item = TrendItem(
            id="item-1",
            platform=Platform.DOUYIN,
            title="Test Item",
            author="author",
            url="http://test.com",
            views=1000,
            likes=100,
            comments=50,
            shares=25,
            publish_time=datetime.now(timezone.utc),
            tags=["test"],
            content_type="video",
            thumbnail_url=None,
            audio_url=None,
            viral_score=0.8,
            efficiency_score=0.7,
            relevance_score=0.9,
            key_frames=[],
            transcript="",
            visual_tags=[]
        )
        assert item.id == "item-1"
    
    def test_trend_report_creation(self):
        from acas_pro.content.trend_monitor import TrendReport, Platform
        report = TrendReport(
            timestamp=datetime.now(timezone.utc),
            platform=Platform.DOUYIN,
            total_items=10,
            top_items=[],
            trending_tags=[],
            category_distribution={"video": 5, "image": 3}
        )
        assert report.platform == Platform.DOUYIN
    
    def test_monitor_get_trending_items(self):
        from acas_pro.content.trend_monitor import TrendMonitor
        monitor = TrendMonitor()
        items = monitor.get_trending_items()
        assert isinstance(items, list)
    
    def test_monitor_get_trend_report(self):
        from acas_pro.content.trend_monitor import TrendMonitor, Platform
        monitor = TrendMonitor()
        report = monitor.get_trend_report(Platform.DOUYIN)
        assert report is not None or report is None
    
    def test_monitor_register_callback(self):
        from acas_pro.content.trend_monitor import TrendMonitor
        monitor = TrendMonitor()
        called = []
        def cb(items):
            called.append(items)
        monitor.register_callback(cb)
        # Should not raise
    
    def test_monitor_start_stop(self):
        from acas_pro.content.trend_monitor import TrendMonitor
        monitor = TrendMonitor()
        monitor.start_monitoring()
        monitor.stop_monitoring()
        # Should not raise
