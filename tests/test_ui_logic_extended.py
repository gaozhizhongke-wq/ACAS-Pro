#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Extended UI Logic Tests
Tests for inventory and content creation logic
"""

import pytest
from datetime import datetime

from acas_pro.ui.logic import (
    InventoryLogic, InventoryItem, InventoryAlert,
    ContentLogic, TrendItem, GeneratedScript,
    ContentStyle, Platform
)


class TestInventoryLogic:
    """Inventory logic tests"""
    
    @pytest.fixture
    def inventory(self):
        return InventoryLogic()
    
    def test_initialization(self, inventory):
        """Test inventory logic initializes"""
        assert inventory is not None
        assert inventory._items == []
        assert inventory._alerts == []
    
    def test_analyze_inventory_default(self, inventory):
        """Test inventory analysis with default data"""
        items = inventory.analyze_inventory()
        
        assert len(items) > 0
        
        # Check item structure
        for item in items:
            assert item.product_id
            assert item.product_name
            assert item.urgency in ["critical", "high", "medium", "low"]
            assert item.days_until_stockout >= 0
    
    def test_analyze_inventory_custom(self, inventory):
        """Test inventory analysis with custom data"""
        products = [
            {"id": "SKU-001", "name": "Test Product", "current_stock": 2, "avg_daily_sales": 1, "lead_time_days": 7},
        ]
        
        items = inventory.analyze_inventory(products)
        
        assert len(items) == 1
        assert items[0].urgency == "critical"
        assert items[0].days_until_stockout == 2
    
    def test_get_critical_count(self, inventory):
        """Test critical count"""
        inventory.analyze_inventory()
        count = inventory.get_critical_count()
        assert isinstance(count, int)
        assert count >= 0
    
    def test_get_reorder_summary(self, inventory):
        """Test reorder summary"""
        inventory.analyze_inventory()
        summary = inventory.get_reorder_summary()
        
        assert "total_items" in summary
        assert "critical_count" in summary
        assert "needs_attention" in summary
    
    def test_export_recommendations(self, inventory):
        """Test export recommendations"""
        inventory.analyze_inventory()
        exported = inventory.export_recommendations()
        
        assert isinstance(exported, list)
        if exported:
            assert "product_id" in exported[0]
            assert "recommended_order" in exported[0]
    
    def test_get_alerts(self, inventory):
        """Test alerts retrieval"""
        inventory.analyze_inventory()
        alerts = inventory.get_alerts()
        
        assert isinstance(alerts, list)


class TestContentLogic:
    """Content creation logic tests"""
    
    @pytest.fixture
    def content(self):
        return ContentLogic()
    
    def test_initialization(self, content):
        """Test content logic initializes"""
        assert content is not None
    
    def test_fetch_trends(self, content):
        """Test fetch trends"""
        trends = content.fetch_trends(limit=10)
        
        assert len(trends) == 10
        
        for trend in trends:
            assert trend.id
            assert trend.title
            assert isinstance(trend.platform, Platform)
            assert trend.views > 0
    
    def test_fetch_trends_by_platform(self, content):
        """Test fetch trends filtered by platform"""
        trends = content.fetch_trends(platform=Platform.DOUYIN, limit=5)
        
        assert len(trends) == 5
        for trend in trends:
            assert trend.platform == Platform.DOUYIN
    
    def test_analyze_trend(self, content):
        """Test trend analysis"""
        content.fetch_trends(limit=5)
        analysis = content.analyze_trend("trend-0")
        
        assert "viral_factors" in analysis
        assert "target_audience" in analysis
        assert "recommendations" in analysis
    
    def test_analyze_trend_not_found(self, content):
        """Test analyze non-existent trend"""
        analysis = content.analyze_trend("non-existent")
        assert analysis == {}
    
    def test_generate_script(self, content):
        """Test script generation"""
        script = content.generate_script(
            topic="Test Topic",
            platform=Platform.DOUYIN,
            style=ContentStyle.CASUAL,
            duration=60,
            keywords=["test", "demo"]
        )
        
        assert isinstance(script, GeneratedScript)
        assert "Test Topic" in script.title
        assert script.platform == Platform.DOUYIN
        assert script.style == ContentStyle.CASUAL
        assert script.word_count > 0
        assert script.estimated_duration == 60
    
    def test_get_templates(self, content):
        """Test get templates"""
        templates = content.get_templates()
        
        assert len(templates) > 0
        for template in templates:
            assert template.id
            assert template.name
            assert template.template
    
    def test_get_templates_by_platform(self, content):
        """Test get templates filtered by platform"""
        templates = content.get_templates(platform=Platform.DOUYIN)
        
        for template in templates:
            assert template.platform == Platform.DOUYIN
    
    def test_optimize_script(self, content):
        """Test script optimization"""
        original = content.generate_script(
            topic="Test",
            platform=Platform.DOUYIN,
            style=ContentStyle.PROFESSIONAL,
            duration=120
        )
        
        optimized = content.optimize_script(original, Platform.XIAOHONGSHU)
        
        assert optimized.platform == Platform.XIAOHONGSHU
        assert "Optimized" in optimized.content


class TestInventoryItem:
    """Inventory item tests"""
    
    def test_item_creation(self):
        """Test inventory item creation"""
        item = InventoryItem(
            product_id="SKU-001",
            product_name="Test Product",
            current_stock=100,
            recommended_order=50,
            urgency="medium",
            days_until_stockout=20,
            reorder_point=30,
            confidence=0.9
        )
        
        assert item.product_id == "SKU-001"
        assert item.urgency == "medium"
        assert item.confidence == 0.9


class TestTrendItem:
    """Trend item tests"""
    
    def test_trend_creation(self):
        """Test trend item creation"""
        trend = TrendItem(
            id="trend-1",
            title="Test Trend",
            author="testuser",
            platform=Platform.DOUYIN,
            views=100000,
            likes=5000,
            comments=200,
            viral_score=85.5,
            timestamp=datetime.now()
        )
        
        assert trend.id == "trend-1"
        assert trend.platform == Platform.DOUYIN
        assert trend.viral_score == 85.5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
