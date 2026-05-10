#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Order Manager Tests
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from acas_pro.ecommerce.order_manager import (
    OrderManager, Order, OrderItem, ShippingAddress, LogisticsInfo,
    OrderStatus, PaymentStatus
)


class TestOrderStatus:
    """Order status enum tests"""
    
    def test_status_values(self):
        """Test status values"""
        assert OrderStatus.PENDING_PAYMENT.value == "pending_payment"
        assert OrderStatus.PENDING_SHIP.value == "pending_ship"
        assert OrderStatus.SHIPPED.value == "shipped"
        assert OrderStatus.DELIVERED.value == "delivered"
        assert OrderStatus.COMPLETED.value == "completed"
        assert OrderStatus.CANCELLED.value == "cancelled"


class TestPaymentStatus:
    """Payment status enum tests"""
    
    def test_payment_status_values(self):
        """Test payment status values"""
        assert PaymentStatus.UNPAID.value == "unpaid"
        assert PaymentStatus.PAID.value == "paid"
        assert PaymentStatus.PARTIAL.value == "partial"
        assert PaymentStatus.REFUNDED.value == "refunded"


class TestOrderItem:
    """Order item tests"""
    
    def test_item_creation(self):
        """Test item creation"""
        item = OrderItem(
            product_id="prod_001",
            product_name="测试商品",
            sku_id="sku_001",
            sku_name="红色-L",
            quantity=2,
            unit_price=99.99,
            total_price=199.98
        )
        
        assert item.product_id == "prod_001"
        assert item.quantity == 2
        assert item.total_price == 199.98


class TestShippingAddress:
    """Shipping address tests"""
    
    def test_address_creation(self):
        """Test address creation"""
        addr = ShippingAddress(
            name="张三",
            phone="13800138000",
            province="广东省",
            city="深圳市",
            district="南山区",
            detail="科技园"
        )
        
        assert addr.name == "张三"
        assert addr.province == "广东省"
    
    def test_get_full_address(self):
        """Test get full address"""
        addr = ShippingAddress(
            name="张三",
            phone="13800138000",
            province="广东省",
            city="深圳市",
            district="南山区",
            detail="科技园"
        )
        
        full = addr.get_full_address()
        assert "广东省" in full
        assert "深圳市" in full
        assert "南山区" in full
        assert "科技园" in full


class TestLogisticsInfo:
    """Logistics info tests"""
    
    def test_logistics_creation(self):
        """Test logistics creation"""
        logistics = LogisticsInfo(
            company="顺丰速运",
            tracking_no="SF1234567890"
        )
        
        assert logistics.company == "顺丰速运"
        assert logistics.status == "pending"  # default


class TestOrder:
    """Order dataclass tests"""
    
    def test_order_creation(self):
        """Test order creation"""
        order = Order(
            id="ord_001",
            platform_order_id="plat_123",
            platform="douyin"
        )
        
        assert order.id == "ord_001"
        assert order.platform == "douyin"
        assert order.status == OrderStatus.PENDING_PAYMENT  # default
        assert order.payment_status == PaymentStatus.UNPAID  # default
    
    def test_calculate_total(self):
        """Test calculate total"""
        order = Order(
            id="ord_001",
            platform_order_id="plat_123",
            platform="douyin",
            items=[
                OrderItem(
                    product_id="p1",
                    product_name="Item1",
                    sku_id=None,
                    sku_name=None,
                    quantity=2,
                    unit_price=50.0,
                    total_price=100.0
                ),
                OrderItem(
                    product_id="p2",
                    product_name="Item2",
                    sku_id=None,
                    sku_name=None,
                    quantity=1,
                    unit_price=80.0,
                    total_price=80.0
                ),
            ],
            shipping_fee=10.0,
            discount=5.0
        )
        
        total = order.calculate_total()
        assert order.subtotal == 180.0
        assert total == 185.0  # 180 + 10 - 5
    
    def test_get_item_count(self):
        """Test get item count"""
        order = Order(
            id="ord_001",
            platform_order_id="plat_123",
            platform="douyin",
            items=[
                OrderItem(
                    product_id="p1",
                    product_name="Item1",
                    sku_id=None,
                    sku_name=None,
                    quantity=2,
                    unit_price=50.0,
                    total_price=100.0
                ),
                OrderItem(
                    product_id="p2",
                    product_name="Item2",
                    sku_id=None,
                    sku_name=None,
                    quantity=3,
                    unit_price=30.0,
                    total_price=90.0
                ),
            ]
        )
        
        assert order.get_item_count() == 5  # 2 + 3


