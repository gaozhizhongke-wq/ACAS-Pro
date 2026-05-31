# -*- coding: utf-8 -*-
"""Tests for ecommerce/product_manager.py"""

import pytest
from datetime import datetime
from typing import List, Dict, Any
from unittest.mock import MagicMock, patch

from acas_pro.ecommerce.product_manager import (
    ProductManager,
    Product,
    ProductVariant,
    ProductImage,
    ProductStatus,
    ProductCategory,
)


class TestProductManager:
    """Test ProductManager class"""

    @pytest.fixture
    def mock_db(self):
        """Mock DatabaseManager"""
        db = MagicMock()
        db.fetchone.return_value = None
        db.fetchall.return_value = []
        db.execute.return_value = None
        return db

    @pytest.fixture
    def manager(self, mock_db):
        """Create ProductManager with mocked DB"""
        with patch('acas_pro.ecommerce.product_manager.DatabaseManager', return_value=mock_db):
            mgr = ProductManager()
            mgr.db = mock_db
            return mgr

    @pytest.fixture
    def sample_variants(self):
        """Create sample product variants"""
        return [
            ProductVariant(
                id='var_001',
                name='红色-大号',
                sku='SKU-RED-L',
                price=199.0,
                original_price=299.0,
                stock=50,
                is_default=True,
            ),
            ProductVariant(
                id='var_002',
                name='蓝色-中号',
                sku='SKU-BLUE-M',
                price=179.0,
                stock=30,
            ),
        ]

    @pytest.fixture
    def sample_images(self):
        """Create sample product images"""
        return [
            ProductImage(
                id='img_001',
                url='https://example.com/img1.jpg',
                is_main=True,
                sort_order=1,
            ),
            ProductImage(
                id='img_002',
                url='https://example.com/img2.jpg',
                is_main=False,
                sort_order=2,
            ),
        ]

    # ===== 初始化测试 =====
    def test_init(self, mock_db):
        """Test ProductManager initialization"""
        with patch('acas_pro.ecommerce.product_manager.DatabaseManager', return_value=mock_db):
            mgr = ProductManager()
            assert mgr.db is not None

    def test_init_database(self, manager, mock_db):
        """Test database initialization"""
        manager._init_database()
        assert mock_db.execute.called

    # ===== 枚举测试 =====
    def test_product_status_values(self):
        """Test ProductStatus enum values"""
        assert ProductStatus.DRAFT.value == 'draft'
        assert ProductStatus.PENDING.value == 'pending'
        assert ProductStatus.ACTIVE.value == 'active'
        assert ProductStatus.INACTIVE.value == 'inactive'
        assert ProductStatus.SOLD_OUT.value == 'sold_out'
        assert ProductStatus.VIOLATION.value == 'violation'

    def test_product_category_values(self):
        """Test ProductCategory enum values"""
        assert ProductCategory.FASHION.value == 'fashion'
        assert ProductCategory.BEAUTY.value == 'beauty'
        assert ProductCategory.FOOD.value == 'food'
        assert ProductCategory.HOME.value == 'home'
        assert ProductCategory.DIGITAL.value == 'digital'
        assert ProductCategory.MOTHER_BABY.value == 'mother_baby'
        assert ProductCategory.SPORTS.value == 'sports'
        assert ProductCategory.BOOKS.value == 'books'
        assert ProductCategory.PET.value == 'pet'
        assert ProductCategory.CAR.value == 'car'
        assert ProductCategory.JEWELRY.value == 'jewelry'
        assert ProductCategory.HEALTH.value == 'health'

    # ===== 商品创建测试 =====
    def test_create_product(self, manager, mock_db):
        """Test creating a product"""
        mock_db.execute.return_value = None

        product = manager.create_product(
            name='黑茶250g',
            category=ProductCategory.FOOD,
            price=128.0,
            shop_id='shop_001',
        )

        assert product is not None
        assert product.name == '黑茶250g'
        assert product.category == ProductCategory.FOOD
        assert product.price == 128.0
        assert product.status == ProductStatus.DRAFT  # default
        mock_db.execute.assert_called()

    def test_create_product_with_kwargs(self, manager, mock_db):
        """Test creating a product with additional kwargs"""
        mock_db.execute.return_value = None

        product = manager.create_product(
            name='茶具套装',
            category=ProductCategory.HOME,
            price=199.0,
            shop_id='shop_001',
            description='高档陶瓷茶具',
            stock=100,
        )

        assert product.description == '高档陶瓷茶具'
        assert product.stock == 100

    # ===== 商品查询测试 =====
    def test_get_product_found(self, manager, mock_db):
        """Test getting an existing product"""
        mock_db.fetchone.return_value = {
            'id': 'prod_001',
            'name': '黑茶',
            'description': '特级黑茶',
            'category': 'food',
            'sub_category': '茶叶',
            'price': 128.0,
            'original_price': 198.0,
            'cost_price': 80.0,
            'stock': 100,
            'stock_alert_threshold': 10,
            'has_variants': 0,
            'variants': '[]',
            'variant_attributes': '{}',
            'images': '[]',
            'main_image': None,
            'video_url': None,
            'weight': 0.25,
            'length': None,
            'width': None,
            'height': None,
            'status': 'draft',
            'platform_mappings': '{}',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'owner_id': 'owner_001',
            'shop_id': 'shop_001',
            'total_sales': 0,
            'monthly_sales': 0,
            'weekly_sales': 0,
        }

        product = manager.get_product('prod_001')
        assert product is not None
        assert product.id == 'prod_001'
        assert product.name == '黑茶'

    def test_get_product_not_found(self, manager, mock_db):
        """Test getting non-existent product"""
        mock_db.fetchone.return_value = None
        product = manager.get_product('nonexistent')
        assert product is None

    def test_get_products_by_shop(self, manager, mock_db):
        """Test getting products by shop"""
        mock_db.fetchall.return_value = []
        products = manager.get_products_by_shop(shop_id='shop_001')
        assert isinstance(products, list)

    def test_get_products_by_shop_with_status(self, manager, mock_db):
        """Test getting products by shop with status filter"""
        mock_db.fetchall.return_value = []
        products = manager.get_products_by_shop(
            shop_id='shop_001',
            status=ProductStatus.ACTIVE,
        )
        assert isinstance(products, list)

    # ===== 商品更新测试 =====
    def test_update_product(self, manager, mock_db):
        """Test updating a product"""
        # Mock get_product to return a product
        mock_db.fetchone.return_value = {
            'id': 'prod_001',
            'name': '黑茶',
            'description': '特级黑茶',
            'category': 'food',
            'sub_category': '',
            'price': 128.0,
            'original_price': None,
            'cost_price': None,
            'stock': 100,
            'stock_alert_threshold': 10,
            'has_variants': 0,
            'variants': '[]',
            'variant_attributes': '{}',
            'images': '[]',
            'main_image': None,
            'video_url': None,
            'weight': 0.0,
            'length': None,
            'width': None,
            'height': None,
            'status': 'draft',
            'platform_mappings': '{}',
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'owner_id': None,
            'shop_id': 'shop_001',
            'total_sales': 0,
            'monthly_sales': 0,
            'weekly_sales': 0,
        }

        result = manager.update_product('prod_001', {'name': '新黑茶', 'price': 148.0})
        assert result is True
        mock_db.execute.assert_called()

    def test_update_product_not_found(self, manager, mock_db):
        """Test updating non-existent product"""
        mock_db.fetchone.return_value = None
        result = manager.update_product('nonexistent', {'name': 'Test'})
        assert result is False

    # ===== 商品删除测试 =====
    def test_delete_product(self, manager, mock_db):
        """Test deleting a product"""
        result = manager.delete_product('prod_001')
        assert result is True
        mock_db.execute.assert_called()

    # ===== 库存更新测试 =====
    def test_update_stock(self, manager, mock_db):
        """Test updating product stock"""
        mock_db.fetchone.return_value = {
            'id': 'prod_001',
            'name': '黑茶',
            'has_variants': False,
            'variants': '[]',
            'stock': 100,
            'status': 'active',
        }

        with patch.object(manager, 'get_product') as mock_get:
            mock_get.return_value = Product(
                id='prod_001',
                name='黑茶',
                has_variants=False,
                stock=100,
            )
            result = manager.update_stock('prod_001', 50)
            assert result is True

    def test_update_stock_with_variant(self, manager, mock_db):
        """Test updating variant stock"""
        with patch.object(manager, 'get_product') as mock_get:
            mock_get.return_value = Product(
                id='prod_001',
                name='黑茶',
                has_variants=True,
                variants=[
                    ProductVariant(id='var_001', name='红色', sku='SKU-RED', price=199.0, stock=50),
                ],
            )
            result = manager.update_stock('prod_001', 20, variant_id='var_001')
            assert result is True

    # ===== 低库存测试 =====
    def test_get_low_stock_products(self, manager):
        """Test getting low stock products"""
        with patch.object(manager, 'get_products_by_shop') as mock_get:
            mock_get.return_value = [
                Product(
                    id='prod_001',
                    name='黑茶',
                    stock=5,  # Below threshold
                    stock_alert_threshold=10,
                ),
                Product(
                    id='prod_002',
                    name='茶具',
                    stock=50,  # Above threshold
                    stock_alert_threshold=10,
                ),
            ]
            low_stock = manager.get_low_stock_products('shop_001')
            assert len(low_stock) == 1
            assert low_stock[0].id == 'prod_001'

    # ===== 平台同步测试 =====
    def test_sync_to_platform(self, manager, mock_db):
        """Test syncing product to platform"""
        with patch.object(manager, 'get_product') as mock_get:
            mock_get.return_value = Product(
                id='prod_001',
                name='黑茶',
                category=ProductCategory.FOOD,
                price=128.0,
            )
            result = manager.sync_to_platform(
                product_id='prod_001',
                platform='douyin',
                platform_shop_id='shop_001',
            )
            assert isinstance(result, dict)

    def test_batch_sync_to_platform(self, manager):
        """Test batch syncing products to platform"""
        with patch.object(manager, 'sync_to_platform') as mock_sync:
            mock_sync.return_value = {'success': True, 'platform_product_id': 'douyin_prod_001'}
            results = manager.batch_sync_to_platform(
                product_ids=['prod_001', 'prod_002'],
                platform='douyin',
                platform_shop_id='shop_001',
            )
            assert results['total'] == 2
            assert results['success'] == 2
            assert results['failed'] == 0


