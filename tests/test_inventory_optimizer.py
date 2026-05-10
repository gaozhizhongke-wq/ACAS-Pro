#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Inventory Optimizer Tests
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from acas_pro.ml.inventory_optimizer import (
    InventoryOptimizer, InventoryRecommendation, StockoutRisk,
    inventory_optimizer
)


class TestInventoryRecommendation:
    """Inventory recommendation tests"""
    
    def test_recommendation_creation(self):
        """Test recommendation creation"""
        rec = InventoryRecommendation(
            product_id="prod_001",
            product_name="Test Product",
            current_stock=100,
            recommended_order_quantity=50,
            urgency_level="medium",
            days_until_stockout=14.0,
            reorder_point=80,
            safety_stock=30,
            economic_order_qty=100,
            reasoning="Stock is adequate",
            confidence_score=0.85
        )
        
        assert rec.product_id == "prod_001"
        assert rec.urgency_level == "medium"
        assert rec.confidence_score == 0.85
    
    def test_recommendation_to_dict(self):
        """Test recommendation to dict"""
        rec = InventoryRecommendation(
            product_id="prod_001",
            product_name="Test",
            current_stock=100,
            recommended_order_quantity=50,
            urgency_level="high",
            days_until_stockout=7.5,
            reorder_point=80,
            safety_stock=30,
            economic_order_qty=100,
            reasoning="Test reasoning",
            confidence_score=0.9
        )
        
        data = rec.to_dict()
        
        assert "product_id" in data
        assert "urgency_level" in data
        assert data["urgency_level"] == "high"
        assert data["confidence_score"] == 0.9


class TestStockoutRisk:
    """Stockout risk tests"""
    
    def test_risk_creation(self):
        """Test risk creation"""
        risk = StockoutRisk(
            product_id="prod_001",
            risk_level="high",
            probability=0.8,
            estimated_stockout_date=datetime.now() + timedelta(days=7),
            revenue_at_risk=5000.0,
            impact_score=8,
            mitigation_actions=["Order immediately", "Contact supplier"]
        )
        
        assert risk.product_id == "prod_001"
        assert risk.risk_level == "high"
        assert risk.probability == 0.8


class TestInventoryOptimizer:
    """Inventory optimizer tests"""
    
    @pytest.fixture
    def optimizer(self):
        return InventoryOptimizer()
    
    def test_init(self, optimizer):
        """Test initialization"""
        assert optimizer.service_level == 0.95
        assert optimizer.lead_time_days == 7
        assert optimizer.holding_cost_rate == 0.25
    
    def test_optimize_inventory_empty(self, optimizer):
        """Test optimize with empty data"""
        recommendations = optimizer.optimize_inventory([], {})
        
        assert recommendations == []
    
    def test_optimize_inventory_basic(self, optimizer):
        """Test basic optimization"""
        inventory_data = [
            {
                "product_id": "prod_001",
                "name": "Test Product",
                "stock": 50,
                "cost": 10.0,
                "price": 20.0
            }
        ]
        
        # Create sales history
        now = datetime.now()
        sales_history = {
            "prod_001": [(now - timedelta(days=i), 5.0) for i in range(30)]
        }
        
        with patch('acas_pro.ml.inventory_optimizer.timesfm_engine') as mock_engine:
            mock_forecast = Mock()
            mock_forecast.forecast = []
            mock_forecast.trend_direction = "stable"
            mock_engine.forecast.return_value = mock_forecast
            
            recommendations = optimizer.optimize_inventory(
                inventory_data,
                sales_history,
                forecast_days=30
            )
        
        assert len(recommendations) == 1
        assert recommendations[0].product_id == "prod_001"
    
    def test_analyze_product_critical(self, optimizer):
        """Test analyze product with critical stock"""
        item = {
            "product_id": "prod_001",
            "name": "Test",
            "stock": 5,
            "cost": 10.0
        }
        
        history = [(datetime.now() - timedelta(days=i), 10.0) for i in range(30)]
        
        rec = optimizer._analyze_product(item, history, 30)
        
        assert rec.urgency_level == "critical"
        assert rec.product_id == "prod_001"
    
    def test_analyze_product_high(self, optimizer):
        """Test analyze product with high urgency"""
        item = {
            "product_id": "prod_001",
            "name": "Test",
            "stock": 100,
            "cost": 10.0
        }
        
        # High demand to trigger high urgency
        history = [(datetime.now() - timedelta(days=i), 20.0) for i in range(30)]
        
        rec = optimizer._analyze_product(item, history, 30)
        
        assert rec.product_id == "prod_001"
        assert rec.reorder_point > 0
        assert rec.safety_stock > 0
    
    def test_assess_stockout_risks_empty(self, optimizer):
        """Test assess risks with empty data"""
        risks = optimizer.assess_stockout_risks([], {})
        
        assert risks == []
    
    def test_calculate_inventory_metrics_empty(self, optimizer):
        """Test calculate metrics with empty list"""
        metrics = optimizer.calculate_inventory_metrics([])
        
        assert metrics == {}
    
    def test_calculate_inventory_metrics(self, optimizer):
        """Test calculate metrics"""
        recommendations = [
            InventoryRecommendation(
                product_id="p1",
                product_name="Product 1",
                current_stock=100,
                recommended_order_quantity=50,
                urgency_level="high",
                days_until_stockout=7.0,
                reorder_point=80,
                safety_stock=30,
                economic_order_qty=100,
                reasoning="Test",
                confidence_score=0.9
            ),
            InventoryRecommendation(
                product_id="p2",
                product_name="Product 2",
                current_stock=200,
                recommended_order_quantity=30,
                urgency_level="low",
                days_until_stockout=30.0,
                reorder_point=150,
                safety_stock=50,
                economic_order_qty=150,
                reasoning="Test",
                confidence_score=0.8
            )
        ]
        
        metrics = optimizer.calculate_inventory_metrics(recommendations)
        
        assert metrics["total_products"] == 2
        assert metrics["total_current_stock"] == 300
        assert metrics["urgency_distribution"]["high"] == 1
        assert metrics["urgency_distribution"]["low"] == 1


class TestGlobalInstance:
    """Test global inventory optimizer instance"""
    
    def test_global_instance_exists(self):
        """Test global instance exists"""
        assert inventory_optimizer is not None
        assert isinstance(inventory_optimizer, InventoryOptimizer)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
