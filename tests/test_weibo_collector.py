#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Weibo Collector Tests
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from acas_pro.collectors.weibo_api import WeiboCollector, WeiboPost


class TestWeiboPost:
    """Weibo post tests"""
    
    def test_post_creation(self):
        """Test post creation"""
        post = WeiboPost(
            id="123456",
            text="Test weibo content",
            author="TestUser",
            author_id="789",
            created_at=datetime.utcnow(),
            reposts_count=10,
            comments_count=5,
            attitudes_count=20,
            source="iPhone"
        )
        
        assert post.id == "123456"
        assert post.author == "TestUser"
        assert post.pics == []  # default
    
    def test_post_to_dict(self):
        """Test post to dict"""
        now = datetime.utcnow()
        post = WeiboPost(
            id="123",
            text="Test",
            author="User",
            author_id="456",
            created_at=now,
            reposts_count=0,
            comments_count=0,
            attitudes_count=0,
            source="Web",
            pics=["pic1.jpg", "pic2.jpg"]
        )
        
        data = post.to_dict()
        assert data['id'] == "123"
        assert data['author'] == "User"
        assert len(data['pics']) == 2


class TestWeiboCollector:
    """Weibo collector tests"""
    
    @pytest.fixture
    def collector(self):
        return WeiboCollector()
    
    def test_init(self, collector):
        """Test initialization"""
        assert collector.API_BASE == "https://api.weibo.com/2"
        assert collector._rate_limit_remaining == 100
    
    def test_init_with_credentials(self):
        """Test init with credentials"""
        collector = WeiboCollector(
            app_key="test_key",
            app_secret="test_secret",
            access_token="test_token"
        )
        assert collector.app_key == "test_key"
        assert collector.access_token == "test_token"
    
    def test_search_no_token(self, collector):
        """Test search without token returns empty"""
        collector.access_token = None
        results = collector.search("test")
        assert results == []
    
    def test_get_hot_topics(self, collector):
        """Test get hot topics"""
        topics = collector.get_hot_topics()
        
        assert len(topics) > 0
        assert all('rank' in t for t in topics)
        assert all('topic' in t for t in topics)
        assert all('heat' in t for t in topics)
    
    def test_get_mock_hot_topics(self, collector):
        """Test mock hot topics"""
        topics = collector._get_mock_hot_topics()
        
        assert len(topics) == 5
        assert topics[0]['rank'] == 1
        assert 'topic' in topics[0]
        assert 'heat' in topics[0]
    
    def test_get_user_timeline_no_token(self, collector):
        """Test get user timeline without token"""
        collector.access_token = None
        results = collector.get_user_timeline("12345")
        assert results == []
    
    def test_parse_status(self, collector):
        """Test parse status"""
        status = {
            'id': 123456789,
            'text': 'Test weibo',
            'created_at': 'Wed Jun 14 15:26:23 +0800 2023',
            'reposts_count': 10,
            'comments_count': 5,
            'attitudes_count': 20,
            'source': 'iPhone客户端',
            'user': {
                'id': 987654321,
                'screen_name': 'TestUser'
            },
            'pic_urls': [
                {'thumbnail_pic': 'http://example.com/pic1.jpg'}
            ]
        }
        
        post = collector._parse_status(status)
        
        assert post.id == "123456789"
        assert post.text == "Test weibo"
        assert post.author == "TestUser"
        assert len(post.pics) == 1
    
    def test_check_rate_limit_reset(self, collector):
        """Test rate limit reset after hour"""
        import time
        collector._rate_limit_remaining = 0
        collector._last_request_time = time.time() - 3700  # More than 1 hour ago
        
        # Should reset
        collector._check_rate_limit()
        assert collector._rate_limit_remaining == 99  # decremented after reset


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
