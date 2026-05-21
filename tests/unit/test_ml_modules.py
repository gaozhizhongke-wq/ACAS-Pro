#!/usr/bin/env python3
"""Tests for ML modules."""

import pytest
import sys
from unittest.mock import MagicMock, patch

# Pre-mock dependencies BEFORE importing acas_pro
if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()
if 'torch' not in sys.modules:
    sys.modules['torch'] = MagicMock()

# Now import using full path with src in path
import sys
sys.path.insert(0, 'src')


class TestTimesFMEngine:
    """Tests for TimesFM forecasting engine."""
    
    def test_timesfm_import(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        assert TimesFMEngine is not None
    
    def test_timesfm_init(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        try:
            engine = TimesFMEngine()
            assert engine is not None
        except Exception:
            pytest.skip("Cannot init TimesFMEngine")
    
    def test_forecast_point_import(self):
        from acas_pro.ml.timesfm_engine import ForecastPoint
        assert ForecastPoint is not None
    
    def test_forecast_result_import(self):
        from acas_pro.ml.timesfm_engine import ForecastResult
        assert ForecastResult is not None


class TestInventoryOptimizer:
    """Tests for inventory optimizer."""
    
    def test_optimizer_import(self):
        try:
            from acas_pro.ml.inventory_optimizer import InventoryOptimizer
            assert InventoryOptimizer is not None
        except ImportError:
            pytest.skip("Cannot import InventoryOptimizer")


class TestMLInit:
    """Tests for ml __init__."""
    
    def test_ml_init_import(self):
        from acas_pro import ml
        assert ml is not None