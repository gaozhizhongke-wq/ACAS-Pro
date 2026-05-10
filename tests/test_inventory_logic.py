#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Inventory Logic Tests
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from acas_pro.ui.logic.inventory_logic import (
    InventoryLogic, InventoryItem, InventoryAlert
)


class TestInventoryItem:
    """Test inventory item structure"""
    
    def test_item_creation(self):
        """Test inventory item creation"""
        item = InventoryItem(
            product_id="SKU-001",
            product_name="Test Product",
            current_stock=100,
            recommended_order=50,
            urgency="medium",
            days_until_stockout=10,
            reorder_point=50,
            confidence=0.9
        )
        assert item.product_id == "SKU-001"
        assert item.current_stock == 100
        assert item.confidence == 0.9


class TestInventoryAlert:
    """Test inventory alert structure"""
    
    def test_alert_creation(self):
        """Test alert creation"""
        alert = InventoryAlert(
            level="critical",
            message="Low stock",
            affected_products=["SKU-001"],
            timestamp=datetime.now()
        )
        assert alert.level == "critical"
        assert len(alert.affected_products) == 1


class TestInventoryLogic:
    """Test inventory logic"""
    
    @pytest.fixture
    def logic(self):
        return InventoryLogic()
    
    def test_init(self, logic):
        """Test initialization"""
        assert logic._items == []
        assert logic._alerts == []
        assert logic.optimizer is None
    
    def test_urgency_colors_defined(self, logic):
        """Test urgency colors are defined"""
        assert "critical" in logic.URGENCY_COLORS
        assert "high" in logic.URGENCY_COLORS
        assert "medium" in logic.URGENCY_COLORS
        assert "low" in logic.URGENCY_COLORS
    
    def test_analyze_inventory(self, logic):
        """Test inventory analysis"""
        products = [
            {"id": "SKU-001", "name": "Product A", "current_stock": 5, "avg_daily_sales": 2, "lead_time_days": 7},
            {"id": "SKU-002", "name": "Product B", "current_stock": 50, "avg_daily_sales": 5, "lead_time_days": 5},
        ]
        
        items = logic.analyze_inventory(products)
        
        assert len(items) == 2
        assert all(isinstance(item, InventoryItem) for item in items)
    
    def test_analyze_inventory_default_data(self, logic):
        """Test inventory analysis with default data"""
        items = logic.analyze_inventory()
        
        assert len(items) == 3
        assert items[0].product_id == "SKU-001"
    
    def test_analyze_inventory_sorting(self, logic):
        """Test items are sorted by urgency"""
        products = [
            {"id": "SKU-001", "name": "Low", "current_stock": 100, "avg_daily_sales": 1, "lead_time_days": 7},
            {"id": "SKU-002", "name": "Critical", "current_stock": 2, "avg_daily_sales": 2, "lead_time_days": 7},
            {"id": "SKU-003", "name": "High", "current_stock": 10, "avg_daily_sales": 2, "lead_time_days": 7},
        ]
        
        items = logic.analyze_inventory(products)
        
        # Critical should be first
        assert items[0].urgency == "critical"
        assert items[1].urgency == "high"
    
    def test_get_alerts(self, logic):
        """Test getting alerts"""
        products = [
            {"id": "SKU-001", "name": "Product A", "current_stock": 2, "avg_daily_sales": 2, "lead_time_days": 7},
        ]
        logic.analyze_inventory(products)
        
        alerts = logic.get_alerts()
        
        assert len(alerts) == 1
        assert alerts[0].level == "critical"
    
    def test_get_critical_count(self, logic):
        """Test getting critical count"""
        products = [
            {"id": "SKU-001", "name": "Critical", "current_stock": 2, "avg_daily_sales": 2, "lead_time_days": 7},
            {"id": "SKU-002", "name": "High", "current_stock": 10, "avg_daily_sales": 2, "lead_time_days": 7},
            {"id": "SKU-003", "name": "Low", "current_stock": 100, "avg_daily_sales": 1, "lead_time_days": 7},
        ]
        logic.analyze_inventory(products)
        
        count = logic.get_critical_count()
        
        assert count == 1
    
    def test_get_reorder_summary(self, logic):
        """Test getting reorder summary"""
        products = [
            {"id": "SKU-001", "name": "Critical", "current_stock": 2, "avg_daily_sales": 2, "lead_time_days": 7},
            {"id": "SKU-002", "name": "High", "current_stock": 10, "avg_daily_sales": 2, "lead_time_days": 7},
        ]
        logic.analyze_inventory(products)
        
        summary = logic.get_reorder_summary()
        
        assert summary["total_items"] == 2
        assert summary["critical_count"] == 1
        assert summary["high_count"] == 1
        assert summary["needs_attention"] is True
    
    def test_export_recommendations(self, logic):
        """Test exporting recommendations"""
        products = [
            {"id": "SKU-001", "name": "Product A", "current_stock": 2, "avg_daily_sales": 2, "lead_time_days": 7},
        ]
        logic.analyze_inventory(products)
        
        exported = logic.export_recommendations()
        
        assert len(exported) == 1
        assert "product_id" in exported[0]
        assert "recommended_order" in exported[0]
    
    def test_analyze_product_critical(self, logic):
        """Test analyzing critical product"""
        product = {"id": "SKU-001", "name": "Test", "current_stock": 2, "avg_daily_sales": 2, "lead_time_days": 7}
        
        item = logic._analyze_product(product)
        
        assert item.urgency == "critical"
        assert item.days_until_stockout == 1
    
    def test_analyze_product_high(self, logic):
        """Test analyzing high urgency product"""
        product = {"id": "SKU-001", "name": "Test", "current_stock": 10, "avg_daily_sales": 2, "lead_time_days": 7}
        
        item = logic._analyze_product(product)
        
        assert item.urgency == "high"
        assert item.days_until_stockout == 5
    
    def test_analyze_product_medium(self, logic):
        """Test analyzing medium urgency product"""
        product = {"id": "SKU-001", "name": "Test", "current_stock": 20, "avg_daily_sales": 2, "lead_time_days": 7}
        
        item = logic._analyze_product(product)
        
        assert item.urgency == "medium"
        assert item.days_until_stockout == 10
    
    def test_analyze_product_low(self, logic):
        """Test analyzing low urgency product"""
        product = {"id": "SKU-001", "name": "Test", "current_stock": 100, "avg_daily_sales": 2, "lead_time_days": 7}
        
        item = logic._analyze_product(product)
        
        assert item.urgency == "low"
        assert item.days_until_stockout == 50
    
    def test_analyze_product_zero_sales(self, logic):
        """Test analyzing product with zero sales"""
        product = {"id": "SKU-001", "name": "Test", "current_stock": 100, "avg_daily_sales": 0, "lead_time_days": 7}
        
        item = logic._analyze_product(product)
        
        assert item.days_until_stockout == 999
        assert item.urgency == "low"
    
    def test_generate_alerts(self, logic):
        """Test alert generation"""
        products = [
            {"id": "SKU-001", "name": "Critical", "current_stock": 2, "avg_daily_sales": 2, "lead_time_days": 7},
            {"id": "SKU-002", "name": "Also Critical", "current_stock": 3, "avg_daily_sales": 2, "lead_time_days": 7},
        ]
        logic.analyze_inventory(products)
        
        alerts = logic.get_alerts()
        
        assert len(alerts) == 1
        assert len(alerts[0].affected_products) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
