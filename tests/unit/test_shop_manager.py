# -*- coding: utf-8 -*-
"""Tests for ecommerce/shop_manager.py"""

import pytest
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import MagicMock, patch

from acas_pro.ecommerce.shop_manager import (
    ShopManager,
    Shop,
    ShopPlatform,
    ShopStatus,
    ShopCredentials,
    ShopStats,
)


class TestShopManager:
    """Test ShopManager class"""

    @pytest.fixture
    def mock_db(self):
        """Mock DatabaseManager"""
        db = MagicMock()
        db.fetch_one.return_value = None
        db.fetch_all.return_value = []
        db.execute.return_value = None
        return db

    @pytest.fixture
    def manager(self, mock_db):
        """Create ShopManager with mocked DB"""
        with patch('acas_pro.ecommerce.shop_manager.DatabaseManager', return_value=mock_db):
            mgr = ShopManager()
            mgr.db = mock_db
            return mgr

    @pytest.fixture
    def sample_credentials(self):
        """Create sample credentials"""
        return {
            'app_key': 'test_key_12345',
            'app_secret': 'test_secret_67890',
            'access_token': 'token_abc123',
            'refresh_token': 'refresh_xyz789',
            'expires_at': (datetime.now() + timedelta(hours=2)).isoformat(),
        }

    # ===== 初始化测试 =====
    def test_init(self, mock_db):
        """Test ShopManager initialization"""
        with patch('acas_pro.ecommerce.shop_manager.DatabaseManager', return_value=mock_db):
            mgr = ShopManager()
            assert mgr.db is not None

    def test_init_database(self, manager, mock_db):
        """Test database initialization"""
        manager._init_database()
        assert mock_db.execute.called

    # ===== 平台配置测试 =====
    def test_platform_config_exists(self, manager):
        """Test PLATFORM_CONFIG constant"""
        assert len(manager.PLATFORM_CONFIG) > 0
        assert ShopPlatform.DOUYIN_SHOP in manager.PLATFORM_CONFIG
        assert ShopPlatform.KUAISHOU_SHOP in manager.PLATFORM_CONFIG

    def test_platform_config_structure(self, manager):
        """Test platform config has required fields"""
        for platform, config in manager.PLATFORM_CONFIG.items():
            assert 'name' in config
            assert 'api_base' in config
            assert 'auth_url' in config
            assert 'scopes' in config

    # ===== 枚举测试 =====
    def test_shop_platform_values(self):
        """Test ShopPlatform enum values"""
        assert ShopPlatform.DOUYIN_SHOP.value == 'douyin_shop'
        assert ShopPlatform.KUAISHOU_SHOP.value == 'kuaishou_shop'
        assert ShopPlatform.TAOBAO.value == 'taobao'
        assert ShopPlatform.TMALL.value == 'tmall'
        assert ShopPlatform.JD.value == 'jd'
        assert ShopPlatform.PDD.value == 'pdd'
        assert ShopPlatform.XIAOHONGSHU_SHOP.value == 'xiaohongshu_shop'
        assert ShopPlatform.WECHAT_SHOP.value == 'wechat_shop'

    def test_shop_status_values(self):
        """Test ShopStatus enum values"""
        assert ShopStatus.ACTIVE.value == 'active'
        assert ShopStatus.PAUSED.value == 'paused'
        assert ShopStatus.SUSPENDED.value == 'suspended'
        assert ShopStatus.PENDING.value == 'pending'
        assert ShopStatus.CLOSED.value == 'closed'

    # ===== 店铺创建测试 =====
    def test_create_shop(self, manager, mock_db, sample_credentials):
        """Test creating a shop"""
        mock_db.execute.return_value = None

        shop = manager.create_shop(
            name='测试店铺',
            platform=ShopPlatform.DOUYIN_SHOP,
            shop_id_on_platform='dy_12345',
            credentials=sample_credentials,
            owner_id='owner_001',
        )

        assert shop is not None
        assert shop.name == '测试店铺'
        assert shop.platform == ShopPlatform.DOUYIN_SHOP
        assert shop.status == ShopStatus.PENDING  # default
        mock_db.execute.assert_called()

    def test_create_shop_with_kwargs(self, manager, mock_db, sample_credentials):
        """Test creating a shop with additional kwargs"""
        mock_db.execute.return_value = None

        shop = manager.create_shop(
            name='小红书店铺',
            platform=ShopPlatform.XIAOHONGSHU_SHOP,
            shop_id_on_platform='xhs_67890',
            credentials=sample_credentials,
            owner_id='owner_001',
            contact_name='张三',
            contact_phone='13800138000',
        )

        assert shop.contact_name == '张三'
        assert shop.contact_phone == '13800138000'

    # ===== 店铺查询测试 =====
    def test_get_shop_found(self, manager, mock_db):
        """Test getting an existing shop"""
        mock_db.fetch_one.return_value = {
            'id': 'shop_001',
            'name': '测试店铺',
            'platform': 'douyin_shop',
            'status': 'pending',
            'shop_id_on_platform': 'dy_12345',
            'shop_url': None,
            'logo_url': None,
            'description': None,
            'contact_name': None,
            'contact_phone': None,
            'contact_email': None,
            'main_category': '',
            'business_license': None,
            'credentials': '{}',
            'auto_sync': 1,
            'sync_interval': 15,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'owner_id': 'owner_001',
            'last_sync_at': None,
        }

        shop = manager.get_shop('shop_001')
        assert shop is not None
        assert shop.id == 'shop_001'
        assert shop.name == '测试店铺'

    def test_get_shop_not_found(self, manager, mock_db):
        """Test getting non-existent shop"""
        mock_db.fetch_one.return_value = None
        shop = manager.get_shop('nonexistent')
        assert shop is None

    def test_get_shops_by_owner(self, manager, mock_db):
        """Test getting shops by owner"""
        mock_db.fetch_all.return_value = []
        shops = manager.get_shops_by_owner(owner_id='owner_001')
        assert isinstance(shops, list)

    def test_get_shops_by_platform(self, manager, mock_db):
        """Test getting shops by platform"""
        mock_db.fetch_all.return_value = []
        shops = manager.get_shops_by_platform(ShopPlatform.DOUYIN_SHOP)
        assert isinstance(shops, list)

    # ===== 店铺更新测试 =====
    def test_update_shop(self, manager, mock_db):
        """Test updating a shop"""
        # Mock get_shop to return a shop
        mock_db.fetch_one.return_value = {
            'id': 'shop_001',
            'name': '测试店铺',
            'platform': 'douyin_shop',
            'status': 'pending',
            'shop_id_on_platform': 'dy_12345',
            'shop_url': None,
            'logo_url': None,
            'description': None,
            'contact_name': None,
            'contact_phone': None,
            'contact_email': None,
            'main_category': '',
            'business_license': None,
            'credentials': '{}',
            'auto_sync': 1,
            'sync_interval': 15,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'owner_id': 'owner_001',
            'last_sync_at': None,
        }

        result = manager.update_shop('shop_001', {'name': '新店铺名', 'status': ShopStatus.ACTIVE})
        assert result is True
        mock_db.execute.assert_called()

    def test_update_shop_not_found(self, manager, mock_db):
        """Test updating non-existent shop"""
        mock_db.fetch_one.return_value = None
        result = manager.update_shop('nonexistent', {'name': 'Test'})
        assert result is False

    # ===== 店铺删除测试 =====
    def test_delete_shop(self, manager, mock_db):
        """Test deleting a shop"""
        result = manager.delete_shop('shop_001')
        assert result is True
        assert mock_db.execute.call_count >= 2  # Deletes from shop_stats and shops

    # ===== 授权URL测试 =====
    def test_get_authorization_url(self, manager):
        """Test getting authorization URL"""
        url = manager.get_authorization_url(ShopPlatform.DOUYIN_SHOP, 'https://example.com/callback')
        assert isinstance(url, str)
        assert len(url) > 0

    # ===== 授权回调测试 =====
    def test_handle_authorization_callback(self, manager):
        """Test handling authorization callback"""
        result = manager.handle_authorization_callback(
            platform=ShopPlatform.DOUYIN_SHOP,
            code='auth_code_123',
            state='state_456',
        )
        assert isinstance(result, dict)
        assert 'success' in result

    # ===== 数据同步测试 =====
    def test_sync_shop_data(self, manager):
        """Test syncing shop data (stub)"""
        # Mock get_shop to return a shop
        with patch.object(manager, 'get_shop') as mock_get:
            mock_get.return_value = Shop(
                id='shop_001',
                name='测试店铺',
                platform=ShopPlatform.DOUYIN_SHOP,
                status=ShopStatus.ACTIVE,
            )
            with pytest.raises(NotImplementedError):
                manager.sync_shop_data('shop_001')

    # ===== 分析数据测试 =====
    def test_get_shop_analytics(self, manager):
        """Test getting shop analytics"""
        result = manager.get_shop_analytics(
            shop_id='shop_001',
            start_date='2026-01-01',
            end_date='2026-12-31',
        )
        assert isinstance(result, dict)
        assert 'shop_id' in result
        assert 'period' in result
        assert 'overview' in result

    # ===== 平台列表测试 =====
    def test_get_platform_list(self, manager):
        """Test getting platform list"""
        platforms = manager.get_platform_list()
        assert isinstance(platforms, list)
        assert len(platforms) > 0
        assert 'id' in platforms[0]
        assert 'name' in platforms[0]

    # ===== 批量同步测试 =====
    def test_batch_sync(self, manager, mock_db):
        """Test batch syncing shops"""
        # Mock get_shops_by_owner to return shops
        with patch.object(manager, 'get_shops_by_owner') as mock_get:
            mock_get.return_value = [
                Shop(
                    id='shop_001',
                    name='店铺1',
                    platform=ShopPlatform.DOUYIN_SHOP,
                    status=ShopStatus.ACTIVE,
                    auto_sync=True,
                ),
                Shop(
                    id='shop_002',
                    name='店铺2',
                    platform=ShopPlatform.XIAOHONGSHU_SHOP,
                    status=ShopStatus.ACTIVE,
                    auto_sync=True,
                ),
            ]

            # Mock sync_shop_data to raise NotImplementedError
            with patch.object(manager, 'sync_shop_data', side_effect=NotImplementedError('Stub')):
                results = manager.batch_sync(owner_id='owner_001')
                assert 'total' in results
                assert 'success' in results
                assert 'failed' in results


