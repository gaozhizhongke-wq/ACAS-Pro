# -*- coding: utf-8 -*-
"""Tests for ecommerce/supply_chain.py"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from acas_pro.ecommerce.supply_chain import (
    SupplyChainManager,
    Supplier,
    SupplierStatus,
    InventorySync,
    InventorySyncStatus,
    PurchaseOrder,
)


class TestSupplyChainManager:
    """Test SupplyChainManager class"""

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
        """Create SupplyChainManager with mocked DB"""
        with patch('acas_pro.ecommerce.supply_chain.DatabaseManager', return_value=mock_db):
            mgr = SupplyChainManager()
            mgr.db = mock_db
            return mgr

    # ===== 初始化测试 =====
    def test_init(self, mock_db):
        """Test SupplyChainManager initialization"""
        with patch('acas_pro.ecommerce.supply_chain.DatabaseManager', return_value=mock_db):
            mgr = SupplyChainManager()
            assert mgr.db is not None

        # _init_database removed — schema managed by core/schema.py
        """Test database initialization"""
        # _init_database removed — schema managed by core/schema.py
        pass  # schema centralized — no execute during init

    # ===== 枚举测试 =====
    def test_supplier_status_values(self):
        """Test SupplierStatus enum values"""
        assert SupplierStatus.ACTIVE.value == 'active'
        assert SupplierStatus.PENDING.value == 'pending'
        assert SupplierStatus.SUSPENDED.value == 'suspended'
        assert SupplierStatus.TERMINATED.value == 'terminated'

    def test_inventory_sync_status_values(self):
        """Test InventorySyncStatus enum values"""
        assert InventorySyncStatus.SYNCED.value == 'synced'
        assert InventorySyncStatus.PENDING.value == 'pending'
        assert InventorySyncStatus.SYNCING.value == 'syncing'
        assert InventorySyncStatus.FAILED.value == 'failed'

    # ===== 供应商创建测试 =====
    def test_create_supplier(self, manager, mock_db):
        """Test creating a supplier"""
        mock_db.execute.return_value = None

        supplier = manager.create_supplier(
            name='测试供应商',
            contact_person='张三',
            contact_phone='13800138000',
            owner_id='owner_001',
        )

        assert supplier is not None
        assert supplier.name == '测试供应商'
        assert supplier.contact_person == '张三'
        assert supplier.status == SupplierStatus.ACTIVE  # default
        mock_db.execute.assert_called()

    def test_create_supplier_with_kwargs(self, manager, mock_db):
        """Test creating a supplier with additional kwargs"""
        mock_db.execute.return_value = None

        supplier = manager.create_supplier(
            name='茶叶供应商',
            contact_person='李四',
            contact_phone='13900139000',
            owner_id='owner_001',
            company_name='云南茶叶有限公司',
            rating=4.5,
        )

        assert supplier.company_name == '云南茶叶有限公司'
        assert supplier.rating == 4.5

    # ===== 供应商查询测试 =====
    def test_get_supplier_found(self, manager, mock_db):
        """Test getting an existing supplier"""
        mock_db.fetchone.return_value = {
            'id': 'sup_001',
            'name': '测试供应商',
            'contact_person': '张三',
            'contact_phone': '13800138000',
            'contact_email': None,
            'company_name': None,
            'business_license': None,
            'address': None,
            'main_products': '[]',
            'supply_categories': '[]',
            'rating': 5.0,
            'cooperation_count': 0,
            'status': 'active',
            'payment_terms': '月结30天',
            'created_at': datetime.now().isoformat(),
            'owner_id': 'owner_001',
            'notes': None,
        }

        supplier = manager.get_supplier('sup_001')
        assert supplier is not None
        assert supplier.id == 'sup_001'
        assert supplier.name == '测试供应商'

    def test_get_supplier_not_found(self, manager, mock_db):
        """Test getting non-existent supplier"""
        mock_db.fetchone.return_value = None
        supplier = manager.get_supplier('nonexistent')
        assert supplier is None

    def test_get_suppliers_by_owner(self, manager, mock_db):
        """Test getting suppliers by owner"""
        mock_db.fetchall.return_value = []
        suppliers = manager.get_suppliers_by_owner(owner_id='owner_001')
        assert isinstance(suppliers, list)

    # ===== 库存同步测试 =====
    def test_sync_inventory_product_not_found(self, manager):
        """Test syncing inventory with non-existent product"""
        # Mock ProductManager class (imported inside sync_inventory)
        with patch('acas_pro.ecommerce.product_manager.ProductManager') as mock_pm_class:
            mock_pm_instance = MagicMock()
            mock_pm_instance.get_product.return_value = None
            mock_pm_class.return_value = mock_pm_instance

            with pytest.raises(ValueError):
                manager.sync_inventory(
                    product_id='prod_nonexistent',
                    shop_id='shop_001',
                    new_quantity=100,
                )

    def test_sync_inventory_success(self, manager, mock_db):
        """Test successful inventory sync"""
        # Mock ProductManager class (imported inside sync_inventory)
        with patch('acas_pro.ecommerce.product_manager.ProductManager') as mock_pm_class:
            # Mock product
            mock_product = MagicMock()
            mock_product.get_total_stock.return_value = 50
            mock_product.has_variants = False
            mock_product.stock = 50

            mock_pm_instance = MagicMock()
            mock_pm_instance.get_product.return_value = mock_product
            mock_pm_class.return_value = mock_pm_instance

            # Mock _sync_to_platforms to raise NotImplementedError (stub)
            with patch.object(manager, '_sync_to_platforms', side_effect=NotImplementedError('Stub')):
                sync_record = manager.sync_inventory(
                    product_id='prod_001',
                    shop_id='shop_001',
                    new_quantity=100,
                )

                assert sync_record is not None
                assert isinstance(sync_record, InventorySync)
                assert sync_record.quantity_before == 50
                assert sync_record.quantity_after == 100
                assert sync_record.quantity_changed == 50

    # ===== 采购订单测试 =====
    def test_create_purchase_order(self, manager, mock_db):
        """Test creating a purchase order"""
        mock_db.execute.return_value = None

        items = [
            {'product_id': 'prod_001', 'product_name': '黑茶', 'quantity': 10, 'unit_price': 128.0},
            {'product_id': 'prod_002', 'product_name': '茶具', 'quantity': 5, 'unit_price': 199.0},
        ]

        order = manager.create_purchase_order(
            supplier_id='sup_001',
            items=items,
            expected_delivery='2026-06-01',
            notes='测试采购',
        )

        assert order is not None
        assert order.supplier_id == 'sup_001'
        assert len(order.items) == 2
        assert order.subtotal == 10 * 128.0 + 5 * 199.0
        assert order.total_amount == order.subtotal  # No shipping fee
        mock_db.execute.assert_called()

    # ===== 采购订单查询测试 =====
    def test_get_purchase_orders_by_supplier(self, manager, mock_db):
        """Test getting purchase orders by supplier"""
        mock_db.fetchall.return_value = []
        orders = manager.get_purchase_orders_by_supplier(supplier_id='sup_001')
        assert isinstance(orders, list)

    def test_get_purchase_orders_by_supplier_with_status(self, manager, mock_db):
        """Test getting purchase orders by supplier with status filter"""
        mock_db.fetchall.return_value = []
        orders = manager.get_purchase_orders_by_supplier(
            supplier_id='sup_001',
            status='pending',
        )
        assert isinstance(orders, list)

    # ===== 采购订单状态更新测试 =====
    def test_update_purchase_order_status_not_found(self, manager, mock_db):
        """Test updating status of non-existent purchase order"""
        mock_db.fetchone.return_value = None
        result = manager.update_purchase_order_status('nonexistent', 'confirmed')
        assert result is False

    # ===== 物流追踪测试 =====
    def test_track_logistics(self, manager):
        """Test tracking logistics"""
        result = manager.track_logistics('顺丰速运', 'SF1234567890')
        assert isinstance(result, dict)

    # ===== 低库存预警测试 =====
    def test_get_low_stock_alerts(self, manager):
        """Test getting low stock alerts"""
        # Mock ShopManager and ProductManager (imported inside get_low_stock_alerts)
        with patch('acas_pro.ecommerce.shop_manager.ShopManager') as mock_sm_class:
            with patch('acas_pro.ecommerce.product_manager.ProductManager') as mock_pm_class:
                # Mock shops
                mock_shop = MagicMock()
                mock_shop.id = 'shop_001'
                mock_shop.name = '测试店铺'
                mock_sm_instance = MagicMock()
                mock_sm_instance.get_shops_by_owner.return_value = [mock_shop]
                mock_sm_class.return_value = mock_sm_instance

                # Mock low stock products
                mock_product = MagicMock()
                mock_product.id = 'prod_001'
                mock_product.name = '黑茶'
                mock_product.get_total_stock.return_value = 5
                mock_product.stock_alert_threshold = 10
                mock_pm_instance = MagicMock()
                mock_pm_instance.get_low_stock_products.return_value = [mock_product]
                mock_pm_class.return_value = mock_pm_instance

                alerts = manager.get_low_stock_alerts(owner_id='owner_001')
                assert isinstance(alerts, list)


class TestSupplier:
    """Test Supplier dataclass"""

    def test_supplier_creation(self):
        """Test Supplier creation"""
        supplier = Supplier(
            id='sup_001',
            name='测试供应商',
            contact_person='张三',
            contact_phone='13800138000',
        )
        assert supplier.id == 'sup_001'
        assert supplier.name == '测试供应商'
        assert supplier.status == SupplierStatus.ACTIVE  # default

    def test_supplier_with_rating(self):
        """Test Supplier with rating"""
        supplier = Supplier(
            id='sup_001',
            name='测试供应商',
            contact_person='张三',
            contact_phone='13800138000',
            rating=4.5,
            cooperation_count=10,
        )
        assert supplier.rating == 4.5
        assert supplier.cooperation_count == 10


class TestInventorySync:
    """Test InventorySync dataclass"""

    def test_inventory_sync_creation(self):
        """Test InventorySync creation"""
        sync = InventorySync(
            id='sync_001',
            product_id='prod_001',
            shop_id='shop_001',
            supplier_id='sup_001',
            quantity_before=50,
            quantity_after=100,
            quantity_changed=50,
            status=InventorySyncStatus.SYNCED,
        )
        assert sync.id == 'sync_001'
        assert sync.quantity_before == 50
        assert sync.quantity_after == 100
        assert sync.quantity_changed == 50
        assert sync.status == InventorySyncStatus.SYNCED


class TestPurchaseOrder:
    """Test PurchaseOrder dataclass"""

    def test_purchase_order_creation(self):
        """Test PurchaseOrder creation"""
        items = [
            {'product_id': 'prod_001', 'product_name': '黑茶', 'quantity': 10, 'unit_price': 128.0},
        ]

        order = PurchaseOrder(
            id='po_001',
            supplier_id='sup_001',
            items=items,
            subtotal=1280.0,
            total_amount=1280.0,
        )
        assert order.id == 'po_001'
        assert order.supplier_id == 'sup_001'
        assert len(order.items) == 1
        assert order.status == 'pending'  # default
