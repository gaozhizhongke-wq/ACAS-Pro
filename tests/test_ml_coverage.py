"""ML Module Coverage Tests"""
import pytest
from unittest.mock import MagicMock, patch
import numpy as np
from datetime import datetime, timezone, timedelta


class TestTimesFMEngine:
    """Test TimesFM Engine"""
    
    def test_engine_initialization(self):
        """Test engine can be initialized"""
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine()
        assert engine is not None
        assert hasattr(engine, 'forecast')
    
    def test_forecast_with_insufficient_data(self):
        """Test forecast with insufficient data"""
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine()
        
        # Less than 14 data points
        data = [(datetime.now(timezone.utc) - timedelta(days=i), 100.0) for i in range(5)]
        result = engine.forecast("test_product", data, horizon_days=7)
        assert result is not None
    
    def test_forecast_result_structure(self):
        """Test forecast result has correct structure"""
        from acas_pro.ml.timesfm_engine import TimesFMEngine, ForecastResult
        engine = TimesFMEngine()
        
        # Generate 20 data points
        data = [(datetime.now(timezone.utc) - timedelta(days=i), 100.0 + i) for i in range(20)]
        result = engine.forecast("test_product", data, horizon_days=7)
        
        assert result.product_id == "test_product"
        assert hasattr(result, 'forecast')
        assert hasattr(result, 'trend_direction')
        assert hasattr(result, 'to_dict')


class TestInventoryOptimizer:
    """Test Inventory Optimizer"""
    
    def test_optimizer_imports(self):
        """Test inventory optimizer can be imported"""
        from acas_pro.ml.inventory_optimizer import InventoryOptimizer
        assert InventoryOptimizer is not None


class TestForecastPoint:
    """Test ForecastPoint dataclass"""
    
    def test_forecast_point_creation(self):
        """Test forecast point can be created"""
        from acas_pro.ml.timesfm_engine import ForecastPoint
        point = ForecastPoint(
            timestamp=datetime.now(timezone.utc),
            value=100.0,
            lower_bound=90.0,
            upper_bound=110.0,
            confidence=0.95
        )
        assert point.value == 100.0
        assert point.confidence == 0.95