class TestOrderManager:
    """Order manager tests"""
    
    @pytest.fixture
    def mock_db(self):
        mock = Mock()
        mock.execute = Mock()
        mock.fetch_one = Mock(return_value=None)
        mock.fetch_all = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def manager(self, mock_db):
        with patch('acas_pro.ecommerce.order_manager.DatabaseManager', return_value=mock_db):
            return OrderManager()
    
    def test_init(self, manager, mock_db):
        """Test initialization"""
        mock_db.execute.assert_called()
    
    def test_create_order(self, manager, mock_db):
        """Test create order"""
        address = ShippingAddress(
            name="张三",
            phone="13800138000",
            province="广东省",
            city="深圳市",
            district="南山区",
            detail="科技园"
        )
        
        order = manager.create_order(
            platform_order_id="plat_123",
            platform="douyin",
            items=[
                OrderItem(
                    product_id="p1",
                    product_name="Item1",
                    sku_id=None,
                    sku_name=None,
                    quantity=1,
                    unit_price=99.99,
                    total_price=99.99
                )
            ],
            shipping_address=address,
            shop_id="shop_001"
        )
        
        assert order.platform_order_id == "plat_123"
        assert order.platform == "douyin"
        assert order.shop_id == "shop_001"
        mock_db.execute.assert_called()
    
    def test_get_order_not_found(self, manager, mock_db):
        """Test get order not found"""
        mock_db.fetch_one.return_value = None
        
        result = manager.get_order("nonexistent")
        
        assert result is None
    
    def test_get_orders_by_shop_empty(self, manager, mock_db):
        """Test get orders by shop empty"""
        mock_db.fetch_all.return_value = []
        
        orders = manager.get_orders_by_shop("shop_001")
        
        assert orders == []
    
    def test_update_order_status_not_found(self, manager, mock_db):
        """Test update order status not found"""
        mock_db.fetch_one.return_value = None
        
        result = manager.update_order_status("nonexistent", OrderStatus.SHIPPED)
        
        assert result is False
    
    def test_ship_order_not_found(self, manager, mock_db):
        """Test ship order not found"""
        mock_db.fetch_one.return_value = None
        
        result = manager.ship_order("nonexistent", "顺丰", "SF123")
        
        assert result is False
    
    def test_sync_orders_from_platform(self, manager):
        """Test sync orders from platform"""
        result = manager.sync_orders_from_platform(
            "shop_001",
            "douyin",
            "2024-01-01T00:00:00",
            "2024-01-31T23:59:59"
        )
        
        assert result['success'] is True
        assert 'synced_count' in result
    
    def test_get_order_statistics_empty(self, manager, mock_db):
        """Test get order statistics empty"""
        mock_db.fetch_all.return_value = []
        
        stats = manager.get_order_statistics(
            "shop_001",
            "2024-01-01",
            "2024-01-31"
        )
        
        assert stats['total_orders'] == 0
        assert stats['total_amount'] == 0.0
        assert stats['average_order_value'] == 0.0
    
    def test_search_orders_empty(self, manager, mock_db):
        """Test search orders empty"""
        mock_db.fetch_all.return_value = []
        
        orders = manager.search_orders("shop_001", "keyword")
        
        assert orders == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
