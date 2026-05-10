#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Shop Manager Tests
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from acas_pro.ecommerce.shop_manager import (
    ShopManager, Shop, ShopCredentials, ShopStats,
    ShopPlatform, ShopStatus
)


class TestShopPlatform:
    """Shop platform enum tests"""
    
    def test_platform_values(self):
        """Test platform values"""
        assert ShopPlatform.DOUYIN_SHOP.value == "douyin_shop"
        assert ShopPlatform.TAOBAO.value == "taobao"
        assert ShopPlatform.TMALL.value == "tmall"
        assert ShopPlatform.JD.value == "jd"
        assert ShopPlatform.PDD.value == "pdd"


class TestShopStatus:
    """Shop status enum tests"""
    
    def test_status_values(self):
        """Test status values"""
        assert ShopStatus.ACTIVE.value == "active"
        assert ShopStatus.PAUSED.value == "paused"
        assert ShopStatus.SUSPENDED.value == "suspended"
        assert ShopStatus.PENDING.value == "pending"
        assert ShopStatus.CLOSED.value == "closed"


class TestShopCredentials:
    """Shop credentials tests"""
    
    def test_credentials_creation(self):
        """Test credentials creation"""
        creds = ShopCredentials(
            app_key="key123",
            app_secret="secret456",
            access_token="token789"
        )
        
        assert creds.app_key == "key123"
        assert creds.is_expired() is True  # no expires_at
    
    def test_credentials_not_expired(self):
        """Test credentials not expired"""
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        creds = ShopCredentials(
            access_token="token",
            expires_at=future
        )
        
        assert creds.is_expired() is False
    
    def test_credentials_expired(self):
        """Test credentials expired"""
        past = (datetime.now() - timedelta(hours=1)).isoformat()
        creds = ShopCredentials(
            access_token="token",
            expires_at=past
        )
        
        assert creds.is_expired() is True


class TestShopStats:
    """Shop stats tests"""
    
    def test_stats_creation(self):
        """Test stats creation"""
        stats = ShopStats(
            total_products=100,
            total_orders_today=50,
            revenue_today=5000.0,
            rating=4.8
        )
        
        assert stats.total_products == 100
        assert stats.rating == 4.8
    
    def test_stats_to_dict(self):
        """Test stats to dict"""
        stats = ShopStats(total_products=100, rating=4.5)
        data = stats.to_dict()
        
        assert data['total_products'] == 100
        assert data['rating'] == 4.5
        assert 'revenue_today' in data


class TestShop:
    """Shop dataclass tests"""
    
    def test_shop_creation(self):
        """Test shop creation"""
        shop = Shop(
            id="shop_001",
            name="测试店铺",
            platform=ShopPlatform.DOUYIN_SHOP,
            status=ShopStatus.ACTIVE
        )
        
        assert shop.id == "shop_001"
        assert shop.name == "测试店铺"
        assert shop.platform == ShopPlatform.DOUYIN_SHOP
        assert shop.auto_sync is True  # default
        assert shop.sync_interval == 15  # default
    
    def test_shop_to_dict(self):
        """Test shop to dict"""
        shop = Shop(
            id="shop_001",
            name="Test Shop",
            platform=ShopPlatform.TAOBAO,
            status=ShopStatus.ACTIVE
        )
        
        data = shop.to_dict()
        assert data['id'] == "shop_001"
        assert data['platform'] == "taobao"
        assert data['status'] == "active"
        assert 'stats' in data


class TestShopManager:
    """Shop manager tests"""
    
    @pytest.fixture
    def mock_db(self):
        mock = Mock()
        mock.execute = Mock()
        mock.fetch_one = Mock(return_value=None)
        mock.fetch_all = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def manager(self, mock_db):
        with patch('acas_pro.ecommerce.shop_manager.DatabaseManager', return_value=mock_db):
            return ShopManager()
    
    def test_init(self, manager, mock_db):
        """Test initialization"""
        mock_db.execute.assert_called()
    
    def test_platform_config(self, manager):
        """Test platform config exists"""
        assert ShopPlatform.DOUYIN_SHOP in manager.PLATFORM_CONFIG
        assert ShopPlatform.TAOBAO in manager.PLATFORM_CONFIG
        assert 'name' in manager.PLATFORM_CONFIG[ShopPlatform.DOUYIN_SHOP]
    
    def test_create_shop(self, manager, mock_db):
        """Test create shop"""
        shop = manager.create_shop(
            name="测试店铺",
            platform=ShopPlatform.DOUYIN_SHOP,
            shop_id_on_platform="platform_123",
            credentials={"app_key": "key", "app_secret": "secret"},
            owner_id="user_001"
        )
        
        assert shop.name == "测试店铺"
        assert shop.platform == ShopPlatform.DOUYIN_SHOP
        assert shop.owner_id == "user_001"
        assert shop.status == ShopStatus.PENDING
        mock_db.execute.assert_called()
    
    def test_get_shop_not_found(self, manager, mock_db):
        """Test get shop not found"""
        mock_db.fetch_one.return_value = None
        
        result = manager.get_shop("nonexistent")
        
        assert result is None
    
    def test_get_shops_by_owner_empty(self, manager, mock_db):
        """Test get shops by owner empty"""
        mock_db.fetch_all.return_value = []
        
        shops = manager.get_shops_by_owner("user_001")
        
        assert shops == []
    
    def test_get_shops_by_platform_empty(self, manager, mock_db):
        """Test get shops by platform empty"""
        mock_db.fetch_all.return_value = []
        
        shops = manager.get_shops_by_platform(ShopPlatform.TAOBAO)
        
        assert shops == []
    
    def test_update_shop_not_found(self, manager, mock_db):
        """Test update shop not found"""
        mock_db.fetch_one.return_value = None
        
        result = manager.update_shop("nonexistent", {"name": "New Name"})
        
        assert result is False
    
    def test_delete_shop(self, manager, mock_db):
        """Test delete shop"""
        result = manager.delete_shop("shop_001")
        
        assert result is True
        mock_db.execute.assert_called()
    
    def test_get_authorization_url(self, manager):
        """Test get authorization URL"""
        url = manager.get_authorization_url(
            ShopPlatform.DOUYIN_SHOP,
            "https://callback.com"
        )
        
        assert "jinritemai" in url or "fxg" in url
    
    def test_handle_authorization_callback(self, manager):
        """Test handle authorization callback"""
        result = manager.handle_authorization_callback(
            ShopPlatform.DOUYIN_SHOP,
            "auth_code",
            "state"
        )
        
        assert result['success'] is True
    
    def test_sync_shop_data_not_found(self, manager, mock_db):
        """Test sync shop data not found"""
        mock_db.fetch_one.return_value = None
        
        result = manager.sync_shop_data("nonexistent")
        
        assert result is False
    
    def test_get_shop_analytics(self, manager):
        """Test get shop analytics"""
        result = manager.get_shop_analytics(
            "shop_001",
            "2024-01-01",
            "2024-01-31"
        )
        
        assert result['shop_id'] == "shop_001"
        assert 'overview' in result
        assert 'daily_stats' in result
    
    def test_get_platform_list(self, manager):
        """Test get platform list"""
        platforms = manager.get_platform_list()
        
        assert len(platforms) == len(ShopPlatform)
        assert all('id' in p and 'name' in p for p in platforms)
    
    def test_batch_sync_empty(self, manager, mock_db):
        """Test batch sync empty"""
        mock_db.fetch_all.return_value = []
        
        result = manager.batch_sync("user_001")
        
        assert result['total'] == 0
        assert result['success'] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