class TestShop:
    """Test Shop dataclass"""

    def test_shop_creation(self):
        """Test Shop creation"""
        shop = Shop(
            id='shop_001',
            name='测试店铺',
            platform=ShopPlatform.DOUYIN_SHOP,
            status=ShopStatus.PENDING,
        )
        assert shop.id == 'shop_001'
        assert shop.name == '测试店铺'
        assert shop.status == ShopStatus.PENDING

    def test_shop_to_dict(self):
        """Test Shop to_dict method"""
        shop = Shop(
            id='shop_001',
            name='测试店铺',
            platform=ShopPlatform.DOUYIN_SHOP,
            status=ShopStatus.ACTIVE,
            contact_name='张三',
            contact_phone='13800138000',
        )
        result = shop.to_dict()
        assert isinstance(result, dict)
        assert result['id'] == 'shop_001'
        assert result['name'] == '测试店铺'


class TestShopCredentials:
    """Test ShopCredentials dataclass"""

    def test_credentials_creation(self):
        """Test ShopCredentials creation"""
        creds = ShopCredentials(
            app_key='key_123',
            app_secret='secret_456',
            access_token='token_789',
            refresh_token='refresh_012',
            expires_at='2026-12-31T23:59:59',
        )
        assert creds.app_key == 'key_123'
        assert creds.access_token == 'token_789'

    def test_is_expired_no_expiry(self):
        """Test is_expired with no expiry date"""
        creds = ShopCredentials()
        assert creds.is_expired() is True

    def test_is_expired_future(self):
        """Test is_expired with future expiry"""
        future = (datetime.now() + timedelta(hours=2)).isoformat()
        creds = ShopCredentials(expires_at=future)
        assert creds.is_expired() is False

    def test_is_expired_past(self):
        """Test is_expired with past expiry"""
        past = (datetime.now() - timedelta(hours=2)).isoformat()
        creds = ShopCredentials(expires_at=past)
        assert creds.is_expired() is True


class TestShopStats:
    """Test ShopStats dataclass"""

    def test_stats_creation(self):
        """Test ShopStats creation"""
        stats = ShopStats(
            total_products=100,
            total_orders_today=10,
            total_orders_month=200,
            revenue_today=5000.0,
            revenue_month=100000.0,
            visitors_today=500,
            conversion_rate=0.02,
            rating=4.5,
        )
        assert stats.total_products == 100
        assert stats.rating == 4.5

    def test_stats_to_dict(self):
        """Test ShopStats to_dict method"""
        stats = ShopStats(
            total_products=50,
            total_orders_today=5,
            revenue_today=2000.0,
        )
        result = stats.to_dict()
        assert isinstance(result, dict)
        assert result['total_products'] == 50
        assert result['revenue_today'] == 2000.0
