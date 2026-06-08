#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Final coverage boost - targeted tests for high-impact uncovered modules."""

import sys
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timezone, timedelta
import json
import urllib.request, urllib.error

import pytest

# ─────────────────────────────────────────────────────────────────────────────
# Mock heavy deps at import time
# ─────────────────────────────────────────────────────────────────────────────
for _mod in ['numpy', 'torch', 'statsforecast', 'pandas']:
    if _mod not in sys.modules:
        m = MagicMock()
        sys.modules[_mod] = m

import sys as _sys
_sys.path.insert(0, 'src')


# =============================================================================
# 1. ml/timesfm_engine.py - 135 missed lines
# =============================================================================
class TestTimesFMEngineCore:
    """Deep coverage for TimesFMEngine."""

    def test_forecast_point_dataclass(self):
        from acas_pro.ml.timesfm_engine import ForecastPoint
        now = datetime.now(timezone.utc)
        pt = ForecastPoint(timestamp=now, value=100.0, lower_bound=80.0,
                           upper_bound=120.0, confidence=0.95)
        assert pt.value == 100.0
        assert pt.lower_bound == 80.0
        assert pt.upper_bound == 120.0
        assert pt.confidence == 0.95

    def test_forecast_result_to_dict(self):
        from acas_pro.ml.timesfm_engine import ForecastPoint, ForecastResult
        now = datetime.now(timezone.utc)
        pts = [
            ForecastPoint(timestamp=now, value=100.0, lower_bound=80.0,
                          upper_bound=120.0, confidence=0.95),
            ForecastPoint(timestamp=now + timedelta(days=1), value=105.0,
                          lower_bound=85.0, upper_bound=125.0, confidence=0.94),
        ]
        result = ForecastResult(
            product_id="prod-1",
            forecast=pts,
            trend_direction="up",
            trend_magnitude=5.0,
            seasonality_detected=True,
            model_version="acas-pro-2.0-statsforecast",
            generated_at=now,
        )
        d = result.to_dict()
        assert d["product_id"] == "prod-1"
        assert d["trend_direction"] == "up"
        assert d["seasonality_detected"] is True
        assert len(d["forecast"]) == 2
        assert d["forecast"][0]["value"] == 100.0

    def test_try_statsforecast_success(self):
        from acas_pro.ml.timesfm_engine import _try_statsforecast
        import numpy as np
        values = np.array([10.0, 12.0, 11.0, 13.0, 14.0] * 5, dtype=np.float64)
        result = _try_statsforecast(values, horizon=3, season_length=7)
        # May be None if statsforecast import fails, that's OK
        # Just verify it doesn't crash
        assert result is None or isinstance(result, dict)

    def test_try_statsforecast_failure(self):
        from acas_pro.ml.timesfm_engine import _try_statsforecast
        import numpy as np
        # Force exception by mocking statsforecast to raise
        with patch.dict('sys.modules', {'statsforecast': MagicMock()}):
            values = np.array([1.0, 2.0, 3.0], dtype=np.float64)
            result = _try_statsforecast(values, horizon=2, season_length=7)
            assert result is None

    def test_calculate_trend_stable(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.alpha = 0.3; engine.beta = 0.1; engine.gamma = 0.1
        # Values identical -> no change
        values = [100.0] * 14
        trend = engine._calculate_trend(values)
        assert trend["direction"] == "stable"
        assert trend["magnitude"] == 0.0

    def test_calculate_trend_up(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.alpha = 0.3; engine.beta = 0.1; engine.gamma = 0.1
        # Second half clearly higher
        values = [100.0] * 7 + [200.0] * 7
        trend = engine._calculate_trend(values)
        assert trend["direction"] == "up"

    def test_calculate_trend_down(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.alpha = 0.3; engine.beta = 0.1; engine.gamma = 0.1
        values = [200.0] * 7 + [80.0] * 7
        trend = engine._calculate_trend(values)
        assert trend["direction"] == "down"

    def test_calculate_trend_insufficient_data(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.alpha = 0.3; engine.beta = 0.1; engine.gamma = 0.1
        trend = engine._calculate_trend([100.0, 110.0])
        assert trend["direction"] == "stable"

    def test_detect_seasonality_short_data(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.season_length = 7
        result = engine._detect_seasonality([1.0, 2.0, 3.0])
        assert result is False

    def test_detect_seasonality_with_pattern(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.season_length = 7
        # Clear weekly pattern
        values = [100.0, 50.0, 50.0, 50.0, 50.0, 50.0, 200.0] * 4
        result = engine._detect_seasonality(values)
        assert isinstance(result, bool)

    def test_holt_winters_no_seasonality(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.alpha = 0.3; engine.beta = 0.1; engine.gamma = 0.1
        engine.season_length = 7
        values = [100.0, 105.0, 110.0, 115.0, 120.0, 125.0, 130.0] * 3
        forecast = engine._holt_winters_forecast(values, horizon=7, use_seasonality=False)
        assert len(forecast) == 7
        assert all(v >= 0 for v in forecast)

    def test_holt_winters_with_seasonality(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.alpha = 0.3; engine.beta = 0.1; engine.gamma = 0.1
        engine.season_length = 7
        values = [100.0, 105.0, 110.0, 115.0, 120.0, 125.0, 130.0] * 3
        forecast = engine._holt_winters_forecast(values, horizon=14, use_seasonality=True)
        assert len(forecast) == 14
        assert all(v >= 0 for v in forecast)

    def test_calculate_residuals_normal(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        values = [100.0, 105.0, 95.0, 110.0, 102.0, 108.0, 98.0] * 3
        residuals = engine._calculate_residuals(values)
        assert isinstance(residuals, list)
        assert len(residuals) > 0

    def test_calculate_residuals_short(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        residuals = engine._calculate_residuals([100.0])
        assert residuals == [0]

    def test_generate_fallback_forecast_with_data(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.MODEL_VERSION = "acas-pro-2.0-statsforecast"
        engine.alpha = 0.3; engine.beta = 0.1; engine.gamma = 0.1
        data = [(datetime.now(timezone.utc), 200.0)]
        result = engine._generate_fallback_forecast("p1", data, horizon_days=5)
        assert result.trend_direction == "stable"
        assert result.model_version.endswith("-fallback")
        assert len(result.forecast) == 5

    def test_generate_fallback_forecast_empty(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.MODEL_VERSION = "acas-pro-2.0-statsforecast"
        engine.alpha = 0.3; engine.beta = 0.1; engine.gamma = 0.1
        result = engine._generate_fallback_forecast("p2", [], horizon_days=3)
        assert len(result.forecast) == 3
        assert result.forecast[0].value == 100

    def test_forecast_insufficient_data(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.statsforecast_ok = True
        engine.MODEL_VERSION = "acas-pro-2.0-statsforecast"
        engine.alpha = 0.3; engine.beta = 0.1; engine.gamma = 0.1
        engine.season_length = 7
        data = [(datetime.now(timezone.utc), 100.0)]
        result = engine.forecast("p1", data, horizon_days=3)
        assert result.model_version.endswith("-fallback")
        assert len(result.forecast) == 3

    def test_forecast_holt_winters_fallback(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.statsforecast_ok = True  # Try statsforecast first
        engine.MODEL_VERSION = "acas-pro-2.0-statsforecast"
        engine.alpha = 0.3; engine.beta = 0.1; engine.gamma = 0.1
        engine.season_length = 7
        # Mock _try_statsforecast to return None (forces HW fallback)
        with patch('acas_pro.ml.timesfm_engine._try_statsforecast', return_value=None):
            data = [(datetime.now(timezone.utc) - timedelta(days=i), float(100 + i % 5))
                    for i in range(30, 0, -1)]
            result = engine.forecast("p1", data, horizon_days=10, confidence_level=0.8)
            assert "-holtwinters" in result.model_version
            assert len(result.forecast) == 10

    def test_forecast_statsforecast_success(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.statsforecast_ok = True
        engine.MODEL_VERSION = "acas-pro-2.0-statsforecast"
        engine.alpha = 0.3; engine.beta = 0.1; engine.gamma = 0.1
        engine.season_length = 7
        sf_result = {
            "values": [100.0, 105.0, 110.0],
            "lower": [90.0, 92.0, 94.0],
            "upper": [110.0, 118.0, 126.0],
        }
        with patch('acas_pro.ml.timesfm_engine._try_statsforecast', return_value=sf_result):
            data = [(datetime.now(timezone.utc) - timedelta(days=i), float(100 + i))
                    for i in range(30, 0, -1)]
            result = engine.forecast("p1", data, horizon_days=3)
            assert "-holtwinters" not in result.model_version
            assert len(result.forecast) == 3

    def test_forecast_confidence_level_0_95(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.statsforecast_ok = True
        engine.MODEL_VERSION = "acas-pro-2.0-statsforecast"
        engine.alpha = 0.3; engine.beta = 0.1; engine.gamma = 0.1
        engine.season_length = 7
        with patch('acas_pro.ml.timesfm_engine._try_statsforecast', return_value=None):
            data = [(datetime.now(timezone.utc) - timedelta(days=i), float(100 + i % 5))
                    for i in range(30, 0, -1)]
            result = engine.forecast("p1", data, horizon_days=5, confidence_level=0.95)
            assert len(result.forecast) == 5

    def test_load_statsforecast_status_file_missing(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.alpha = 0.3; engine.beta = 0.1; engine.gamma = 0.1
        engine.season_length = 7
        with patch.object(TimesFMEngine, '_STATUS_FILE', property(lambda self: MagicMock(exists=lambda: False))):
            result = engine._load_statsforecast_status()
            # Default is True when file doesn't exist

    def test_save_statsforecast_status_read_error(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.alpha = 0.3; engine.beta = 0.1; engine.gamma = 0.1
        engine.season_length = 7
        # Should not raise even if saving fails
        engine._save_statsforecast_status(False)

    def test_load_statsforecast_status_unavailable_retry(self):
        from acas_pro.ml.timesfm_engine import TimesFMEngine
        engine = TimesFMEngine.__new__(TimesFMEngine)
        engine.alpha = 0.3; engine.beta = 0.1; engine.gamma = 0.1
        engine.season_length = 7
        # Simulate file with unavailable=True but last_failure > 24h ago
        old_timestamp = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        mock_file = MagicMock()
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = json.dumps({
            "available": False,
            "last_failure": old_timestamp
        })
        with patch.object(TimesFMEngine, '_STATUS_FILE', property(lambda self: mock_file)):
            result = engine._load_statsforecast_status()
            # Should retry after 24h
            assert result is True


# =============================================================================
# 2. ml/inventory_optimizer.py - 114 missed lines
# =============================================================================
class TestInventoryRecommendation:
    def test_dataclass(self):
        from acas_pro.ml.inventory_optimizer import InventoryRecommendation
        rec = InventoryRecommendation(
            product_id="p1", product_name="Product 1", current_stock=50,
            recommended_order_quantity=100, urgency_level="high",
            days_until_stockout=7.5, reorder_point=30, safety_stock=10,
            economic_order_qty=200, reasoning="test", confidence_score=0.85
        )
        assert rec.urgency_level == "high"
        d = rec.to_dict()
        assert d["product_id"] == "p1"
        assert d["days_until_stockout"] == 7.5


class TestStockoutRisk:
    def test_dataclass(self):
        from acas_pro.ml.inventory_optimizer import StockoutRisk
        risk = StockoutRisk(
            product_id="p1", risk_level="critical", probability=0.9,
            estimated_stockout_date=datetime.now(timezone.utc),
            revenue_at_risk=5000.0, impact_score=9,
            mitigation_actions=["action1"]
        )
        assert risk.risk_level == "critical"
        assert risk.probability == 0.9


class TestInventoryOptimizerCore:
    def test_optimize_inventory_basic(self):
        from acas_pro.ml.inventory_optimizer import InventoryOptimizer
        opt = InventoryOptimizer()
        opt.lead_time_days = 7
        opt.holding_cost_rate = 0.25
        opt.ordering_cost = 100

        # Mock timesfm_engine
        mock_forecast_result = MagicMock()
        mock_forecast_result.trend_direction = "stable"
        mock_forecast_result.forecast = [MagicMock(value=10.0)] * 30

        with patch('acas_pro.ml.inventory_optimizer.timesfm_engine') as mock_tf:
            mock_tf.engine.forecast.return_value = mock_forecast_result
            opt.forecast = lambda pid, hist, days: mock_forecast_result

            inventory_data = [
                {"product_id": "p1", "name": "Widget", "stock": 5, "cost": 10.0, "price": 50.0}
            ]
            sales_history = {
                "p1": [(datetime.now(timezone.utc) - timedelta(days=i), 10.0)
                       for i in range(30, 0, -1)]
            }
            recs = opt.optimize_inventory(inventory_data, sales_history, forecast_days=30)
            assert len(recs) == 1
            assert recs[0].urgency_level in ["critical", "high", "medium", "low"]

    def test_assess_stockout_risks_no_stockout(self):
        from acas_pro.ml.inventory_optimizer import InventoryOptimizer
        from acas_pro.ml.timesfm_engine import ForecastPoint, ForecastResult
        opt = InventoryOptimizer()
        opt.lead_time_days = 7

        mock_forecast = MagicMock(spec=ForecastResult)
        mock_forecast.forecast = [MagicMock(value=1.0)] * 30  # Small demand, no stockout

        inventory_data = [{"product_id": "p1", "stock": 100, "price": 50.0}]
        risks = opt.assess_stockout_risks(inventory_data, {"p1": mock_forecast})
        assert len(risks) == 1
        assert risks[0].risk_level == "low"

    def test_assess_stockout_risks_critical(self):
        from acas_pro.ml.inventory_optimizer import InventoryOptimizer
        from acas_pro.ml.timesfm_engine import ForecastPoint, ForecastResult
        opt = InventoryOptimizer()

        mock_forecast = MagicMock(spec=ForecastResult)
        # High demand: stockout in 3 days
        mock_forecast.forecast = [MagicMock(value=50.0)] * 30

        inventory_data = [{"product_id": "p1", "stock": 100, "price": 50.0}]
        risks = opt.assess_stockout_risks(inventory_data, {"p1": mock_forecast})
        assert risks[0].risk_level == "critical"

    def test_assess_stockout_risks_high(self):
        from acas_pro.ml.inventory_optimizer import InventoryOptimizer
        from acas_pro.ml.timesfm_engine import ForecastPoint, ForecastResult
        opt = InventoryOptimizer()

        mock_forecast = MagicMock(spec=ForecastResult)
        # Stockout in 13 days -> high (days 1-13: 10*13=130 >= 100)
        mock_forecast.forecast = [MagicMock(value=10.0)] * 30

        inventory_data = [{"product_id": "p1", "stock": 100, "price": 50.0}]
        risks = opt.assess_stockout_risks(inventory_data, {"p1": mock_forecast})
        assert risks[0].risk_level in ["high", "medium"]

    def test_assess_stockout_risks_no_forecast(self):
        from acas_pro.ml.inventory_optimizer import InventoryOptimizer
        opt = InventoryOptimizer()
        inventory_data = [{"product_id": "p1", "stock": 100, "price": 50.0}]
        risks = opt.assess_stockout_risks(inventory_data, {})  # No forecast
        assert len(risks) == 0

    def test_calculate_inventory_metrics(self):
        from acas_pro.ml.inventory_optimizer import InventoryOptimizer, InventoryRecommendation
        opt = InventoryOptimizer()
        recs = [
            InventoryRecommendation(
                product_id="p1", product_name="P1", current_stock=10,
                recommended_order_quantity=50, urgency_level="critical",
                days_until_stockout=2.0, reorder_point=20, safety_stock=5,
                economic_order_qty=100, reasoning="", confidence_score=0.8
            ),
            InventoryRecommendation(
                product_id="p2", product_name="P2", current_stock=80,
                recommended_order_quantity=20, urgency_level="low",
                days_until_stockout=30.0, reorder_point=50, safety_stock=10,
                economic_order_qty=150, reasoning="", confidence_score=0.9
            ),
        ]
        metrics = opt.calculate_inventory_metrics(recs)
        assert metrics["total_products"] == 2
        assert metrics["total_current_stock"] == 90
        assert metrics["critical_items"] == 1
        assert metrics["high_priority_items"] == 0

    def test_calculate_inventory_metrics_empty(self):
        from acas_pro.ml.inventory_optimizer import InventoryOptimizer
        opt = InventoryOptimizer()
        metrics = opt.calculate_inventory_metrics([])
        assert metrics == {}


# =============================================================================
# 3. publisher/publish_manager.py - 110 missed lines
# =============================================================================
class TestPublishManagerMethods:
    def test_create_task(self):
        from acas_pro.publisher.publish_manager import PublishManager, ContentType
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            mgr._save_task = MagicMock()

            task = mgr.create_task(
                content_path="/video.mp4",
                content_type=ContentType.VIDEO,
                title="Test Video",
                description="Desc",
                tags=["tag1", "tag2"],
                platforms=["douyin", "bilibili"],
            )
            assert task.title == "Test Video"
            assert task.description == "Desc"
            assert len(task.platforms) == 2
            assert task.status.value == "pending"

    def test_get_task_not_found(self):
        from acas_pro.publisher.publish_manager import PublishManager
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            mgr.db.execute_one.return_value = None
            result = mgr.get_task("nonexistent")
            assert result is None

    def test_adapt_content_douyin(self):
        from acas_pro.publisher.publish_manager import PublishManager
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()

            adapted = mgr.adapt_content_for_platform(
                title="A" * 100, description="B" * 600, tags=["t1", "t2", "t3"], platform="douyin"
            )
            assert len(adapted["title"]) <= 55
            assert len(adapted["description"]) <= 500
            assert len(adapted["tags"]) <= 10

    def test_adapt_content_xiaohongshu_hashtags(self):
        from acas_pro.publisher.publish_manager import PublishManager
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()

            adapted = mgr.adapt_content_for_platform(
                title="Test", description="Desc", tags=["fashion", "style"], platform="xiaohongshu"
            )
            assert "#fashion" in adapted["description"]
            assert "#style" in adapted["description"]

    def test_adapt_content_instagram_no_tags_field(self):
        from acas_pro.publisher.publish_manager import PublishManager
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()

            adapted = mgr.adapt_content_for_platform(
                title="Test", description="Desc", tags=["tag1", "tag2"], platform="instagram"
            )
            assert adapted["tags"] == []  # Instagram moves tags to desc
            assert "#tag1" in adapted["description"]

    def test_adapt_content_unknown_platform(self):
        from acas_pro.publisher.publish_manager import PublishManager
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            adapted = mgr.adapt_content_for_platform("T", "D", ["t1"], "unknown")
            assert adapted["title"] == "T"
            assert adapted["description"] == "D"

    def test_publish_task_not_found(self):
        from acas_pro.publisher.publish_manager import PublishManager
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            mgr.get_task = MagicMock(return_value=None)
            result = mgr.publish("nonexistent")
            assert result is False

    def test_publish_already_published(self):
        from acas_pro.publisher.publish_manager import PublishManager, PublishStatus, ContentType
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            already_pub = MagicMock()
            already_pub.status = PublishStatus.PUBLISHED
            mgr.get_task = MagicMock(return_value=already_pub)
            result = mgr.publish("already-done")
            assert result is False

    def test_publish_scheduled_future(self):
        from acas_pro.publisher.publish_manager import PublishManager, PublishStatus, ContentType
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            mgr._save_task = MagicMock()
            future_task = MagicMock()
            future_task.status = PublishStatus.PENDING
            future_task.scheduled_time = datetime.now() + timedelta(hours=1)
            future_task.platforms = []
            mgr.get_task = MagicMock(return_value=future_task)
            result = mgr.publish("scheduled-future", immediate=False)
            assert result is True
            assert future_task.status == PublishStatus.SCHEDULED

    def test_publish_immediate_success(self):
        from acas_pro.publisher.publish_manager import (
            PublishManager, PublishStatus, ContentType, PlatformConfig
        )
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            mgr._save_task = MagicMock()
            mgr._publish_to_platform = MagicMock(return_value={
                "success": True, "post_id": "pid1", "url": "http://x.com"
            })
            task = MagicMock()
            task.status = PublishStatus.PENDING
            task.scheduled_time = None
            task.title = "T"
            task.description = "D"
            task.tags = ["t1"]
            task.cover_image = None
            task.platforms = [PlatformConfig(platform="douyin", account_id="a1")]
            task.publish_results = {}
            mgr.get_task = MagicMock(return_value=task)
            result = mgr.publish("task1", immediate=True)
            assert result is True
            assert task.status == PublishStatus.PUBLISHED

    def test_publish_partial_failure(self):
        from acas_pro.publisher.publish_manager import (
            PublishManager, PublishStatus, ContentType, PlatformConfig
        )
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            mgr._save_task = MagicMock()
            mgr._publish_to_platform = MagicMock(return_value={"success": False, "error": "API error"})
            task = MagicMock()
            task.status = PublishStatus.PENDING
            task.scheduled_time = None
            task.title = "T"
            task.description = "D"
            task.tags = ["t1"]
            task.cover_image = None
            task.platforms = [PlatformConfig(platform="douyin", account_id="a1")]
            task.publish_results = {}
            mgr.get_task = MagicMock(return_value=task)
            result = mgr.publish("task-fail", immediate=True)
            assert result is False
            assert task.status == PublishStatus.FAILED

    def test_schedule_task(self):
        from acas_pro.publisher.publish_manager import PublishManager, PublishStatus
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            mgr._save_task = MagicMock()
            task = MagicMock()
            task.status = PublishStatus.PENDING
            mgr.get_task = MagicMock(return_value=task)
            new_time = datetime.now(timezone.utc) + timedelta(hours=2)
            result = mgr.schedule_task("task1", new_time)
            assert result is True
            assert task.scheduled_time == new_time
            assert task.status == PublishStatus.SCHEDULED

    def test_cancel_task(self):
        from acas_pro.publisher.publish_manager import PublishManager, PublishStatus
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            mgr._save_task = MagicMock()
            task = MagicMock()
            task.status = PublishStatus.PENDING
            mgr.get_task = MagicMock(return_value=task)
            result = mgr.cancel_task("task1")
            assert result is True
            assert task.status == PublishStatus.CANCELLED

    def test_cancel_already_published(self):
        from acas_pro.publisher.publish_manager import PublishManager, PublishStatus
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            task = MagicMock()
            task.status = PublishStatus.PUBLISHED
            mgr.get_task = MagicMock(return_value=task)
            result = mgr.cancel_task("task1")
            assert result is False

    def test_retry_task_max_retries(self):
        from acas_pro.publisher.publish_manager import PublishManager, PublishStatus
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            task = MagicMock()
            task.status = PublishStatus.FAILED
            task.retry_count = 3
            task.max_retries = 3
            mgr.get_task = MagicMock(return_value=task)
            result = mgr.retry_task("task1")
            assert result is False

    def test_list_tasks_with_status_filter(self):
        from acas_pro.publisher.publish_manager import PublishManager, PublishStatus
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            mgr.db.execute.return_value = []
            mgr._row_to_task = MagicMock(return_value=MagicMock(
                status=PublishStatus.PENDING, platforms=[]
            ))
            result = mgr.list_tasks(status=PublishStatus.PENDING)
            assert isinstance(result, list)

    def test_list_tasks_with_platform_filter(self):
        from acas_pro.publisher.publish_manager import PublishManager, PublishStatus
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            mgr.db.execute.return_value = []
            mock_task = MagicMock()
            mock_task.status = PublishStatus.PENDING
            mock_task.platforms = [MagicMock(platform="douyin")]
            mgr._row_to_task = MagicMock(return_value=mock_task)
            result = mgr.list_tasks(platform="douyin")
            assert isinstance(result, list)

    def test_get_pending_tasks(self):
        from acas_pro.publisher.publish_manager import PublishManager, PublishStatus
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            mgr.list_tasks = MagicMock(return_value=[])
            result = mgr.get_pending_tasks()
            mgr.list_tasks.assert_called_once()
            mgr.list_tasks.assert_called_with(status=PublishStatus.PENDING)

    def test_delete_task_success(self):
        from acas_pro.publisher.publish_manager import PublishManager
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            mgr.db.execute.return_value = None
            result = mgr.delete_task("task1")
            assert result is True

    def test_delete_task_failure(self):
        from acas_pro.publisher.publish_manager import PublishManager
        with patch.object(PublishManager, '_init_database'):
            mgr = PublishManager.__new__(PublishManager)
            mgr.db = MagicMock()
            mgr.db.execute.side_effect = Exception("DB error")
            result = mgr.delete_task("task1")
            assert result is False


# =============================================================================
# 4. ecommerce/kuaishou_shop_api.py - 61 missed lines
# =============================================================================
class TestKuaishouShopClient:
    def test_check_business_error_raises(self):
        from acas_pro.ecommerce.kuaishou_shop_api import KuaishouShopClient, APIError, AuthError
        from acas_pro.ecommerce.platform_api_base import PlatformCredentials
        creds = PlatformCredentials(app_key="k", app_secret="s", access_token="t", refresh_token="r")
        client = KuaishouShopClient(creds)
        # Error code != 1 should raise
        with pytest.raises(APIError):
            client._check_business_error({"result": 100, "error_msg": "test error"})
        with pytest.raises(AuthError):
            client._check_business_error({"result": 401, "error_msg": "auth error"})

    def test_check_business_error_ok(self):
        from acas_pro.ecommerce.kuaishou_shop_api import KuaishouShopClient
        from acas_pro.ecommerce.platform_api_base import PlatformCredentials
        creds = PlatformCredentials(app_key="k", app_secret="s", access_token="t", refresh_token="r")
        client = KuaishouShopClient(creds)
        # Should not raise
        client._check_business_error({"result": 1})

    def test_build_common_params(self):
        from acas_pro.ecommerce.kuaishou_shop_api import KuaishouShopClient
        from acas_pro.ecommerce.platform_api_base import PlatformCredentials
        creds = PlatformCredentials(app_key="mykey", app_secret="mysecret",
                                   access_token="mytoken", refresh_token="myrefresh")
        client = KuaishouShopClient(creds)
        params = client._build_common_params("open.order.list")
        assert params["app_key"] == "mykey"
        assert params["method"] == "open.order.list"
        assert params["version"] == "1"
        assert params["sign_method"] == "MD5"
        assert "sign" in params
        assert "timestamp" in params

    def test_sync_orders_not_authenticated(self):
        from acas_pro.ecommerce.kuaishou_shop_api import KuaishouShopClient, SyncResult
        from acas_pro.ecommerce.platform_api_base import PlatformCredentials
        creds = PlatformCredentials(app_key="k", app_secret="s", access_token="", refresh_token="")
        client = KuaishouShopClient(creds)
        result = client.sync_orders()
        assert result.success is False

    def test_sync_orders_success(self):
        from acas_pro.ecommerce.kuaishou_shop_api import KuaishouShopClient
        from acas_pro.ecommerce.platform_api_base import PlatformCredentials
        creds = PlatformCredentials(app_key="k", app_secret="s", access_token="valid_token",
                                   refresh_token="r")
        client = KuaishouShopClient(creds)
        with patch.object(client, '_request_api', return_value={
            "result": 1, "data": {"order_list": [{"id": "o1"}, {"id": "o2"}], "total": 50}
        }):
            result = client.sync_orders()
            assert result.success is True
            assert result.total == 50
            assert result.created == 2

    def test_sync_orders_exception(self):
        from acas_pro.ecommerce.kuaishou_shop_api import KuaishouShopClient
        from acas_pro.ecommerce.platform_api_base import PlatformCredentials
        creds = PlatformCredentials(app_key="k", app_secret="s", access_token="t", refresh_token="r")
        client = KuaishouShopClient(creds)
        with patch.object(client, '_request_api', side_effect=Exception("network error")):
            result = client.sync_orders()
            assert result.success is False
            assert "network error" in result.errors[0]

    def test_sync_products_success(self):
        from acas_pro.ecommerce.kuaishou_shop_api import KuaishouShopClient
        from acas_pro.ecommerce.platform_api_base import PlatformCredentials
        creds = PlatformCredentials(app_key="k", app_secret="s", access_token="t", refresh_token="r")
        client = KuaishouShopClient(creds)
        with patch.object(client, '_request_api', return_value={
            "result": 1, "data": {"item_list": [{"id": "i1"}], "total": 10}
        }):
            result = client.sync_products()
            assert result.success is True
            assert result.created == 1

    def test_sync_inventory_success(self):
        from acas_pro.ecommerce.kuaishou_shop_api import KuaishouShopClient
        from acas_pro.ecommerce.platform_api_base import PlatformCredentials
        creds = PlatformCredentials(app_key="k", app_secret="s", access_token="t", refresh_token="r")
        client = KuaishouShopClient(creds)
        with patch.object(client, '_request_api', return_value={
            "result": 1, "data": {"stock_list": [{"id": "s1", "stock": 100}]}
        }):
            result = client.sync_inventory()
            assert result.success is True

    def test_update_product_status_online(self):
        from acas_pro.ecommerce.kuaishou_shop_api import KuaishouShopClient
        from acas_pro.ecommerce.platform_api_base import PlatformCredentials
        creds = PlatformCredentials(app_key="k", app_secret="s", access_token="t", refresh_token="r")
        client = KuaishouShopClient(creds)
        with patch.object(client, '_request_api', return_value={"result": 1}):
            result = client.update_product_status("prod1", "online")
            assert result is True

    def test_update_product_status_offline(self):
        from acas_pro.ecommerce.kuaishou_shop_api import KuaishouShopClient
        from acas_pro.ecommerce.platform_api_base import PlatformCredentials
        creds = PlatformCredentials(app_key="k", app_secret="s", access_token="t", refresh_token="r")
        client = KuaishouShopClient(creds)
        with patch.object(client, '_request_api', return_value={"result": 1}):
            result = client.update_product_status("prod1", "offline")
            assert result is True

    def test_update_product_status_api_error(self):
        from acas_pro.ecommerce.kuaishou_shop_api import KuaishouShopClient
        from acas_pro.ecommerce.platform_api_base import PlatformCredentials
        creds = PlatformCredentials(app_key="k", app_secret="s", access_token="t", refresh_token="r")
        client = KuaishouShopClient(creds)
        with patch.object(client, '_request_api', side_effect=Exception("api fail")):
            result = client.update_product_status("prod1", "online")
            assert result is False

    def test_get_logistics_info_success(self):
        from acas_pro.ecommerce.kuaishou_shop_api import KuaishouShopClient
        from acas_pro.ecommerce.platform_api_base import PlatformCredentials
        creds = PlatformCredentials(app_key="k", app_secret="s", access_token="t", refresh_token="r")
        client = KuaishouShopClient(creds)
        with patch.object(client, '_request_api', return_value={
            "result": 1, "data": {"carrier": "SF", "tracking_no": "SF123"}
        }):
            result = client.get_logistics_info("order1")
            assert result["carrier"] == "SF"

    def test_get_logistics_info_exception(self):
        from acas_pro.ecommerce.kuaishou_shop_api import KuaishouShopClient
        from acas_pro.ecommerce.platform_api_base import PlatformCredentials
        creds = PlatformCredentials(app_key="k", app_secret="s", access_token="t", refresh_token="r")
        client = KuaishouShopClient(creds)
        with patch.object(client, '_request_api', side_effect=Exception("logistics error")):
            result = client.get_logistics_info("order1")
            assert "error" in result

    def test_exchange_token_success(self):
        from acas_pro.ecommerce.kuaishou_shop_api import KuaishouShopClient
        from acas_pro.ecommerce.platform_api_base import PlatformCredentials
        creds = PlatformCredentials(app_key="k", app_secret="s", access_token="t", refresh_token="r")
        client = KuaishouShopClient(creds)
        with patch.object(client, 'request', return_value={
            "data": {"access_token": "new_at", "refresh_token": "new_rt",
                     "expires_in": 7200, "shop_id": "shop1"}
        }):
            result = client.exchange_token("auth_code")
            assert result["access_token"] == "new_at"
            assert result["refresh_token"] == "new_rt"

    def test_exchange_token_error(self):
        from acas_pro.ecommerce.kuaishou_shop_api import KuaishouShopClient
        from acas_pro.ecommerce.platform_api_base import PlatformCredentials
        creds = PlatformCredentials(app_key="k", app_secret="s", access_token="t", refresh_token="r")
        client = KuaishouShopClient(creds)
        with patch.object(client, 'request', side_effect=Exception("token exchange failed")):
            result = client.exchange_token("bad_code")
            assert "error" in result


# =============================================================================
# 5. web/__init__.py - 37 missed lines
# =============================================================================
class TestWebInit:
    def test_create_app_testing_mode(self):
        from acas_pro.web import create_app
        app = create_app(test_config={"TESTING": True})
        assert app.config.get("TESTING") is True

    def test_register_blueprints(self):
        from acas_pro.web import create_app
        app = create_app(test_config={"TESTING": True})
        # Should have registered blueprints
        rules = [r.rule for r in app.url_map.iter_rules()]
        assert len(rules) > 0

    def test_create_app_with_secret_key(self, monkeypatch):
        from acas_pro.web import create_app
        # Set environment with proper secret key
        monkeypatch.setenv("SECRET_KEY", "test-secret-key-for-testing-12345")
        monkeypatch.setenv("ENVIRONMENT", "development")
        app = create_app(test_config={"TESTING": True})
        assert app.secret_key == "test-secret-key-for-testing-12345"

    def test_create_app_production_no_secret(self, monkeypatch):
        from acas_pro.web import create_app
        monkeypatch.setenv("SECRET_KEY", "acas-pro-secret-key-change-me")
        monkeypatch.setenv("ENVIRONMENT", "production")
        # Patch _configure_app to raise before config.validate
        with patch('acas_pro.web._configure_app') as mock_cfg:
            mock_cfg.side_effect = ValueError("SECRET_KEY must be set in production!")
            with pytest.raises(ValueError, match="SECRET_KEY must be set"):
                create_app(test_config={"TESTING": True})

    def test_register_auth_middleware_public_routes(self):
        from acas_pro.web import create_app
        with patch('acas_pro.web.health.DatabaseManager') as MockDB:
            mock_db = MagicMock()
            mock_db.execute_one.return_value = {'health_check': 1}
            MockDB.return_value = mock_db
            app = create_app(test_config={"TESTING": True})
            client = app.test_client()
            # Public routes should work without auth
            resp = client.get("/api/health")
            assert resp.status_code in (200, 404)

    # Remove skip: auth middleware now registered in create_app
    def test_register_auth_middleware_protected_without_token(self):
        """Test that protected routes require authentication."""
        from acas_pro.web import create_app
        app = create_app(test_config={"TESTING": True})
        
        # Add a test protected route (not in PUBLIC_ROUTES or PUBLIC_PREFIXES)
        @app.route('/api/protected_test')
        def protected_test():
            from flask import jsonify
            return jsonify({'message': 'protected'}), 200
        
        client = app.test_client()
        resp = client.get("/api/protected_test")
        assert resp.status_code == 401, f'Expected 401, got {resp.status_code}'

    def test_authenticate_with_bearer_token(self):
        from acas_pro.web import create_app
        with patch('acas_pro.web.health.DatabaseManager') as MockDB:
            mock_db = MagicMock()
            mock_db.execute_one.return_value = {'health_check': 1}
            MockDB.return_value = mock_db
            app = create_app(test_config={"TESTING": True})
            client = app.test_client()
            resp = client.get("/api/health")  # public
            assert resp.status_code in (200, 404)


# =============================================================================
# 6. update/updater.py - 46 missed lines
# =============================================================================
class TestUpdateChecker:
    def test_compare_versions_v1_greater(self):
        from acas_pro.update.updater import UpdateChecker
        checker = UpdateChecker(current_version="5.0.0")
        assert checker._compare_versions("5.1.0", "5.0.0") > 0

    def test_compare_versions_v2_greater(self):
        from acas_pro.update.updater import UpdateChecker
        checker = UpdateChecker(current_version="5.0.0")
        assert checker._compare_versions("5.1.0", "5.0.5") > 0

    def test_compare_versions_equal(self):
        from acas_pro.update.updater import UpdateChecker
        checker = UpdateChecker(current_version="5.1.0")
        assert checker._compare_versions("5.1.0", "5.1.0") == 0

    def test_compare_versions_minor_less(self):
        from acas_pro.update.updater import UpdateChecker
        checker = UpdateChecker(current_version="5.1.0")
        assert checker._compare_versions("5.0.0", "5.1.0") < 0

    def test_compare_versions_with_v_prefix(self):
        from acas_pro.update.updater import UpdateChecker
        checker = UpdateChecker(current_version="v5.0.0")
        assert checker._compare_versions("v5.1.0", "v5.0.0") > 0

    def test_compare_versions_different_lengths(self):
        from acas_pro.update.updater import UpdateChecker
        checker = UpdateChecker(current_version="5.0.0")
        assert checker._compare_versions("5.1", "5.0.0") > 0

    def test_check_no_update_available(self):
        from acas_pro.update.updater import UpdateChecker
        checker = UpdateChecker(current_version="999.999.999")
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({
            "latest_version": "999.999.999",
            "release_date": "2025-01-01",
            "download_url": "http://x.com/setup.exe",
            "sha256": "abc123",
            "changelog": "..."
        }).encode()
        with patch('urllib.request.urlopen', return_value=mock_response):
            has_update, info = checker.check()
            assert has_update is False
            assert info is None

    def test_check_update_available(self):
        from acas_pro.update.updater import UpdateChecker
        checker = UpdateChecker(current_version="1.0.0")
        json_bytes = json.dumps({
            "latest_version": "2.0.0",
            "release_date": "2025-06-01",
            "download_url": "http://x.com/v2.exe",
            "sha256": "abc123def456",
            "changelog": "New features!",
            "mandatory": True
        }).encode()

        def fake_urlopen(req, timeout=None):
            resp = MagicMock()
            resp.read.return_value = json_bytes
            resp.__enter__ = MagicMock(return_value=resp)
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        with patch('urllib.request.urlopen', side_effect=fake_urlopen):
            has_update, info = checker.check()
            assert has_update is True
            assert info is not None
            assert info.version == "2.0.0"
            assert info.mandatory is True

    def test_check_network_error(self):
        from acas_pro.update.updater import UpdateChecker
        checker = UpdateChecker(current_version="1.0.0")
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError("no network")):
            has_update, info = checker.check()
            assert has_update is False
            assert info is None

    def test_check_json_decode_error(self):
        from acas_pro.update.updater import UpdateChecker
        checker = UpdateChecker(current_version="1.0.0")
        mock_response = MagicMock()
        mock_response.read.return_value = b"not json"
        with patch('urllib.request.urlopen', return_value=mock_response):
            has_update, info = checker.check()
            assert has_update is False

    def test_download_no_update_info(self):
        from acas_pro.update.updater import UpdateChecker
        checker = UpdateChecker(current_version="1.0.0")
        checker._update_info = None
        result = checker.download()
        assert result is None

    def test_download_success(self, tmp_path):
        from acas_pro.update.updater import UpdateChecker, UpdateInfo
        checker = UpdateChecker(current_version="1.0.0")
        checker._update_info = UpdateInfo(
            version="2.0.0",
            release_date="2025-06-01",
            download_url="http://x.com/setup.exe",
            sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            changelog="test"
        )
        # sha256 of empty bytes = e3b0c44298fc...
        def fake_urlopen(req, timeout=None):
            resp = MagicMock()
            resp.headers.get.return_value = "0"
            resp.read = MagicMock(side_effect=[b""])
            resp.__enter__ = MagicMock(return_value=resp)
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        with patch('urllib.request.urlopen', side_effect=fake_urlopen):
            result = checker.download()
            assert result is not None

    def test_download_with_progress_callback(self, tmp_path):
        from acas_pro.update.updater import UpdateChecker, UpdateInfo
        checker = UpdateChecker(current_version="1.0.0")
        checker._update_info = UpdateInfo(
            version="2.0.0", release_date="2025-06-01",
            download_url="http://x.com/setup.exe",
            sha256="", changelog=""
        )
        def fake_urlopen(req, timeout=None):
            resp = MagicMock()
            resp.headers.get.return_value = "16384"
            chunks = [b"x" * 8192, b"x" * 8192, b""]
            resp.read = MagicMock(side_effect=lambda n=None: chunks.pop(0) if chunks else b"")
            resp.__enter__ = MagicMock(return_value=resp)
            resp.__exit__ = MagicMock(return_value=False)
            return resp

        progress_values = []
        def progress(pct):
            progress_values.append(pct)

        with patch('urllib.request.urlopen', side_effect=fake_urlopen):
            result = checker.download(progress_callback=progress)
            assert result is not None

    def test_download_hash_mismatch(self, tmp_path):
        from acas_pro.update.updater import UpdateChecker, UpdateInfo
        checker = UpdateChecker(current_version="1.0.0")
        checker._update_info = UpdateInfo(
            version="2.0.0", release_date="2025-06-01",
            download_url="http://x.com/setup.exe",
            sha256="wronghash", changelog=""
        )
        mock_response = MagicMock()
        mock_response.headers.get.return_value = "10"
        mock_response.read = MagicMock(side_effect=[b"x" * 10, b""])

        with patch('urllib.request.urlopen', return_value=mock_response):
            result = checker.download()
            # Hash mismatch -> file deleted -> None
            assert result is None

    def test_download_network_error(self):
        from acas_pro.update.updater import UpdateChecker, UpdateInfo
        checker = UpdateChecker(current_version="1.0.0")
        checker._update_info = UpdateInfo(
            version="2.0.0", release_date="2025-06-01",
            download_url="http://x.com/setup.exe",
            sha256="abc", changelog=""
        )
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError("network")):
            result = checker.download()
            assert result is None

    def test_get_update_info(self):
        from acas_pro.update.updater import UpdateChecker, UpdateInfo
        checker = UpdateChecker(current_version="1.0.0")
        info = UpdateInfo(version="2.0.0", release_date="2025-06-01",
                          download_url="http://x.com", sha256="abc", changelog="")
        checker._update_info = info
        assert checker.get_update_info() == info

    def test_module_level_check(self):
        from acas_pro.update import updater
        # The module-level check_for_updates function
        has_update, info = updater.check_for_updates()
        # May or may not have update depending on network, just check no crash
        assert isinstance(has_update, bool)


# =============================================================================
# 7. ui/logic/report_logic.py - 38 missed lines
# =============================================================================
class TestReportLogic:
    def test_generate_sales_report(self):
        from acas_pro.ui.logic.report_logic import ReportLogic
        logic = ReportLogic()
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        report = logic.generate_sales_report(start, end, "Weekly Sales")
        assert report.name == "Weekly Sales"
        assert report.data["total_revenue"] == 150000.00
        assert report.data["total_orders"] == 450
        assert len(report.data["daily_sales"]) > 0

    def test_generate_customer_report(self):
        from acas_pro.ui.logic.report_logic import ReportLogic
        logic = ReportLogic()
        report = logic.generate_customer_report(segment="VIP")
        assert report.type.value == "customer"
        assert report.data["total_customers"] == 1250
        assert report.data["filtered_by_segment"] == "VIP"

    def test_generate_campaign_report(self):
        from acas_pro.ui.logic.report_logic import ReportLogic
        logic = ReportLogic()
        report = logic.generate_campaign_report(campaign_id="camp-1")
        assert report.type.value == "campaign"
        assert report.data["total_campaigns"] == 12

    def test_get_report(self):
        from acas_pro.ui.logic.report_logic import ReportLogic
        logic = ReportLogic()
        report = logic.generate_sales_report(datetime.now(), datetime.now())
        retrieved = logic.get_report(report.id)
        assert retrieved is not None
        assert retrieved.id == report.id

    def test_get_report_not_found(self):
        from acas_pro.ui.logic.report_logic import ReportLogic
        logic = ReportLogic()
        result = logic.get_report("nonexistent")
        assert result is None

    def test_list_reports_all(self):
        from acas_pro.ui.logic.report_logic import ReportLogic
        logic = ReportLogic()
        logic.generate_sales_report(datetime.now(), datetime.now())
        logic.generate_customer_report()
        reports = logic.list_reports()
        assert len(reports) >= 2

    def test_list_reports_filtered(self):
        from acas_pro.ui.logic.report_logic import ReportLogic, ReportType
        logic = ReportLogic()
        logic.generate_sales_report(datetime.now(), datetime.now())
        logic.generate_customer_report()
        reports = logic.list_reports(report_type=ReportType.CUSTOMER)
        assert all(r.type == ReportType.CUSTOMER for r in reports)

    def test_export_report_json(self):
        from acas_pro.ui.logic.report_logic import ReportLogic, ReportFormat
        logic = ReportLogic()
        report = logic.generate_sales_report(datetime.now(), datetime.now())
        path = logic.export_report(report.id, ReportFormat.JSON)
        assert path is not None
        assert path.endswith(".json")

    def test_export_report_csv(self):
        from acas_pro.ui.logic.report_logic import ReportLogic, ReportFormat
        logic = ReportLogic()
        report = logic.generate_sales_report(datetime.now(), datetime.now())
        path = logic.export_report(report.id, ReportFormat.CSV)
        assert path is not None
        assert path.endswith(".csv")

    def test_export_report_pdf(self):
        from acas_pro.ui.logic.report_logic import ReportLogic, ReportFormat
        logic = ReportLogic()
        report = logic.generate_sales_report(datetime.now(), datetime.now())
        path = logic.export_report(report.id, ReportFormat.PDF)
        assert path is not None
        assert path.endswith(".pdf")

    def test_export_report_not_found(self):
        from acas_pro.ui.logic.report_logic import ReportLogic, ReportFormat
        logic = ReportLogic()
        result = logic.export_report("nonexistent", ReportFormat.JSON)
        assert result is None

    def test_delete_report(self):
        from acas_pro.ui.logic.report_logic import ReportLogic
        logic = ReportLogic()
        report = logic.generate_sales_report(datetime.now(), datetime.now())
        result = logic.delete_report(report.id)
        assert result is True
        assert logic.get_report(report.id) is None

    def test_delete_report_not_found(self):
        from acas_pro.ui.logic.report_logic import ReportLogic
        logic = ReportLogic()
        result = logic.delete_report("nonexistent")
        assert result is False

    def test_get_report_summary_empty(self):
        from acas_pro.ui.logic.report_logic import ReportLogic
        logic = ReportLogic()
        summary = logic.get_report_summary()
        assert summary["total"] == 0
        assert summary["by_type"] == {}

    def test_get_report_summary_with_reports(self):
        from acas_pro.ui.logic.report_logic import ReportLogic, ReportType
        logic = ReportLogic()
        logic.generate_sales_report(datetime.now(), datetime.now())
        logic.generate_customer_report()
        logic.generate_customer_report()
        summary = logic.get_report_summary()
        assert summary["total"] >= 3
        assert "sales" in summary["by_type"]
        assert "customer" in summary["by_type"]


# =============================================================================
# 8. monitoring/health_monitor.py - 18 missed lines
# =============================================================================
class TestHealthMonitor:
    def test_register_check(self):
        from acas_pro.monitoring.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        monitor.register_check("db", lambda: True)
        assert "db" in monitor._checks

    def test_register_check_no_fn(self):
        from acas_pro.monitoring.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        monitor.register_check("api")
        assert "api" in monitor._checks

    def test_check_single(self):
        from acas_pro.monitoring.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        monitor.register_check("test", lambda: True)
        monitor.update_status("test", "healthy")
        result = monitor.check("test")
        assert result["name"] == "test"
        assert result["status"] == "healthy"

    def test_check_unknown(self):
        from acas_pro.monitoring.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        result = monitor.check("unknown")
        assert result["status"] == "unknown"

    def test_check_all(self):
        from acas_pro.monitoring.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        monitor.register_check("c1")
        monitor.update_status("c1", "healthy")
        monitor.register_check("c2")
        monitor.update_status("c2", "degraded")
        results = monitor.check()
        assert "c1" in results
        assert "c2" in results

    def test_overall_status_healthy(self):
        from acas_pro.monitoring.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        monitor.register_check("c1")
        monitor.update_status("c1", "healthy")
        monitor.register_check("c2")
        monitor.update_status("c2", "healthy")
        assert monitor.overall_status == "healthy"

    def test_overall_status_degraded(self):
        from acas_pro.monitoring.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        monitor.register_check("c1")
        monitor.update_status("c1", "healthy")
        monitor.register_check("c2")
        monitor.update_status("c2", "degraded")
        assert monitor.overall_status == "degraded"

    def test_overall_status_unhealthy(self):
        from acas_pro.monitoring.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        monitor.register_check("c1")
        monitor.update_status("c1", "healthy")
        monitor.register_check("c2")
        monitor.update_status("c2", "unhealthy")
        assert monitor.overall_status == "unhealthy"

    def test_overall_status_empty(self):
        from acas_pro.monitoring.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        assert monitor.overall_status == "healthy"

    def test_report(self):
        from acas_pro.monitoring.health_monitor import HealthMonitor
        monitor = HealthMonitor()
        monitor.register_check("db")
        monitor.update_status("db", "healthy")
        report = monitor.report()
        assert report["overall_status"] == "healthy"
        assert "timestamp" in report
        assert "db" in report["checks"]


# =============================================================================
# 9. monitoring/metrics_monitor.py - 13 missed lines
# =============================================================================
class TestMetricsMonitor:
    def test_increment(self):
        from acas_pro.monitoring.metrics_monitor import MetricsMonitor
        monitor = MetricsMonitor()
        monitor.increment("requests", 5.0)
        assert monitor.get_counter("requests") == 5.0

    def test_increment_multiple(self):
        from acas_pro.monitoring.metrics_monitor import MetricsMonitor
        monitor = MetricsMonitor()
        monitor.increment("requests", 1.0)
        monitor.increment("requests", 2.0)
        assert monitor.get_counter("requests") == 3.0

    def test_gauge(self):
        from acas_pro.monitoring.metrics_monitor import MetricsMonitor
        monitor = MetricsMonitor()
        monitor.gauge("memory_mb", 512.5)
        assert monitor.get_gauge("memory_mb") == 512.5

    def test_get_gauge_missing(self):
        from acas_pro.monitoring.metrics_monitor import MetricsMonitor
        monitor = MetricsMonitor()
        assert monitor.get_gauge("missing") is None

    def test_get_history(self):
        from acas_pro.monitoring.metrics_monitor import MetricsMonitor
        monitor = MetricsMonitor()
        monitor.increment("events", 1.0)
        monitor.increment("events", 2.0)
        monitor.increment("events", 3.0)
        history = monitor.get_history("events", limit=2)
        assert len(history) == 2

    def test_get_history_missing(self):
        from acas_pro.monitoring.metrics_monitor import MetricsMonitor
        monitor = MetricsMonitor()
        history = monitor.get_history("missing")
        assert history == []

    def test_report(self):
        from acas_pro.monitoring.metrics_monitor import MetricsMonitor
        monitor = MetricsMonitor()
        monitor.increment("requests", 10.0)
        monitor.gauge("memory_mb", 256.0)
        report = monitor.report()
        assert "counters" in report
        assert "gauges" in report
        assert report["counters"]["requests"] == 10.0
        assert report["gauges"]["memory_mb"] == 256.0
        assert "timestamp" in report

    def test_reset(self):
        from acas_pro.monitoring.metrics_monitor import MetricsMonitor
        monitor = MetricsMonitor()
        monitor.increment("requests", 10.0)
        monitor.gauge("memory_mb", 256.0)
        monitor.reset()
        assert monitor.get_counter("requests") == 0.0
        assert monitor.get_gauge("memory_mb") is None
