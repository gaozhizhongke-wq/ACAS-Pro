#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - News Engine Tests
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from acas_pro.sentiment.news_engine import (
    MarketIntelligenceEngine, NewsArticle, RiskAlert,
    NewsCategory, RiskLevel, market_intelligence
)


class TestNewsCategory:
    """News category enum tests"""
    
    def test_category_values(self):
        """Test category values"""
        assert NewsCategory.BUSINESS.value == "business"
        assert NewsCategory.TECHNOLOGY.value == "technology"
        assert NewsCategory.FINANCE.value == "finance"
        assert NewsCategory.POLITICS.value == "politics"
        assert NewsCategory.COMMODITY.value == "commodity"
        assert NewsCategory.LOGISTICS.value == "logistics"
        assert NewsCategory.DISASTER.value == "disaster"
        assert NewsCategory.REGULATION.value == "regulation"


class TestRiskLevel:
    """Risk level enum tests"""
    
    def test_risk_level_values(self):
        """Test risk level values"""
        assert RiskLevel.CRITICAL.value == "critical"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.INFO.value == "info"


class TestNewsArticle:
    """News article tests"""
    
    def test_article_creation(self):
        """Test article creation"""
        article = NewsArticle(
            id="news_001",
            title="Test Title",
            content="Test content here.",
            summary="Test summary",
            source="Test Source",
            source_url="https://example.com",
            category=NewsCategory.BUSINESS,
            published_at=datetime.now(),
            language="en"
        )
        
        assert article.id == "news_001"
        assert article.category == NewsCategory.BUSINESS
        assert article.affected_regions == []  # default
        assert article.keywords == []  # default
    
    def test_article_to_dict(self):
        """Test article to dict"""
        article = NewsArticle(
            id="news_001",
            title="Test",
            content="Content",
            summary="Summary",
            source="Source",
            source_url="https://example.com",
            category=NewsCategory.TECHNOLOGY,
            published_at=datetime.now(),
            language="en",
            relevance_score=0.85,
            affected_regions=["global"]
        )
        
        data = article.to_dict()
        
        assert "id" in data
        assert "category" in data
        assert data["category"] == "technology"


class TestRiskAlert:
    """Risk alert tests"""
    
    def test_alert_creation(self):
        """Test alert creation"""
        alert = RiskAlert(
            id="alert_001",
            level=RiskLevel.HIGH,
            title="Supply Risk",
            description="Description here",
            category="supply_chain",
            source_articles=["news_001"],
            affected_regions=["global"],
            detected_at=datetime.now()
        )
        
        assert alert.id == "alert_001"
        assert alert.level == RiskLevel.HIGH
    
    def test_alert_to_dict(self):
        """Test alert to dict"""
        alert = RiskAlert(
            id="alert_001",
            level=RiskLevel.MEDIUM,
            title="Test",
            description="Desc",
            category="test",
            source_articles=[],
            affected_regions=[],
            detected_at=datetime.now()
        )
        
        data = alert.to_dict()
        
        assert "id" in data
        assert "level" in data
        assert data["level"] == "medium"


class TestMarketIntelligenceEngine:
    """Market intelligence engine tests"""
    
    @pytest.fixture
    def engine(self):
        return MarketIntelligenceEngine()
    
    def test_init(self, engine):
        """Test initialization"""
        assert engine._cache == []
        assert engine._cache_time is None
        assert engine._cache_ttl.total_seconds() == 900  # 15 minutes
    
    def test_fetch_intelligence(self, engine):
        """Test fetch intelligence"""
        articles = engine.fetch_intelligence(max_items=10)
        
        assert len(articles) <= 10
        assert all(isinstance(a, NewsArticle) for a in articles)
    
    def test_fetch_intelligence_with_categories(self, engine):
        """Test fetch with category filter"""
        articles = engine.fetch_intelligence(
            categories=[NewsCategory.BUSINESS],
            max_items=5
        )
        
        assert all(a.category == NewsCategory.BUSINESS for a in articles)
    
    def test_fetch_intelligence_with_regions(self, engine):
        """Test fetch with region filter"""
        articles = engine.fetch_intelligence(
            regions=["global"],
            max_items=5
        )
        
        # All articles should have "global" in affected_regions
        for article in articles:
            assert "global" in article.affected_regions
    
    def test_generate_sample_data(self, engine):
        """Test generate sample data"""
        articles = engine._generate_sample_data(20)
        
        assert len(articles) == 20
        assert all(isinstance(a, NewsArticle) for a in articles)
        assert all(a.sentiment is not None for a in articles)
    
    def test_detect_risks(self, engine):
        """Test detect risks"""
        articles = engine._generate_sample_data(50)
        alerts = engine.detect_risks(articles)
        
        assert isinstance(alerts, list)
        # May or may not have alerts depending on random data
    
    def test_get_recommended_actions(self, engine):
        """Test get recommended actions"""
        actions = engine._get_recommended_actions("supply_disruption")
        
        assert len(actions) > 0
        assert isinstance(actions, list)
    
    def test_get_recommended_actions_unknown(self, engine):
        """Test get actions for unknown risk type"""
        actions = engine._get_recommended_actions("unknown_risk")
        
        assert actions == ["继续监控情况"]
    
    def test_get_sentiment_summary_empty(self, engine):
        """Test sentiment summary with empty list"""
        summary = engine.get_sentiment_summary([])
        
        assert summary["total"] == 0
        assert summary["trend"] == "neutral"
    
    def test_get_sentiment_summary(self, engine):
        """Test sentiment summary"""
        articles = engine._generate_sample_data(10)
        summary = engine.get_sentiment_summary(articles)
        
        assert summary["total"] == 10
        assert "sentiment_distribution" in summary
        assert "average_score" in summary
        assert "trend" in summary
    
    def test_risk_patterns_exist(self, engine):
        """Test risk patterns are defined"""
        assert "supply_disruption" in engine.RISK_PATTERNS
        assert "price_volatility" in engine.RISK_PATTERNS
        assert "geopolitical" in engine.RISK_PATTERNS
        assert "natural_disaster" in engine.RISK_PATTERNS
        assert "cybersecurity" in engine.RISK_PATTERNS
    
    def test_sources_exist(self, engine):
        """Test news sources are defined"""
        assert len(engine.SOURCES) > 0
        assert "Reuters" in engine.SOURCES


class TestGlobalInstance:
    """Test global market intelligence instance"""
    
    def test_global_instance_exists(self):
        """Test global instance exists"""
        assert market_intelligence is not None
        assert isinstance(market_intelligence, MarketIntelligenceEngine)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
