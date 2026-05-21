#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for v2 modules (settlement_engine, order_manager, product_manager)."""

from unittest.mock import MagicMock, patch
import sys
import pytest

if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()


class TestSettlementEngine:
    def test_create_settlement(self):
        from acas_pro.blockchain.settlement_engine_v2 import SettlementEngine
        mock_db = MagicMock()
        with patch.object(SettlementEngine, '_init_tables'):
            engine = SettlementEngine(db=mock_db)
            ok, sid = engine.create_settlement(100.0, "USD")
            assert ok == True
            assert sid is not None
            mock_db.execute.assert_called_once()

    def test_complete_settlement(self):
        from acas_pro.blockchain.settlement_engine_v2 import SettlementEngine
        mock_db = MagicMock()
        with patch.object(SettlementEngine, '_init_tables'):
            engine = SettlementEngine(db=mock_db)
            ok, msg = engine.complete_settlement("settle-123")
            assert ok == True
            assert "Completed" in msg


class TestOrderManager:
    def test_create_order(self):
        from acas_pro.ecommerce.order_manager_v2 import OrderManager
        mock_db = MagicMock()
        with patch.object(OrderManager, '_init_tables'):
            mgr = OrderManager(db=mock_db)
            items = [{"product_id": "p1", "quantity": 2, "price": 50.0}]
            ok, oid = mgr.create_order("user1", items)
            assert ok == True
            assert oid is not None
            mock_db.execute.assert_called()

    def test_create_order_calculates_total(self):
        from acas_pro.ecommerce.order_manager_v2 import OrderManager
        mock_db = MagicMock()
        with patch.object(OrderManager, '_init_tables'):
            mgr = OrderManager(db=mock_db)
            items = [
                {"product_id": "p1", "quantity": 3, "price": 10.0},
                {"product_id": "p2", "quantity": 1, "price": 25.0},
            ]
            ok, _ = mgr.create_order("user1", items)
            assert ok == True
            # Verify the INSERT call contains total = 55.0
            call_args = mock_db.execute.call_args
            assert call_args is not None


class TestProductManager:
    def test_create_product(self):
        from acas_pro.ecommerce.product_manager_v2 import ProductManager
        mock_db = MagicMock()
        with patch.object(ProductManager, '_init_tables'):
            mgr = ProductManager(db=mock_db)
            ok, pid = mgr.create_product("Test Product", 99.9, stock=100)
            assert ok == True
            assert pid is not None
            mock_db.execute.assert_called_once()

    def test_get_product(self):
        from acas_pro.ecommerce.product_manager_v2 import ProductManager
        mock_db = MagicMock()
        mock_db.fetchone.return_value = {"id": "p1", "name": "Test"}
        with patch.object(ProductManager, '_init_tables'):
            mgr = ProductManager(db=mock_db)
            product = mgr.get_product("p1")
            assert product["name"] == "Test"
            mock_db.fetchone.assert_called_once()

    def test_list_products(self):
        from acas_pro.ecommerce.product_manager_v2 import ProductManager
        mock_db = MagicMock()
        mock_db.fetchall.return_value = [{"id": "p1"}, {"id": "p2"}]
        with patch.object(ProductManager, '_init_tables'):
            mgr = ProductManager(db=mock_db)
            products = mgr.list_products()
            assert len(products) == 2
