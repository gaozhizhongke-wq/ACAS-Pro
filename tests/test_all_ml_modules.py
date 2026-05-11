"""Comprehensive ML Modules Test Suite"""
import pytest
from unittest.mock import MagicMock, patch, Mock
import numpy as np
from datetime import datetime, timezone, timedelta


class TestTimesFMEngine:
    """Test TimesFM Forecasting Engine"""
    
    def test_engine_imports(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        assert TimesFMEngine is not None
    
    def test_forecast_result_imports(self):
        from acas_pro.ml.timesfm_engine import ForecastResult
        assert ForecastResult is not None
    
    def test_forecast_point_imports(self):
        from acas_pro.ml.timesfm_engine import ForecastPoint
        assert ForecastPoint is not None
    
    def test_engine_initialization(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine()
        assert engine is not None
        assert hasattr(engine, 'forecast')
        assert hasattr(engine, 'alpha')
        assert hasattr(engine, 'beta')
        assert hasattr(engine, 'gamma')
    
    def test_forecast_with_data(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine()
        
        # Generate test data (20+ points for normal operation)
        data = [(datetime.now(timezone.utc) - timedelta(days=i), 100.0 + i * 10) for i in range(20)]
        result = engine.forecast("test_product", data, horizon_days=7)
        
        assert result is not None
        assert result.product_id == "test_product"
        assert hasattr(result, 'forecast')
        assert hasattr(result, 'trend_direction')
        assert hasattr(result, 'to_dict')
    
    def test_forecast_with_insufficient_data(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine()
        
        # Less than 14 data points triggers fallback
        data = [(datetime.now(timezone.utc) - timedelta(days=i), 100.0) for i in range(5)]
        result = engine.forecast("test_product", data, horizon_days=7)
        
        assert result is not None
    
    def test_forecast_result_to_dict(self):
        from acas_pro.ml.timesfm_engine import ForecastResult, ForecastPoint
        
        points = [
            ForecastPoint(
                timestamp=datetime.now(timezone.utc),
                value=100.0,
                lower_bound=90.0,
                upper_bound=110.0,
                confidence=0.95
            )
        ]
        
        result = ForecastResult(
            product_id="test",
            forecast=points,
            trend_direction="up",
            trend_magnitude=5.0,
            seasonality_detected=True,
            model_version="test-v1",
            generated_at=datetime.now(timezone.utc)
        )
        
        d = result.to_dict()
        assert d['product_id'] == "test"
        assert 'forecast' in d
        assert 'trend_direction' in d


class TestInventoryOptimizer:
    """Test Inventory Optimizer"""
    
    def test_optimizer_imports(self):
        from acas_pro.ml.inventory_optimizer import InventoryOptimizer
        assert InventoryOptimizer is not None
    
    def test_optimizer_initialization(self):
        from acas_pro.ml.inventory_optimizer import InventoryOptimizer
        optimizer = InventoryOptimizer()
        assert optimizer is not None


class TestStatsForecastFallback:
    """Test StatsForecast fallback mechanism"""
    
    def test_statsforecast_status_persistence(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine()
        
        # Check status file handling
        assert hasattr(engine, '_STATUS_FILE')
        assert hasattr(engine, '_load_statsforecast_status')
        assert hasattr(engine, '_save_statsforecast_status')
