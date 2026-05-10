#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Business Logic Tests
Tests for order and product logic
"""

import pytest
from datetime import datetime

from acas_pro.ui.logic import (
    OrderLogic, Order, OrderItem, OrderStatus, PaymentStatus,
    ProductLogic, Product, ProductStatus
)


class TestOrderLogic:
    """Order logic tests"""
    
    @pytest.fixture
    def orders(self):
        return OrderLogic()
    
    def test_create_order(self, orders):
        """Test order creation"""
        items = [
            {"product_id": "P001", "product_name": "Product A", "quantity": 2, "unit_price": 50.0},
            {"product_id": "P002", "product_name": "Product B", "quantity": 1, "unit_price": 100.0},
        ]
        
        order = orders.create_order(
            customer_id="C001",
            customer_name="Test Customer",
            items=items,
            shipping_address="123 Test St"
        )
        
        assert order.customer_id == "C001"
        assert order.total_amount == 200.0  # 2*50 + 1*100
        assert order.status == OrderStatus.PENDING
        assert len(order.items) == 2
    
    def test_update_status(self, orders):
        """Test status update"""
        order = orders.create_order("C001", "Test", [], "Address")
        
        result = orders.update_status(order.id, OrderStatus.CONFIRMED)
        
        assert result is True
        assert order.status == OrderStatus.CONFIRMED
    
    def test_update_payment(self, orders):
        """Test payment update"""
        order = orders.create_order("C001", "Test", [], "Address")
        
        result = orders.update_payment(order.id, PaymentStatus.PAID)
        
        assert result is True
        assert order.payment_status == PaymentStatus.PAID
    
    def test_get_order(self, orders):
        """Test get order"""
        order = orders.create_order("C001", "Test", [], "Address")
        fetched = orders.get_order(order.id)
        
        assert fetched == order
    
    def test_list_orders(self, orders):
        """Test list orders"""
        orders.create_order("C001", "Customer 1", [], "Addr1")
        orders.create_order("C002", "Customer 2", [], "Addr2")
        
        all_orders = orders.list_orders()
        
        assert len(all_orders) == 2
    
    def test_list_orders_by_status(self, orders):
        """Test filter by status"""
        order1 = orders.create_order("C001", "Test", [], "Addr")
        orders.update_status(order1.id, OrderStatus.SHIPPED)
        orders.create_order("C002", "Test2", [], "Addr")
        
        shipped = orders.list_orders(status=OrderStatus.SHIPPED)
        
        assert len(shipped) == 1
    
    def test_calculate_revenue(self, orders):
        """Test revenue calculation"""
        items = [{"product_id": "P001", "product_name": "Product", "quantity": 1, "unit_price": 100.0}]
        
        order = orders.create_order("C001", "Test", items, "Addr")
        orders.update_payment(order.id, PaymentStatus.PAID)
        
        result = orders.calculate_revenue(
            datetime(2026, 1, 1),
            datetime(2026, 12, 31)
        )
        
        assert result["total_revenue"] == 100.0
        assert result["order_count"] == 1
    
    def test_get_status_summary(self, orders):
        """Test status summary"""
        orders.create_order("C001", "Test", [], "Addr")
        
        summary = orders.get_status_summary()
        
        assert summary["pending"] == 1


class TestProductLogic:
    """Product logic tests"""
    
    @pytest.fixture
    def products(self):
        return ProductLogic()
    
    def test_create_product(self, products):
        """Test product creation"""
        product = products.create_product(
            name="Test Product",
            description="A test product",
            price=99.99,
            cost=50.0,
            stock=100,
            category="Electronics",
            tags=["new", "featured"]
        )
        
        assert product.name == "Test Product"
        assert product.price == 99.99
        assert product.stock_quantity == 100
        assert product.status == ProductStatus.ACTIVE
    
    def test_create_product_out_of_stock(self, products):
        """Test product with no stock"""
        product = products.create_product(
            name="Out of Stock",
            description="No stock",
            price=50.0,
            stock=0
        )
        
        assert product.status == ProductStatus.OUT_OF_STOCK
    
    def test_update_product(self, products):
        """Test product update"""
        product = products.create_product("Test", "Desc", 100.0)
        
        result = products.update_product(product.id, price=150.0, name="Updated")
        
        assert result is True
        assert product.price == 150.0
        assert product.name == "Updated"
    
    def test_update_stock(self, products):
        """Test stock update"""
        product = products.create_product("Test", "Desc", 100.0, stock=10)
        
        result = products.update_stock(product.id, 50)
        
        assert result is True
        assert product.stock_quantity == 50
    
    def test_update_stock_to_zero(self, products):
        """Test stock update to zero"""
        product = products.create_product("Test", "Desc", 100.0, stock=10)
        
        products.update_stock(product.id, 0)
        
        assert product.status == ProductStatus.OUT_OF_STOCK
    
    def test_calculate_profit_margin(self, products):
        """Test profit margin calculation"""
        product = products.create_product("Test", "Desc", price=100.0, cost=60.0)
        
        margin = products.calculate_profit_margin(product.id)
        
        assert margin == 40.0  # (100-60)/100 * 100
    
    def test_get_low_stock_products(self, products):
        """Test low stock detection"""
        products.create_product("Normal", "Desc", 100.0, stock=100)
        products.create_product("Low", "Desc", 100.0, stock=5)
        
        low_stock = products.get_low_stock_products(threshold=10)
        
        assert len(low_stock) == 1
        assert low_stock[0].name == "Low"
    
    def test_list_products_by_category(self, products):
        """Test filter by category"""
        products.create_product("Phone", "Smartphone", 999.0, category="Electronics")
        products.create_product("Shirt", "T-shirt", 29.0, category="Clothing")
        
        electronics = products.list_products(category="Electronics")
        
        assert len(electronics) == 1
        assert electronics[0].name == "Phone"
    
    def test_list_products_search(self, products):
        """Test search"""
        products.create_product("iPhone 15", "Apple phone", 999.0)
        products.create_product("Samsung S24", "Android phone", 899.0)
        products.create_product("MacBook", "Laptop", 1999.0)
        
        phones = products.list_products(search="phone")
        
        assert len(phones) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