class TestProduct:
    """Test Product dataclass"""

    def test_product_creation(self):
        """Test Product creation"""
        product = Product(
            id='prod_001',
            name='黑茶250g',
            category=ProductCategory.FOOD,
            price=128.0,
        )
        assert product.id == 'prod_001'
        assert product.name == '黑茶250g'
        assert product.status == ProductStatus.DRAFT  # default

    def test_get_display_price_no_variants(self):
        """Test get_display_price without variants"""
        product = Product(
            id='prod_001',
            name='黑茶',
            price=128.0,
        )
        display = product.get_display_price()
        assert '¥128.00' in display

    def test_get_display_price_with_variants(self):
        """Test get_display_price with variants"""
        product = Product(
            id='prod_001',
            name='黑茶',
            has_variants=True,
            variants=[
                ProductVariant(id='var_001', name='大号', sku='SKU-L', price=199.0, stock=50),
                ProductVariant(id='var_002', name='中号', sku='SKU-M', price=179.0, stock=30),
            ],
        )
        display = product.get_display_price()
        assert '¥179.00' in display
        assert '¥199.00' in display

    def test_get_total_stock_no_variants(self):
        """Test get_total_stock without variants"""
        product = Product(
            id='prod_001',
            name='黑茶',
            stock=100,
        )
        total = product.get_total_stock()
        assert total == 100

    def test_get_total_stock_with_variants(self):
        """Test get_total_stock with variants"""
        product = Product(
            id='prod_001',
            name='黑茶',
            has_variants=True,
            variants=[
                ProductVariant(id='var_001', name='大号', sku='SKU-L', price=199.0, stock=50),
                ProductVariant(id='var_002', name='中号', sku='SKU-M', price=179.0, stock=30),
            ],
        )
        total = product.get_total_stock()
        assert total == 80


class TestProductVariant:
    """Test ProductVariant dataclass"""

    def test_variant_creation(self):
        """Test ProductVariant creation"""
        variant = ProductVariant(
            id='var_001',
            name='红色-大号',
            sku='SKU-RED-L',
            price=199.0,
            original_price=299.0,
            stock=50,
            is_default=True,
        )
        assert variant.id == 'var_001'
        assert variant.name == '红色-大号'
        assert variant.price == 199.0
        assert variant.is_default is True


class TestProductImage:
    """Test ProductImage dataclass"""

    def test_image_creation(self):
        """Test ProductImage creation"""
        image = ProductImage(
            id='img_001',
            url='https://example.com/img1.jpg',
            is_main=True,
            sort_order=1,
        )
        assert image.id == 'img_001'
        assert image.is_main is True
        assert image.sort_order == 1
