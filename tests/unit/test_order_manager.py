# -*- coding: utf-8 -*-
"""Tests for ecommerce/order_manager.py"""

import pytest
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import MagicMock, patch

from acas_pro.ecommerce.order_manager import (
    OrderManager,
    Order,
    OrderItem,
    OrderStatus,
    PaymentStatus,
    ShippingAddress,
    LogisticsInfo,
)


class TestOrderManager:
    """Test OrderManager class"""

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
        """Create OrderManager with mocked DB"""
        with patch('acas_pro.ecommerce.order_manager.DatabaseManager', return_value=mock_db):
            mgr = OrderManager()
            mgr.db = mock_db
            return mgr

    @pytest.fixture
    def sample_address(self):
        """Create sample shipping address"""
        return ShippingAddress(
            name='张三',
            phone='13800138000',
            province='广东省',
            city='深圳市',
            district='南山区',
            detail='科技园南路1号',
            zip_code='518000',
        )

    @pytest.fixture
    def sample_items(self):
        """Create sample order items"""
        return [
            OrderItem(
                product_id='prod_001',
                product_name='黑茶250g',
                sku_id='sku_001',
                sku_name='特级黑茶',
                quantity=2,
                unit_price=128.0,
                total_price=256.0,
                image_url='https://example.com/tea.jpg',
            ),
            OrderItem(
                product_id='prod_002',
                product_name='茶具套装',
                sku_id='sku_002',
                sku_name='陶瓷茶具',
                quantity=1,
                unit_price=199.0,
                total_price=199.0,
            ),
        ]

    # ===== 初始化测试 =====
    def test_init(self, mock_db):
        """Test OrderManager initialization"""
        with patch('acas_pro.ecommerce.order_manager.DatabaseManager', return_value=mock_db):
            mgr = OrderManager()
            assert mgr.db is not None

    def test_init_database(self, manager, mock_db):
        """Test database initialization"""
        manager._init_database()
        assert mock_db.execute.called

    # ===== 订单状态枚举测试 =====
    def test_order_status_values(self):
        """Test OrderStatus enum values"""
        assert OrderStatus.PENDING_PAYMENT.value == 'pending_payment'
        assert OrderStatus.PENDING_SHIP.value == 'pending_ship'
        assert OrderStatus.SHIPPED.value == 'shipped'
        assert OrderStatus.DELIVERED.value == 'delivered'
        assert OrderStatus.COMPLETED.value == 'completed'
        assert OrderStatus.CANCELLED.value == 'cancelled'
        assert OrderStatus.REFUNDING.value == 'refunding'
        assert OrderStatus.REFUNDED.value == 'refunded'

    def test_payment_status_values(self):
        """Test PaymentStatus enum values"""
        assert PaymentStatus.UNPAID.value == 'unpaid'
        assert PaymentStatus.PAID.value == 'paid'
        assert PaymentStatus.PARTIAL.value == 'partial'
        assert PaymentStatus.REFUNDED.value == 'refunded'

    # ===== 订单创建测试 =====
    def test_create_order(self, manager, mock_db, sample_address, sample_items):
        """Test creating an order"""
        mock_db.execute.return_value = None

        order = manager.create_order(
            platform_order_id='ext_001',
            platform='douyin',
            items=sample_items,
            shipping_address=sample_address,
            shop_id='shop_001',
        )

        assert order is not None
        assert order.platform_order_id == 'ext_001'
        assert order.platform == 'douyin'
        assert len(order.items) == 2
        assert order.status == OrderStatus.PENDING_PAYMENT
        assert order.payment_status == PaymentStatus.UNPAID
        mock_db.execute.assert_called()

    def test_create_order_calculates_total(self, manager, mock_db, sample_address, sample_items):
        """Test that create_order calculates total"""
        mock_db.execute.return_value = None

        order = manager.create_order(
            platform_order_id='ext_002',
            platform='xiaohongshu',
            items=sample_items,
            shipping_address=sample_address,
        )

        assert order.subtotal > 0
        assert order.total_amount > 0

    # ===== 订单查询测试 =====
    def test_get_order_found(self, manager, mock_db):
        """Test getting an existing order"""
        # Mock database row
        mock_db.fetch_one.return_value = {
            'id': 'ord_001',
            'platform_order_id': 'ext_001',
            'platform': 'douyin',
            'items': '[{"product_id": "prod_001", "product_name": "黑茶", "sku_id": "sku_001", "sku_name": "特级", "quantity": 1, "unit_price": 128.0, "total_price": 128.0}]',
            'subtotal': 128.0,
            'shipping_fee': 10.0,
            'discount': 0.0,
            'tax': 0.0,
            'total_amount': 138.0,
            'status': 'pending_payment',
            'payment_status': 'unpaid',
            'shipping_address': None,
            'logistics': None,
            'buyer_id': 'buyer_001',
            'buyer_nickname': '测试用户',
            'buyer_message': None,
            'created_at': datetime.now().isoformat(),
            'paid_at': None,
            'shipped_at': None,
            'completed_at': None,
            'shop_id': 'shop_001',
            'seller_note': None,
        }

        order = manager.get_order('ord_001')
        assert order is not None
        assert order.id == 'ord_001'

    def test_get_order_not_found(self, manager, mock_db):
        """Test getting non-existent order"""
        mock_db.fetch_one.return_value = None
        order = manager.get_order('nonexistent')
        assert order is None

    def test_get_orders_by_shop(self, manager, mock_db):
        """Test getting orders by shop"""
        mock_db.fetch_all.return_value = []
        orders = manager.get_orders_by_shop(shop_id='shop_001')
        assert isinstance(orders, list)

    def test_get_orders_by_shop_with_status(self, manager, mock_db):
        """Test getting orders by shop with status filter"""
        mock_db.fetch_all.return_value = []
        orders = manager.get_orders_by_shop(
            shop_id='shop_001',
            status=OrderStatus.SHIPPED,
        )
        assert isinstance(orders, list)

    # ===== 订单状态更新测试 =====
    def test_update_order_status(self, manager, mock_db):
        """Test updating order status"""
        # Mock get_order to return an order
        mock_db.fetch_one.return_value = {
            'id': 'ord_001',
            'platform_order_id': 'ext_001',
            'platform': 'douyin',
            'items': '[]',
            'subtotal': 0.0,
            'shipping_fee': 0.0,
            'discount': 0.0,
            'tax': 0.0,
            'total_amount': 0.0,
            'status': 'pending_payment',
            'payment_status': 'unpaid',
            'shipping_address': None,
            'logistics': None,
            'buyer_id': None,
            'buyer_nickname': None,
            'buyer_message': None,
            'created_at': datetime.now().isoformat(),
            'paid_at': None,
            'shipped_at': None,
            'completed_at': None,
            'shop_id': 'shop_001',
            'seller_note': None,
        }

        result = manager.update_order_status('ord_001', OrderStatus.PENDING_SHIP)
        assert result is True
        mock_db.execute.assert_called()

    def test_update_order_status_not_found(self, manager, mock_db):
        """Test updating status of non-existent order"""
        mock_db.fetch_one.return_value = None
        result = manager.update_order_status('nonexistent', OrderStatus.PENDING_SHIP)
        assert result is False

    def test_ship_order(self, manager, mock_db):
        """Test shipping an order"""
        mock_db.fetch_one.return_value = {
            'id': 'ord_001',
            'platform_order_id': 'ext_001',
            'platform': 'douyin',
            'items': '[]',
            'subtotal': 0.0,
            'shipping_fee': 0.0,
            'discount': 0.0,
            'tax': 0.0,
            'total_amount': 0.0,
            'status': 'pending_ship',
            'payment_status': 'paid',
            'shipping_address': None,
            'logistics': None,
            'buyer_id': None,
            'buyer_nickname': None,
            'buyer_message': None,
            'created_at': datetime.now().isoformat(),
            'paid_at': datetime.now().isoformat(),
            'shipped_at': None,
            'completed_at': None,
            'shop_id': 'shop_001',
            'seller_note': None,
        }

        result = manager.ship_order('ord_001', '顺丰速运', 'SF1234567890')
        assert result is True
        mock_db.execute.assert_called()

    def test_ship_order_not_found(self, manager, mock_db):
        """Test shipping non-existent order"""
        mock_db.fetch_one.return_value = None
        result = manager.ship_order('nonexistent', '顺丰', '123')
        assert result is False

    # ===== 订单统计测试 =====
    def test_get_order_statistics(self, manager, mock_db):
        """Test getting order statistics"""
        # Mock get_orders_by_shop to return sample orders
        sample_orders = [
            Order(
                id='ord_001',
                platform_order_id='ext_001',
                platform='douyin',
                items=[],
                total_amount=138.0,
                status=OrderStatus.COMPLETED,
                payment_status=PaymentStatus.PAID,
            ),
            Order(
                id='ord_002',
                platform_order_id='ext_002',
                platform='xiaohongshu',
                items=[],
                total_amount=256.0,
                status=OrderStatus.SHIPPED,
                payment_status=PaymentStatus.PAID,
            ),
        ]

        with patch.object(manager, 'get_orders_by_shop', return_value=sample_orders):
            stats = manager.get_order_statistics(
                shop_id='shop_001',
                start_date='2026-01-01',
                end_date='2026-12-31',
            )

        assert stats['total_orders'] == 2
        assert stats['total_amount'] == 394.0
        assert stats['paid_orders'] == 2
        assert 'status_distribution' in stats

    # ===== 订单搜索测试 =====
    def test_search_orders(self, manager, mock_db):
        """Test searching orders"""
        mock_db.fetch_all.return_value = []
        results = manager.search_orders(shop_id='shop_001', keyword='黑茶')
        assert isinstance(results, list)

    # ===== 同步订单测试 =====
    def test_sync_orders_from_platform(self, manager):
        """Test syncing orders from platform"""
        result = manager.sync_orders_from_platform(
            shop_id='shop_001',
            platform='douyin',
            start_time='2026-01-01',
            end_time='2026-12-31',
        )
        assert isinstance(result, dict)


