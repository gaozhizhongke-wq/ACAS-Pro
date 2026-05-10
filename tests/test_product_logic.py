#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Product Logic Tests
"""

import pytest
from datetime import datetime

from acas_pro.ui.logic.product_logic import (
    ProductLogic, Product, ProductStatus
)


class TestProductStatus:
    def test_status_values(self):
        assert ProductStatus.ACTIVE.value == "active"
        assert ProductStatus.OUT_OF_STOCK.value == "out_of_stock"
        assert ProductStatus.DRAFT.value == "draft"


class TestProduct:
    def test_product_creation(self):
        product = Product(
            id="prod001",
            name="Test Product",
            description="Test desc",
            price=99.99,
            cost=50.0,
            stock_quantity=100,
            status=ProductStatus.ACTIVE,
            category="Electronics",
            tags=["new"],
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert product.name == "Test Product"
        assert product.price == 99.99


class TestProductLogic:
    @pytest.fixture
    def logic(self):
        return ProductLogic()

    def test_init(self, logic):
        assert logic._products == {}

    def test_create_product(self, logic):
        product = logic.create_product(
            name="Laptop",
            description="Gaming laptop",
            price=999.99,
            cost=700.0,
            stock=50,
            category="Electronics",
            tags=["gaming", "new"]
        )
        assert product.name == "Laptop"
        assert product.price == 999.99
        assert product.status == ProductStatus.ACTIVE
        assert len(product.id) == 8

    def test_create_product_out_of_stock(self, logic):
        product = logic.create_product(
            name="Out of Stock Item",
            description="No stock",
            price=99.99,
            stock=0
        )
        assert product.status == ProductStatus.OUT_OF_STOCK

    def test_update_product(self, logic):
        product = logic.create_product(name="Test", description="Desc", price=100)
        result = logic.update_product(product.id, name="Updated", price=150)
        assert result is True
        assert product.name == "Updated"
        assert product.price == 150

    def test_update_nonexistent_product(self, logic):
        result = logic.update_product("nonexistent", name="Test")
        assert result is False

    def test_get_product(self, logic):
        product = logic.create_product(name="Test", description="Desc", price=100)
        fetched = logic.get_product(product.id)
        assert fetched == product

    def test_list_products(self, logic):
        logic.create_product(name="P1", description="D1", price=100, category="A")
        logic.create_product(name="P2", description="D2", price=200, category="B")
        products = logic.list_products()
        assert len(products) == 2

    def test_list_products_by_category(self, logic):
        logic.create_product(name="P1", description="D1", price=100, category="A")
        logic.create_product(name="P2", description="D2", price=200, category="B")
        products = logic.list_products(category="A")
        assert len(products) == 1
        assert products[0].name == "P1"

    def test_list_products_by_status(self, logic):
        p1 = logic.create_product(name="P1", description="D1", price=100, stock=10)
        p2 = logic.create_product(name="P2", description="D2", price=200, stock=0)
        products = logic.list_products(status=ProductStatus.OUT_OF_STOCK)
        assert len(products) == 1
        assert products[0].name == "P2"

    def test_list_products_by_search(self, logic):
        logic.create_product(name="Laptop Pro", description="Gaming", price=1000)
        logic.create_product(name="Mouse", description="Wireless", price=50)
        products = logic.list_products(search="laptop")
        assert len(products) == 1
        assert products[0].name == "Laptop Pro"

    def test_update_stock(self, logic):
        product = logic.create_product(name="Test", description="Desc", price=100, stock=10)
        result = logic.update_stock(product.id, 50)
        assert result is True
        assert product.stock_quantity == 50

    def test_update_stock_to_zero(self, logic):
        product = logic.create_product(name="Test", description="Desc", price=100, stock=10)
        logic.update_stock(product.id, 0)
        assert product.status == ProductStatus.OUT_OF_STOCK

    def test_update_stock_restock(self, logic):
        product = logic.create_product(name="Test", description="Desc", price=100, stock=0)
        logic.update_stock(product.id, 10)
        assert product.status == ProductStatus.ACTIVE

    def test_calculate_profit_margin(self, logic):
        product = logic.create_product(name="Test", description="Desc", price=200, cost=150)
        margin = logic.calculate_profit_margin(product.id)
        assert margin == 25.0

    def test_calculate_profit_margin_zero_price(self, logic):
        product = logic.create_product(name="Test", description="Desc", price=0, cost=100)
        margin = logic.calculate_profit_margin(product.id)
        assert margin == 0.0

    def test_get_low_stock_products(self, logic):
        logic.create_product(name="Low", description="D", price=100, stock=5)
        logic.create_product(name="Normal", description="D", price=100, stock=50)
        low_stock = logic.get_low_stock_products(threshold=10)
        assert len(low_stock) == 1
        assert low_stock[0].name == "Low"

    def test_get_category_summary(self, logic):
        logic.create_product(name="P1", description="D", price=100, category="A")
        logic.create_product(name="P2", description="D", price=100, category="A")
        logic.create_product(name="P3", description="D", price=100, category="B")
        summary = logic.get_category_summary()
        assert summary["A"] == 2
        assert summary["B"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
