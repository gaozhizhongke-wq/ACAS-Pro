#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Forecasting Engine Tests
Tests for sales prediction and forecasting
"""

import pytest
import numpy as np
from datetime import datetime, timedelta

from acas_pro.ml.timesfm_engine import TimesFMEngine, ForecastResult


class TestTimesFMEngine:
    """Forecasting engine tests"""
    
    def test_basic_forecast(self, sample_sales_data):
        """Test basic forecast generation"""
        engine = TimesFMEngine()
        
        # Convert to format expected by engine
        dates = [d for d, _ in sample_sales_data]
        result = engine.forecast(
            product_id="TEST_PRODUCT",
            historical_data=sample_sales_data,
            horizon_days=7
        )
        
        # Check result structure
        assert isinstance(result, ForecastResult)
        assert result.product_id == "TEST_PRODUCT"
        assert len(result.forecast) == 7
        assert result.model_version is not None
    
    def test_forecast_values_reasonable(self, sample_sales_data):
        """Test forecast values are reasonable"""
        engine = TimesFMEngine()
        
        values = [v for _, v in sample_sales_data]
        mean_value = np.mean(values)
        
        result = engine.forecast(
            product_id="TEST_PRODUCT",
            historical_data=sample_sales_data,
            horizon_days=7
        )
        
        # Forecast values should be within reasonable range
        for point in result.forecast:
            # Not negative
            assert point.value >= 0
            
            # Not too far from historical mean (within 3 std)
            std_value = np.std(values)
            assert abs(point.value - mean_value) < 3 * std_value
    
    def test_confidence_intervals(self, sample_sales_data):
        """Test confidence intervals are valid"""
        engine = TimesFMEngine()
        
        result = engine.forecast(
            product_id="TEST_PRODUCT",
            historical_data=sample_sales_data,
            horizon_days=7
        )
        
        for point in result.forecast:
            # Lower bound < value < upper bound
            assert point.lower_bound <= point.value
            assert point.value <= point.upper_bound
            
            # Confidence should be between 0 and 1
            assert 0 <= point.confidence <= 1
    
    def test_trend_detection(self, sample_sales_data):
        """Test trend detection"""
        engine = TimesFMEngine()
        
        result = engine.forecast(
            product_id="TEST_PRODUCT",
            historical_data=sample_sales_data,
            horizon_days=7
        )
        
        # Trend should be one of these
        assert result.trend_direction in ["up", "down", "stable"]
        
        # Magnitude should be percentage
        assert -100 <= result.trend_magnitude <= 100
    
    def test_insufficient_data(self):
        """Test handling of insufficient data"""
        engine = TimesFMEngine()
        
        # Only 5 data points
        base = datetime(2024, 1, 1)
        values = [(base + timedelta(days=i), v) for i, v in enumerate([100, 105, 98, 110, 95])]
        
        result = engine.forecast(
            product_id="TEST_PRODUCT",
            historical_data=values,
            horizon_days=7
        )
        
        # Should still produce forecast
        assert len(result.forecast) == 7
    
    def test_constant_values(self):
        """Test forecast with constant values"""
        engine = TimesFMEngine()
        
        # Constant sales
        base = datetime(2024, 1, 1)
        values = [(base + timedelta(days=i), 100.0) for i in range(30)]
        
        result = engine.forecast(
            product_id="TEST_PRODUCT",
            historical_data=values,
            horizon_days=7
        )
        
        # Forecast should be close to constant
        for point in result.forecast:
            assert abs(point.value - 100) < 10  # Within 10%
        
        # Trend should be stable
        assert result.trend_direction == "stable"
    
    def test_seasonal_pattern(self):
        """Test detection of seasonal pattern"""
        engine = TimesFMEngine()
        
        # Create clear weekly seasonality
        base = datetime(2024, 1, 1)
        values = []
        for i in range(70):
            day = i % 7
            # Weekend higher
            if day in [5, 6]:
                values.append((base + timedelta(days=i), 150 + np.random.normal(0, 5)))
            else:
                values.append((base + timedelta(days=i), 100 + np.random.normal(0, 5)))
        
        result = engine.forecast(
            product_id="TEST_PRODUCT",
            historical_data=values,
            horizon_days=7
        )
        
        # Should detect seasonality
        assert result.seasonality_detected is True
    
    def test_to_dict(self, sample_sales_data):
        """Test forecast result serialization"""
        engine = TimesFMEngine()
        
        result = engine.forecast(
            product_id="TEST_PRODUCT",
            historical_data=sample_sales_data,
            horizon_days=7
        )
        
        # Convert to dict
        result_dict = result.to_dict()
        
        # Check structure
        assert "product_id" in result_dict
        assert "forecast" in result_dict
        assert "trend_direction" in result_dict
        assert len(result_dict["forecast"]) == 7
        
        # Each forecast point should have date and value
        for point in result_dict["forecast"]:
            assert "date" in point
            assert "value" in point


class TestForecastingEdgeCases:
    """Edge case tests"""
    
    def test_zero_values(self):
        """Test with zero sales"""
        engine = TimesFMEngine()
        
        base = datetime(2024, 1, 1)
        values = [(base + timedelta(days=i), v) for i, v in enumerate([0]*30 + [10, 15, 20])]
        
        result = engine.forecast(
            product_id="TEST_PRODUCT",
            historical_data=values,
            horizon_days=7
        )
        
        # Should produce valid forecast
        assert len(result.forecast) == 7
        assert all(p.value >= 0 for p in result.forecast)
    
    def test_negative_handling(self):
        """Test negative values are handled"""
        engine = TimesFMEngine()
        
        base = datetime(2024, 1, 1)
        values = [(base + timedelta(days=i), v) for i, v in enumerate([100, 95, -10, 110, 105, -5, 120])]
        
        result = engine.forecast(
            product_id="TEST_PRODUCT",
            historical_data=values,
            horizon_days=7
        )
        
        # Forecast should still be non-negative
        assert all(p.value >= 0 for p in result.forecast)
    
    def test_large_values(self):
        """Test with large sales values"""
        engine = TimesFMEngine()
        
        base = datetime(2024, 1, 1)
        values = [(base + timedelta(days=i), 1000000 + np.random.normal(0, 10000)) for i in range(60)]
        
        result = engine.forecast(
            product_id="TEST_PRODUCT",
            historical_data=values,
            horizon_days=7
        )
        
        # Should handle large values
        assert len(result.forecast) == 7
        assert all(p.value > 0 for p in result.forecast)
