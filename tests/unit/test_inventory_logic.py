#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for inventory logic module"""
from datetime import datetime
from unittest.mock import patch
from acas_pro.ui.logic.inventory_logic import InventoryLogic, InventoryItem, InventoryAlert


class TestInventoryItem:
    def test_create_item(self):
        item = InventoryItem(
            product_id="PROD-001",
            product_name="Test Product",
            current_stock=100,
            recommended_order=50,
            urgency="medium",
            days_until_stockout=30,
            reorder_point=20,
            confidence=0.85
        )
        assert item.product_id == "PROD-001"
        assert item.product_name == "Test Product"
        assert item.current_stock == 100
        assert item.recommended_order == 50
        assert item.urgency == "medium"
        assert item.days_until_stockout == 30
        assert item.reorder_point == 20
        assert item.confidence == 0.85


class TestInventoryAlert:
    def test_create_alert(self):
        alert = InventoryAlert(
            level="critical",
            message="Stockout imminent",
            affected_products=["PROD-001", "PROD-002"],
            timestamp=datetime.now()
        )
        assert alert.level == "critical"
        assert alert.message == "Stockout imminent"
        assert alert.affected_products == ["PROD-001", "PROD-002"]
        assert isinstance(alert.timestamp, datetime)


class TestInventoryLogicInit:
    def test_init(self):
        with patch('acas_pro.core.database.DatabaseManager'):
            logic = InventoryLogic()
            assert logic._items == []
            assert logic._alerts == []
            assert logic.optimizer is None

    def test_init_with_optimizer(self):
        mock_optimizer = object()
        with patch('acas_pro.core.database.DatabaseManager'):
            logic = InventoryLogic(optimizer_service=mock_optimizer)
            assert logic.optimizer is mock_optimizer


class TestAnalyzeInventory:
    def test_analyze_with_data(self):
        with patch('acas_pro.core.database.DatabaseManager'):
            logic = InventoryLogic()
            products = [
                {"id": "P1", "name": "Product 1", "current_stock": 100, "avg_daily_sales": 5, "lead_time_days": 7},
                {"id": "P2", "name": "Product 2", "current_stock": 10, "avg_daily_sales": 20, "lead_time_days": 7},
            ]
            items = logic.analyze_inventory(products)
            assert len(items) == 2
            # Items are sorted by urgency (critical first)
            assert items[0].product_id in ["P1", "P2"]
            assert items[1].product_id in ["P1", "P2"]

    def test_analyze_empty(self):
        with patch('acas_pro.core.database.DatabaseManager'):
            logic = InventoryLogic()
            items = logic.analyze_inventory([])
            assert items == []

    def test_analyze_none(self):
        with patch('acas_pro.core.database.DatabaseManager'):
            logic = InventoryLogic()
            items = logic.analyze_inventory(None)
            # Returns default products when None
            assert len(items) >= 3  # Default products exist


class TestGetAlerts:
    def test_get_alerts(self):
        with patch('acas_pro.core.database.DatabaseManager'):
            logic = InventoryLogic()
            alert = InventoryAlert(
                level="warning",
                message="Low stock",
                affected_products=["P1"],
                timestamp=datetime.now()
            )
            logic._alerts = [alert]
            alerts = logic.get_alerts()
            assert len(alerts) == 1
            assert alerts[0].message == "Low stock"

    def test_get_alerts_empty(self):
        with patch('acas_pro.core.database.DatabaseManager'):
            logic = InventoryLogic()
            alerts = logic.get_alerts()
            assert alerts == []


class TestGetCriticalCount:
    def test_get_critical_count(self):
        with patch('acas_pro.core.database.DatabaseManager'):
            logic = InventoryLogic()
            logic._items = [
                InventoryItem("P1", "A", 100, 0, "low", 60, 20, 0.9),
                InventoryItem("P2", "B", 5, 100, "critical", 2, 30, 0.95),
            ]
            assert logic.get_critical_count() == 1

    def test_get_critical_count_empty(self):
        with patch('acas_pro.core.database.DatabaseManager'):
            logic = InventoryLogic()
            assert logic.get_critical_count() == 0


class TestGetReorderSummary:
    def test_get_summary(self):
        with patch('acas_pro.core.database.DatabaseManager'):
            logic = InventoryLogic()
            logic._items = [
                InventoryItem("P1", "A", 100, 0, "low", 60, 20, 0.9),
                InventoryItem("P2", "B", 5, 100, "critical", 2, 30, 0.95),
            ]
            summary = logic.get_reorder_summary()
            assert summary["total_items"] == 2
            assert summary["critical_count"] == 1
            assert summary["high_count"] == 0
            assert summary["needs_attention"] is True

    def test_get_summary_empty(self):
        with patch('acas_pro.core.database.DatabaseManager'):
            logic = InventoryLogic()
            summary = logic.get_reorder_summary()
            assert summary["total_items"] == 0
            assert summary["critical_count"] == 0
            assert summary["needs_attention"] is False


class TestExportRecommendations:
    def test_export(self):
        with patch('acas_pro.core.database.DatabaseManager'):
            logic = InventoryLogic()
            logic._items = [
                InventoryItem("P1", "Product 1", 100, 50, "medium", 30, 20, 0.85),
            ]
            recs = logic.export_recommendations()
            assert len(recs) == 1
            assert recs[0]["product_id"] == "P1"
            assert recs[0]["product_name"] == "Product 1"
            assert recs[0]["current_stock"] == 100
            assert recs[0]["recommended_order"] == 50
            assert recs[0]["urgency"] == "medium"
            assert recs[0]["days_until_stockout"] == 30

    def test_export_empty(self):
        with patch('acas_pro.core.database.DatabaseManager'):
            logic = InventoryLogic()
            recs = logic.export_recommendations()
            assert recs == []
