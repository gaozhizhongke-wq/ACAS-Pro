#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for ecommerce modules (order, product, shop managers)."""

from unittest.mock import MagicMock
import sys

if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()


# ============================================================
# ORDER MANAGER
# ============================================================
class TestOrderStatusEnum:
    def test_values(self):
        from acas_pro.ecommerce.order_manager import OrderStatus
        assert OrderStatus.PENDING_PAYMENT.value is not None
        assert len(list(OrderStatus)) >= 5

class TestPaymentStatusEnum:
    def test_values(self):
        from acas_pro.ecommerce.order_manager import PaymentStatus
        assert PaymentStatus.PAID.value is not None
        assert len(list(PaymentStatus)) >= 3

class TestOrderItem:
    def test_create(self):
        from acas_pro.ecommerce.order_manager import OrderItem
        item = OrderItem(product_id="p1", product_name="Widget", sku_id="s1", sku_name="Red", quantity=2, unit_price=9.99, total_price=19.98)
        assert item.product_id == "p1"
        assert item.quantity == 2

class TestShippingAddress:
    def test_create(self):
        from acas_pro.ecommerce.order_manager import ShippingAddress
        addr = ShippingAddress(name="张三", phone="13800138000", province="北京", city="北京", district="朝阳", detail="xx路1号")
        assert addr.province == "北京"

class TestLogisticsInfo:
    def test_create(self):
        from acas_pro.ecommerce.order_manager import LogisticsInfo
        li = LogisticsInfo(company="顺丰", tracking_no="SF123", status="shipped", shipped_at="2026-01-01", delivered_at=None, tracking_history=[])
        assert li.company == "顺丰"

class TestOrder:
    def test_create(self):
        from acas_pro.ecommerce.order_manager import Order
        order = Order(id="o1", platform_order_id="po1", platform="douyin", items=[], subtotal=100.0, shipping_fee=10.0)
        assert order.id == "o1"

class TestOrderManager:
    def test_create(self):
        from acas_pro.ecommerce.order_manager import OrderManager
        om = OrderManager()
        assert om is not None


# ============================================================
# PRODUCT MANAGER
# ============================================================
class TestProductCategoryEnum:
    def test_values(self):
        from acas_pro.ecommerce.product_manager import ProductCategory
        assert len(list(ProductCategory)) >= 5

class TestProductStatusEnum:
    def test_values(self):
        from acas_pro.ecommerce.product_manager import ProductStatus
        assert len(list(ProductStatus)) >= 4

class TestProductImage:
    def test_create(self):
        from acas_pro.ecommerce.product_manager import ProductImage
        img = ProductImage(id="img1", url="https://img.example.com/1.jpg", is_main=True, sort_order=0)
        assert img.is_main

class TestProductVariant:
    def test_create(self):
        from acas_pro.ecommerce.product_manager import ProductVariant
        pv = ProductVariant(id="v1", name="红色L码", sku="SKU-RED-L", price=99.0, original_price=129.0, stock=50)
        assert pv.sku == "SKU-RED-L"

class TestProduct:
    def test_create(self):
        from acas_pro.ecommerce.product_manager import Product
        p = Product(id="p1", name="测试商品", description="desc", category="DIGITAL", sub_category="phone", price=2999.0)
        assert p.name == "测试商品"

class TestProductManager:
    def test_create(self):
        from acas_pro.ecommerce.product_manager import ProductManager
        pm = ProductManager()
        assert pm is not None


# ============================================================
# SHOP MANAGER
# ============================================================
class TestShopPlatformEnum:
    def test_values(self):
        from acas_pro.ecommerce.shop_manager import ShopPlatform
        assert len(list(ShopPlatform)) >= 4

class TestShopStatusEnum:
    def test_values(self):
        from acas_pro.ecommerce.shop_manager import ShopStatus
        assert len(list(ShopStatus)) >= 4

class TestShopCredentials:
    def test_create(self):
        from acas_pro.ecommerce.shop_manager import ShopCredentials
        sc = ShopCredentials(app_key="key", app_secret="secret", access_token="at", refresh_token="rt", expires_at="2026-12-31")
        assert sc.app_key == "key"

class TestShopStats:
    def test_create(self):
        from acas_pro.ecommerce.shop_manager import ShopStats
        ss = ShopStats(total_products=100, total_orders_today=5, total_orders_month=150, revenue_today=5000.0, revenue_month=75000.0, visitors_today=200)
        assert ss.total_products == 100

class TestShop:
    def test_create(self):
        from acas_pro.ecommerce.shop_manager import Shop
        s = Shop(id="s1", name="我的店铺", platform="douyin", status="active", shop_id_on_platform="dp123", shop_url="https://shop.douyin.com/dp123")
        assert s.name == "我的店铺"

class TestShopManager:
    def test_create(self):
        from acas_pro.ecommerce.shop_manager import ShopManager
        sm = ShopManager()
        assert sm is not None

    def test_platform_list(self):
        from acas_pro.ecommerce.shop_manager import ShopManager
        sm = ShopManager()
        platforms = sm.get_platform_list()
        assert isinstance(platforms, (list, dict))
