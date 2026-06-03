# -*- coding: utf-8 -*-
"""Tests for rss_collector.py"""

import sys
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

sys.modules['feedparser'] = MagicMock()

import pytest
from acas_pro.collectors.rss_collector import RSSArticle, RSSCollector


class TestRSSArticle:
    def test_post_init(self):
        article = RSSArticle(
            title="Test", content="Content", summary="Summary",
            source="Source", source_url="http://example.com",
            published_at=datetime.now()
        )
        assert article.tags == []

    def test_to_dict(self):
        article = RSSArticle(
            title="Test", content="Content", summary="Summary",
            source="Source", source_url="http://example.com",
            published_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            language="zh", tags=["tag1"]
        )
        data = article.to_dict()
        assert data['title'] == "Test"
        assert data['language'] == "zh"
        assert data['tags'] == ["tag1"]


class TestRSSCollector:
    def test_init_default(self):
        rc = RSSCollector()
        assert len(rc.sources) > 0
        assert rc.timeout == 30

    def test_init_custom(self):
        rc = RSSCollector(custom_sources={"custom": "http://custom.com"}, timeout=60)
        assert "custom" in rc.sources
        assert rc.timeout == 60

    def test_add_source(self):
        rc = RSSCollector()
        rc.add_source("new", "http://new.com")
        assert rc.sources["new"] == "http://new.com"

    def test_get_available_sources(self):
        rc = RSSCollector()
        sources = rc.get_available_sources()
        assert isinstance(sources, list)
        assert len(sources) > 0

    def test_collect_empty_sources(self):
        rc = RSSCollector()
        result = rc.collect(sources=[])
        assert isinstance(result, list)

    def test_fetch_feed(self):
        rc = RSSCollector()
        
        mock_feed = MagicMock()
        mock_feed.feed = {'title': 'Test Feed'}
        mock_feed.bozo = False
        
        # Create a proper mock entry that behaves like a dict for .get()
        mock_entry = {
            'title': 'Test Article',
            'summary': 'Summary',
            'description': 'Desc',
            'link': 'http://link.com',
            'published_parsed': (2026, 1, 1, 0, 0, 0),
            'tags': [MagicMock(term="tech")],
            'category': None,
            'content': None
        }
        mock_feed.entries = [mock_entry]
        
        # Mock the feedparser module itself (conftest mocks it globally)
        import acas_pro.collectors.rss_collector as rss_mod
        with patch.object(rss_mod, 'feedparser') as mock_fp:
            mock_fp.parse.return_value = mock_feed
            result = rc._fetch_feed("test", "http://test.com")
        
        assert len(result) == 1
        assert result[0].title == "Test Article"

    def test_fetch_feed_bozo(self):
        rc = RSSCollector()
        
        mock_feed = MagicMock()
        mock_feed.feed = {'title': 'Test'}
        mock_feed.bozo = True
        mock_feed.bozo_exception = "Parse error"
        mock_feed.entries = []
        
        with patch('acas_pro.collectors.rss_collector.feedparser.parse', return_value=mock_feed):
            result = rc._fetch_feed("test", "http://test.com")
        
        assert len(result) == 0

    def test_fetch_feed_exception(self):
        rc = RSSCollector()
        with patch('acas_pro.collectors.rss_collector.feedparser.parse', side_effect=Exception("Network error")):
            result = rc._fetch_feed("test", "http://test.com")
        assert len(result) == 0

    def test_parse_time_published(self):
        rc = RSSCollector()
        entry = MagicMock()
        entry.published_parsed = (2026, 5, 20, 10, 0, 0)
        entry.updated_parsed = None
        result = rc._parse_time(entry)
        assert result.year == 2026

    def test_parse_time_updated(self):
        rc = RSSCollector()
        entry = MagicMock()
        entry.published_parsed = None
        entry.updated_parsed = (2026, 5, 20, 10, 0, 0)
        result = rc._parse_time(entry)
        assert result.year == 2026

    def test_parse_time_fallback(self):
        rc = RSSCollector()
        entry = MagicMock()
        entry.published_parsed = None
        entry.updated_parsed = None
        result = rc._parse_time(entry)
        assert isinstance(result, datetime)

    def test_detect_language_chinese(self):
        rc = RSSCollector()
        result = rc._detect_language("这是一段中文文本")
        assert result == "zh"

    def test_detect_language_english(self):
        rc = RSSCollector()
        result = rc._detect_language("This is English text")
        assert result == "en"

    def test_detect_language_empty(self):
        rc = RSSCollector()
        result = rc._detect_language("")
        assert result == "zh"

    def test_clean_content(self):
        rc = RSSCollector()
        result = rc._clean_content("<p>Hello  World</p>")
        assert result == "Hello World"

    def test_extract_tags(self):
        rc = RSSCollector()
        entry = MagicMock()
        entry.tags = [MagicMock(term="tech"), MagicMock(term="AI")]
        entry.category = "news"
        result = rc._extract_tags(entry)
        assert "tech" in result
        assert "news" in result

    def test_extract_tags_no_tags(self):
        rc = RSSCollector()
        entry = MagicMock()
        entry.tags = None
        entry.category = None
        result = rc._extract_tags(entry)
        assert result == []

    def test_deduplicate(self):
        rc = RSSCollector()
        a1 = RSSArticle(title="Test", content="C", summary="S", source="Src", source_url="http://1.com", published_at=datetime.now())
        a2 = RSSArticle(title="Test", content="C2", summary="S2", source="Src2", source_url="http://2.com", published_at=datetime.now())
        a3 = RSSArticle(title="Different", content="C", summary="S", source="Src", source_url="http://3.com", published_at=datetime.now())
        result = rc._deduplicate([a1, a2, a3])
        assert len(result) == 2

    def test_similarity_identical(self):
        rc = RSSCollector()
        result = rc._similarity("hello", "hello")
        assert result == 1.0

    def test_similarity_different(self):
        rc = RSSCollector()
        result = rc._similarity("abc", "xyz")
        assert result < 0.5

    def test_similarity_empty(self):
        rc = RSSCollector()
        result = rc._similarity("", "test")
        assert result == 0.0
