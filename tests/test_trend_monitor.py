#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Trend Monitor Tests
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from acas_pro.content.trend_monitor import (
    TrendMonitor, TrendItem, TrendReport,
    Platform
)


class TestPlatform:
    """Platform enum tests"""
    
    def test_platform_values(self):
        """Test platform values"""
        assert Platform.DOUYIN.value == "douyin"
        assert Platform.XIAOHONGSHU.value == "xhs"
        assert Platform.KUAISHOU.value == "kuaishou"
        assert Platform.BILIBILI.value == "bilibili"
        assert Platform.TIKTOK.value == "tiktok"


class TestTrendItem:
    """Trend item tests"""
    
    def test_trend_item_creation(self):
        """Test trend item creation"""
        item = TrendItem(
            id="item_001",
            platform=Platform.DOUYIN,
            title="Test Title",
            author="Test Author",
            url="https://example.com",
            views=100000,
            likes=5000,
            comments=500,
            shares=200,
            publish_time=datetime.now(),
            tags=["热门"],
            content_type="video"
        )
        
        assert item.id == "item_001"
        assert item.platform == Platform.DOUYIN
        assert item.views == 100000
        assert item.key_frames == []  # default
        assert item.visual_tags == []  # default


class TestTrendMonitor:
    """Trend monitor tests"""
    
    @pytest.fixture
    def mock_db(self):
        mock = Mock()
        mock.execute = Mock()
        mock.fetchone = Mock(return_value=None)
        mock.fetchall = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def monitor(self, mock_db):
        return TrendMonitor(db=mock_db)
    
    def test_init(self, monitor, mock_db):
        """Test initialization"""
        assert monitor.db == mock_db
        assert not monitor._running
        mock_db.execute.assert_called()
    
    def test_start_stop_monitoring(self, monitor):
        """Test start and stop monitoring"""
        with patch.object(monitor, '_monitor_loop'):
            monitor.start_monitoring()
            assert monitor._running
            
            monitor.stop_monitoring()
            assert not monitor._running
    
    def test_simulate_fetch(self, monitor):
        """Test simulate fetch"""
        items = monitor._simulate_fetch(Platform.DOUYIN)
        
        assert len(items) == 5
        assert all(isinstance(item, TrendItem) for item in items)
        assert all(item.platform == Platform.DOUYIN for item in items)
    
    def test_analyze_content(self, monitor):
        """Test content analysis"""
        item = TrendItem(
            id="item_001",
            platform=Platform.DOUYIN,
            title="Test",
            author="Author",
            url="https://example.com",
            views=100000,
            likes=5000,
            comments=500,
            shares=200,
            publish_time=datetime.now(),
            tags=["热门"],
            content_type="video"
        )
        
        monitor._analyze_content(item)
        
        assert item.viral_score > 0
        assert item.efficiency_score > 0
        assert item.relevance_score > 0
    
    def test_get_trending_items_empty(self, monitor, mock_db):
        """Test get trending items with no data"""
        mock_db.fetchall.return_value = []
        
        items = monitor.get_trending_items(
            platform=Platform.DOUYIN,
            min_viral_score=50.0
        )
        
        assert items == []
    
    def test_get_trend_report(self, monitor, mock_db):
        """Test get trend report"""
        mock_db.fetchall.return_value = [
            {
                "id": "item_001",
                "platform": "douyin",
                "title": "Test Title",
                "author": "Author",
                "url": "https://example.com",
                "views": 100000,
                "likes": 5000,
                "comments": 500,
                "shares": 200,
                "publish_time": datetime.now().isoformat(),
                "tags": '["热门", "推荐"]',
                "content_type": "video",
                "thumbnail_url": None,
                "viral_score": 85.0,
                "efficiency_score": 5.7,
                "relevance_score": 75.0,
                "transcript": "",
                "visual_tags": "[]"
            }
        ]
        
        report = monitor.get_trend_report(
            platform=Platform.DOUYIN,
            hours=24
        )
        
        assert report is not None
        assert report.platform == Platform.DOUYIN
        assert report.total_items == 1
        assert len(report.top_items) == 1
    
    def test_register_callback(self, monitor):
        """Test register callback"""
        callback = Mock()
        
        monitor.register_callback(callback)
        
        assert callback in monitor._callbacks
    
    def test_notify_callbacks(self, monitor):
        """Test notify callbacks"""
        callback = Mock()
        monitor._callbacks.append(callback)
        
        items = []
        monitor._notify_callbacks(Platform.DOUYIN, items)
        
        callback.assert_called_once_with(Platform.DOUYIN, items)
    
    def test_platform_configs(self, monitor):
        """Test platform configurations"""
        assert Platform.DOUYIN in monitor.platform_configs
        assert Platform.XIAOHONGSHU in monitor.platform_configs
        
        douyin_config = monitor.platform_configs[Platform.DOUYIN]
        assert "api_endpoint" in douyin_config
        assert "fetch_interval" in douyin_config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
