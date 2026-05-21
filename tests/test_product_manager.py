#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Product Manager Tests
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from acas_pro.ecommerce.product_manager import (
    ProductManager, Product, ProductVariant, ProductImage,
    ProductStatus, ProductCategory
)


class TestProductStatus:
    """Product status enum tests"""
    
    def test_status_values(self):
        """Test status values"""
        assert ProductStatus.DRAFT.value == "draft"
        assert ProductStatus.ACTIVE.value == "active"
        assert ProductStatus.INACTIVE.value == "inactive"
        assert ProductStatus.SOLD_OUT.value == "sold_out"


class TestProductCategory:
    """Product category enum tests"""
    
    def test_category_values(self):
        """Test category values"""
        assert ProductCategory.FASHION.value == "fashion"
        assert ProductCategory.BEAUTY.value == "beauty"
        assert ProductCategory.FOOD.value == "food"
        assert ProductCategory.DIGITAL.value == "digital"


class TestProductVariant:
    """Product variant tests"""
    
    def test_variant_creation(self):
        """Test variant creation"""
        variant = ProductVariant(
            id="var_001",
            name="红色-大号",
            sku="SKU001",
            price=99.99,
            stock=100
        )
        
        assert variant.id == "var_001"
        assert variant.name == "红色-大号"
        assert variant.price == 99.99
        assert variant.stock == 100


class TestProductImage:
    """Product image tests"""
    
    def test_image_creation(self):
        """Test image creation"""
        image = ProductImage(
            id="img_001",
            url="https://example.com/image.jpg",
            is_main=True,
            sort_order=1
        )
        
        assert image.id == "img_001"
        assert image.is_main is True
        assert image.sort_order == 1


class TestProduct:
    """Product dataclass tests"""
    
    def test_product_creation(self):
        """Test product creation"""
        product = Product(
            id="prod_001",
            name="测试商品",
            category=ProductCategory.FASHION,
            price=99.99,
            stock=100
        )
        
        assert product.id == "prod_001"
        assert product.name == "测试商品"
        assert product.status == ProductStatus.DRAFT  # default
    
    def test_get_display_price_simple(self):
        """Test get display price simple"""
        product = Product(
            id="prod_001",
            name="Test",
            price=99.99
        )
        
        assert product.get_display_price() == "¥99.99"
    
    def test_get_display_price_with_variants(self):
        """Test get display price with variants"""
        product = Product(
            id="prod_001",
            name="Test",
            has_variants=True,
            variants=[
                ProductVariant(id="v1", name="S", sku="S001", price=99.0),
                ProductVariant(id="v2", name="L", sku="L001", price=129.0),
            ]
        )
        
        price_display = product.get_display_price()
        assert "¥99.0" in price_display
        assert "¥129.0" in price_display
    
    def test_get_total_stock_simple(self):
        """Test get total stock simple"""
        product = Product(
            id="prod_001",
            name="Test",
            stock=100
        )
        
        assert product.get_total_stock() == 100
    
    def test_get_total_stock_with_variants(self):
        """Test get total stock with variants"""
        product = Product(
            id="prod_001",
            name="Test",
            has_variants=True,
            variants=[
                ProductVariant(id="v1", name="S", sku="S001", price=99.0, stock=50),
                ProductVariant(id="v2", name="L", sku="L001", price=129.0, stock=30),
            ]
        )
        
        assert product.get_total_stock() == 80


class TestProductManager:
    """Product manager tests"""
    
    @pytest.fixture
    def mock_db(self):
        mock = Mock()
        mock.execute = Mock()
        mock.fetchone = Mock(return_value=None)
        mock.fetchall = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def manager(self, mock_db):
        with patch('acas_pro.ecommerce.product_manager.DatabaseManager', return_value=mock_db):
            from acas_pro.ecommerce.product_manager import ProductManager
            return ProductManager()
    
    def test_init(self, manager, mock_db):
        """Test initialization"""
        mock_db.execute.assert_called()
    
    def test_create_product(self, manager, mock_db):
        """Test create product"""
        product = manager.create_product(
            name="测试商品",
            category=ProductCategory.FASHION,
            price=99.99,
            owner_id="user_001",
            shop_id="shop_001"
        )
        
        assert product.name == "测试商品"
        assert product.category == ProductCategory.FASHION
        assert product.price == 99.99
        assert product.owner_id == "user_001"
        mock_db.execute.assert_called()
    
    def test_get_product_not_found(self, manager, mock_db):
        """Test get product not found"""
        mock_db.fetchone.return_value = None
        
        result = manager.get_product("nonexistent")
        
        assert result is None
    
    def test_get_products_by_shop_empty(self, manager, mock_db):
        """Test get products by shop empty"""
        mock_db.fetchall.return_value = []
        
        products = manager.get_products_by_shop("shop_001")
        
        assert products == []
    
    def test_update_product_not_found(self, manager, mock_db):
        """Test update product not found"""
        mock_db.fetchone.return_value = None
        
        result = manager.update_product("nonexistent", {"price": 199.0})
        
        assert result is False
    
    def test_delete_product(self, manager, mock_db):
        """Test delete product"""
        result = manager.delete_product("prod_001")
        
        assert result is True
        mock_db.execute.assert_called()
    
    def test_update_stock_not_found(self, manager, mock_db):
        """Test update stock not found"""
        mock_db.fetchone.return_value = None
        
        result = manager.update_stock("nonexistent", 10)
        
        assert result is False
    
    def test_get_low_stock_products_empty(self, manager, mock_db):
        """Test get low stock products empty"""
        mock_db.fetchall.return_value = []
        
        products = manager.get_low_stock_products("shop_001")
        
        assert products == []
    
    def test_sync_to_platform_not_found(self, manager, mock_db):
        """Test sync to platform product not found"""
        mock_db.fetchone.return_value = None
        
        result = manager.sync_to_platform("nonexistent", "douyin", "shop_001")
        
        assert result['success'] is False
        assert 'error' in result
    
    def test_batch_sync_to_platform(self, manager, mock_db):
        """Test batch sync to platform"""
        mock_db.fetchone.return_value = None
        
        result = manager.batch_sync_to_platform(
            ["prod_001", "prod_002"],
            "douyin",
            "shop_001"
        )
        
        assert result['total'] == 2
        assert result['failed'] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
