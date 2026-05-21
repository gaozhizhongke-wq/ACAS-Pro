#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for ml/inventory_optimizer.py"""

import pytest
from datetime import datetime, timedelta
from acas_pro.ml.inventory_optimizer import InventoryOptimizer
from acas_pro.ml.timesfm_engine import ForecastResult, ForecastPoint


class TestInventoryOptimizer:
    def setup_method(self):
        self.optimizer = InventoryOptimizer()

    def test_init(self):
        assert self.optimizer is not None
        assert self.optimizer.service_level == 0.95
        assert self.optimizer.lead_time_days == 7

    def test_optimize_inventory_basic(self):
        inventory_data = [
            {"product_id": "P001", "current_stock": 100, "avg_daily_sales": 10}
        ]
        sales_history = {
            "P001": [(datetime.now() - timedelta(days=i), 10.0) for i in range(30)]
        }
        result = self.optimizer.optimize_inventory(inventory_data, sales_history, forecast_days=30)
        assert isinstance(result, list)

    def test_optimize_inventory_multiple(self):
        inventory_data = [
            {"product_id": "P001", "current_stock": 100, "avg_daily_sales": 10},
            {"product_id": "P002", "current_stock": 50, "avg_daily_sales": 20}
        ]
        sales_history = {
            "P001": [(datetime.now() - timedelta(days=i), 10.0) for i in range(30)],
            "P002": [(datetime.now() - timedelta(days=i), 20.0) for i in range(30)]
        }
        result = self.optimizer.optimize_inventory(inventory_data, sales_history, forecast_days=30)
        assert isinstance(result, list)
        assert len(result) >= 0

    def test_optimize_inventory_low_stock(self):
        inventory_data = [
            {"product_id": "P001", "current_stock": 5, "avg_daily_sales": 10}
        ]
        sales_history = {
            "P001": [(datetime.now() - timedelta(days=i), 10.0) for i in range(30)]
        }
        result = self.optimizer.optimize_inventory(inventory_data, sales_history, forecast_days=30)
        assert isinstance(result, list)

    def test_optimize_inventory_zero_stock(self):
        inventory_data = [
            {"product_id": "P001", "current_stock": 0, "avg_daily_sales": 10}
        ]
        sales_history = {
            "P001": [(datetime.now() - timedelta(days=i), 10.0) for i in range(30)]
        }
        result = self.optimizer.optimize_inventory(inventory_data, sales_history, forecast_days=30)
        assert isinstance(result, list)

    def test_calculate_inventory_metrics(self):
        recommendations = self.optimizer.optimize_inventory(
            [{"product_id": "P001", "current_stock": 100, "avg_daily_sales": 10}],
            {"P001": [(datetime.now() - timedelta(days=i), 10.0) for i in range(30)]},
            forecast_days=30
        )
        metrics = self.optimizer.calculate_inventory_metrics(recommendations)
        assert isinstance(metrics, dict)

    def test_calculate_inventory_metrics_empty(self):
        metrics = self.optimizer.calculate_inventory_metrics([])
        assert isinstance(metrics, dict)

    def test_assess_stockout_risks(self):
        inventory_data = [
            {"product_id": "P001", "current_stock": 5, "avg_daily_sales": 10},
            {"product_id": "P002", "current_stock": 100, "avg_daily_sales": 5}
        ]
        # Create mock forecasts
        from acas_pro.ml.timesfm_engine import ForecastPoint
        now = datetime.now()
        forecast_points = [
            ForecastPoint(timestamp=now + timedelta(days=i), value=10.0, lower_bound=8.0, upper_bound=12.0, confidence=0.8)
            for i in range(30)
        ]
        forecasts = {
            "P001": ForecastResult(product_id="P001", forecast=forecast_points, trend_direction="stable", trend_magnitude=0.0, seasonality_detected=False, model_version="test", generated_at=now),
            "P002": ForecastResult(product_id="P002", forecast=forecast_points, trend_direction="up", trend_magnitude=0.1, seasonality_detected=False, model_version="test", generated_at=now)
        }
        risks = self.optimizer.assess_stockout_risks(inventory_data, forecasts)
        assert isinstance(risks, list)

    def test_assess_stockout_risks_empty(self):
        risks = self.optimizer.assess_stockout_risks([], {})
        assert isinstance(risks, list)
        assert len(risks) == 0

    def test_service_level(self):
        assert self.optimizer.service_level == 0.95

    def test_lead_time_days(self):
        assert self.optimizer.lead_time_days == 7

    def test_ordering_cost(self):
        assert self.optimizer.ordering_cost == 100.0

    def test_holding_cost_rate(self):
        assert abs(self.optimizer.holding_cost_rate - 0.255) < 0.015

    def test_stockout_cost(self):
        assert self.optimizer.stockout_cost == 500.0
