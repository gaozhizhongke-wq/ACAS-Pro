#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - RSS Collector Tests
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, MagicMock

from acas_pro.collectors.rss_collector import RSSCollector, RSSArticle


class TestRSSArticle:
    """RSS article tests"""
    
    def test_article_creation(self):
        """Test article creation"""
        article = RSSArticle(
            title="Test Title",
            content="Test content here",
            summary="Test summary",
            source="Test Source",
            source_url="https://example.com/article",
            published_at=datetime.now(timezone.utc)
        )
        
        assert article.title == "Test Title"
        assert article.language == "zh"  # default
        assert article.tags == []  # default
    
    def test_article_to_dict(self):
        """Test article to dict"""
        now = datetime.now(timezone.utc)
        article = RSSArticle(
            title="Test",
            content="Content",
            summary="Summary",
            source="Source",
            source_url="https://example.com",
            published_at=now,
            tags=["tag1", "tag2"]
        )
        
        data = article.to_dict()
        assert data['title'] == "Test"
        assert data['language'] == "zh"
        assert len(data['tags']) == 2


class TestRSSCollector:
    """RSS collector tests"""
    
    @pytest.fixture
    def collector(self):
        return RSSCollector()
    
    def test_init(self, collector):
        """Test initialization"""
        assert len(collector.sources) > 0
        assert collector.timeout == 30
        assert "sina_finance" in collector.sources
    
    def test_default_sources_exist(self, collector):
        """Test default sources exist"""
        assert "sina_finance" in collector.DEFAULT_SOURCES
        assert "36kr" in collector.DEFAULT_SOURCES
        assert "people" in collector.DEFAULT_SOURCES
    
    def test_international_sources_exist(self, collector):
        """Test international sources exist"""
        assert "reuters_business" in collector.INTERNATIONAL_SOURCES
        assert "bbc_business" in collector.INTERNATIONAL_SOURCES
    
    def test_add_source(self, collector):
        """Test add source"""
        collector.add_source("custom", "https://custom.com/rss")
        assert "custom" in collector.sources
        assert collector.sources["custom"] == "https://custom.com/rss"
    
    def test_get_available_sources(self, collector):
        """Test get available sources"""
        sources = collector.get_available_sources()
        assert "sina_finance" in sources
        assert "36kr" in sources
    
    def test_detect_language_chinese(self, collector):
        """Test detect Chinese language"""
        lang = collector._detect_language("这是一段中文文本")
        assert lang == "zh"
    
    def test_detect_language_english(self, collector):
        """Test detect English language"""
        lang = collector._detect_language("This is English text")
        assert lang == "en"
    
    def test_clean_content(self, collector):
        """Test clean content"""
        html = "<p>This is <b>bold</b> text</p>"
        cleaned = collector._clean_content(html)
        assert "<p>" not in cleaned
        assert "<b>" not in cleaned
        assert "bold" in cleaned
    
    def test_similarity_identical(self, collector):
        """Test similarity with identical strings"""
        sim = collector._similarity("hello world", "hello world")
        assert sim == 1.0
    
    def test_similarity_different(self, collector):
        """Test similarity with different strings"""
        sim = collector._similarity("abc", "xyz")
        assert sim < 0.5
    
    def test_similarity_empty(self, collector):
        """Test similarity with empty strings"""
        sim = collector._similarity("", "test")
        assert sim == 0.0
    
    def test_deduplicate(self, collector):
        """Test deduplicate articles"""
        now = datetime.now(timezone.utc)
        articles = [
            RSSArticle("Title A", "Content", "Summary", "Source", "url1", now),
            RSSArticle("Title B", "Content", "Summary", "Source", "url2", now),
            RSSArticle("Title A", "Content", "Summary", "Source", "url3", now),  # duplicate
        ]
        
        unique = collector._deduplicate(articles)
        assert len(unique) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