class TestOrder:
    """Test Order dataclass"""

    @pytest.fixture
    def sample_items(self):
        """Create sample items"""
        return [
            OrderItem(
                product_id='prod_001',
                product_name='黑茶',
                sku_id='sku_001',
                sku_name='特级',
                quantity=2,
                unit_price=128.0,
                total_price=256.0,
            ),
        ]

    def test_order_creation(self, sample_items):
        """Test Order creation"""
        order = Order(
            id='ord_001',
            platform_order_id='ext_001',
            platform='douyin',
            items=sample_items,
        )
        assert order.id == 'ord_001'
        assert order.status == OrderStatus.PENDING_PAYMENT  # default
        assert order.payment_status == PaymentStatus.UNPAID  # default

    def test_calculate_total(self, sample_items):
        """Test calculate_total method"""
        order = Order(
            id='ord_001',
            platform_order_id='ext_001',
            platform='douyin',
            items=sample_items,
            shipping_fee=10.0,
            discount=20.0,
        )
        total = order.calculate_total()
        assert total == 246.0  # 256 + 10 - 20

    def test_get_item_count(self, sample_items):
        """Test get_item_count method"""
        order = Order(
            id='ord_001',
            platform_order_id='ext_001',
            platform='douyin',
            items=sample_items,
        )
        count = order.get_item_count()
        assert count == 2


