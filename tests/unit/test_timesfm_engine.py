"""Test timesfm_engine to increase coverage"""
import pytest
import sys
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone, timedelta

class TestTimesfmEngine:
    def test_import(self):
        """Import timesfm_engine with numpy mocked"""
        if 'numpy' not in sys.modules:
            sys.modules['numpy'] = MagicMock()
            sys.modules['numpy.ndarray'] = MagicMock
            sys.modules['numpy.float64'] = float
            sys.modules['numpy.std'] = lambda x, *args, **kwargs: 1.0
        from acas_pro.ml.timesfm_engine import TimesFMEngine, ForecastResult, ForecastPoint, timesfm_engine
        assert TimesFMEngine is not None

    def test_forecast_result_to_dict(self):
        """Test ForecastResult.to_dict"""
        if 'numpy' not in sys.modules:
            sys.modules['numpy'] = MagicMock()
        from acas_pro.ml.timesfm_engine import ForecastResult, ForecastPoint
        
        fp = ForecastPoint(
            timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc),
            value=100.0,
            lower_bound=80.0,
            upper_bound=120.0,
            confidence=0.95
        )
        result = ForecastResult(
            product_id="test",
            forecast=[fp],
            trend_direction="up",
            trend_magnitude=10.0,
            seasonality_detected=True,
            model_version="v1",
            generated_at=datetime(2024, 1, 1, tzinfo=timezone.utc)
        )
        d = result.to_dict()
        assert d["product_id"] == "test"
        assert d["trend_direction"] == "up"
        assert len(d["forecast"]) == 1

    def test_timesfm_engine_init(self):
        """Test TimesFMEngine initialization"""
        if 'numpy' not in sys.modules:
            sys.modules['numpy'] = MagicMock()
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        
        with patch('pathlib.Path.exists', return_value=False):
            engine = TimesFMEngine()
            assert engine.alpha == 0.3
            assert engine.statsforecast_ok is True

    def test_load_statsforecast_status(self):
        """Test _load_statsforecast_status"""
        if 'numpy' not in sys.modules:
            sys.modules['numpy'] = MagicMock()
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        
        engine = TimesFMEngine()
        
        # Test with missing file
        with patch('pathlib.Path.exists', return_value=False):
            result = engine._load_statsforecast_status()
            assert result is True

    def test_calculate_trend(self):
        """Test _calculate_trend"""
        if 'numpy' not in sys.modules:
            sys.modules['numpy'] = MagicMock()
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        
        engine = TimesFMEngine()
        
        # Test with insufficient data
        result = engine._calculate_trend([1, 2])
        assert result["direction"] == "stable"
        
        # Test with upward trend
        result = engine._calculate_trend([1]*14 + [2]*14)
        assert result["direction"] == "up"
        
        # Test with downward trend
        result = engine._calculate_trend([2]*14 + [1]*14)
        assert result["direction"] == "down"

    def test_detect_seasonality(self):
        """Test _detect_seasonality"""
        if 'numpy' not in sys.modules:
            sys.modules['numpy'] = MagicMock()
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        
        engine = TimesFMEngine()
        
        # Test with insufficient data
        result = engine._detect_seasonality([1, 2, 3])
        assert result is False
        
        # Test with seasonal data
        values = [100, 50, 100, 50, 100, 50, 100] * 3  # Weekly pattern
        result = engine._detect_seasonality(values)
        assert result is True

    def test_holt_winters_forecast(self):
        """Test _holt_winters_forecast"""
        if 'numpy' not in sys.modules:
            sys.modules['numpy'] = MagicMock()
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        
        engine = TimesFMEngine()
        
        values = [100, 110, 105, 115, 120, 110, 125] * 4
        result = engine._holt_winters_forecast(values, 7, True)
        assert len(result) == 7
        assert all(v >= 0 for v in result)

    def test_calculate_residuals(self):
        """Test _calculate_residuals"""
        if 'numpy' not in sys.modules:
            sys.modules['numpy'] = MagicMock()
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        
        engine = TimesFMEngine()
        
        # Test with insufficient data
        result = engine._calculate_residuals([1])
        assert result == [0]
        
        # Test with sufficient data
        result = engine._calculate_residuals([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        assert len(result) > 0

    def test_generate_fallback_forecast(self):
        """Test _generate_fallback_forecast"""
        if 'numpy' not in sys.modules:
            sys.modules['numpy'] = MagicMock()
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        
        engine = TimesFMEngine()
        
        data = [(datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0)]
        result = engine._generate_fallback_forecast("test", data, 7)
        assert result.product_id == "test"
        assert len(result.forecast) == 7
        assert result.trend_direction == "stable"

    def test_forecast_with_data(self):
        """Test forecast method with sufficient data"""
        if 'numpy' not in sys.modules:
            sys.modules['numpy'] = MagicMock()
            sys.modules['numpy.ndarray'] = MagicMock
            sys.modules['numpy.float64'] = float
            sys.modules['numpy.std'] = lambda x, *args, **kwargs: 1.0
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        
        engine = TimesFMEngine()
        
        # Create 30 days of data
        data = []
        for i in range(30):
            date = datetime(2024, 1, 1, tzinfo=timezone.utc) + timedelta(days=i)
            data.append((date, 100.0 + i * 2))
        
        with patch.object(engine, '_holt_winters_forecast', return_value=[100.0]*7):
            result = engine.forecast("test", data, 7)
            assert result.product_id == "test"
            assert len(result.forecast) == 7

    def test_forecast_with_insufficient_data(self):
        """Test forecast with insufficient data falls back"""
        if 'numpy' not in sys.modules:
            sys.modules['numpy'] = MagicMock()
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        
        engine = TimesFMEngine()
        
        data = [(datetime(2024, 1, 1, tzinfo=timezone.utc), 100.0)]
        result = engine.forecast("test", data, 7)
        assert result.product_id == "test"
        assert len(result.forecast) == 7
        assert "fallback" in result.model_version

    def test_save_statsforecast_status(self):
        """Test _save_statsforecast_status"""
        if 'numpy' not in sys.modules:
            sys.modules['numpy'] = MagicMock()
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        
        engine = TimesFMEngine()
        
        with patch('pathlib.Path.mkdir'):
            with patch('pathlib.Path.write_text'):
                engine._save_statsforecast_status(True)

    def test_global_instance(self):
        """Test global timesfm_engine instance"""
        if 'numpy' not in sys.modules:
            sys.modules['numpy'] = MagicMock()
        from acas_pro.ml.timesfm_engine import timesfm_engine
        assert timesfm_engine is not None