class TestOrderItem:
    """Test OrderItem dataclass"""

    def test_order_item_creation(self):
        """Test OrderItem creation"""
        item = OrderItem(
            product_id='prod_001',
            product_name='黑茶',
            sku_id='sku_001',
            sku_name='特级黑茶',
            quantity=1,
            unit_price=128.0,
            total_price=128.0,
            image_url='https://example.com/tea.jpg',
        )
        assert item.product_id == 'prod_001'
        assert item.quantity == 1
        assert item.unit_price == 128.0


class TestShippingAddress:
    """Test ShippingAddress dataclass"""

    def test_address_creation(self):
        """Test ShippingAddress creation"""
        addr = ShippingAddress(
            name='张三',
            phone='13800138000',
            province='广东省',
            city='深圳市',
            district='南山区',
            detail='科技园南路1号',
            zip_code='518000',
        )
        assert addr.name == '张三'
        assert addr.phone == '13800138000'

    def test_get_full_address(self):
        """Test get_full_address method"""
        addr = ShippingAddress(
            name='张三',
            phone='13800138000',
            province='广东省',
            city='深圳市',
            district='南山区',
            detail='科技园南路1号',
        )
        full = addr.get_full_address()
        assert '广东省' in full
        assert '深圳市' in full
        assert '南山区' in full
        assert '科技园南路1号' in full


class TestLogisticsInfo:
    """Test LogisticsInfo dataclass"""

    def test_logistics_creation(self):
        """Test LogisticsInfo creation"""
        logistics = LogisticsInfo(
            company='顺丰速运',
            tracking_no='SF1234567890',
            status='in_transit',
        )
        assert logistics.company == '顺丰速运'
        assert logistics.tracking_no == 'SF1234567890'
        assert logistics.status == 'in_transit'
