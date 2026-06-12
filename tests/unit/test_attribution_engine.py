# -*- coding: utf-8 -*-
"""Tests for advanced_analytics/attribution_engine.py"""

import pytest
from datetime import datetime, timedelta

from acas_pro.advanced_analytics.attribution_engine import (
    AttributionEngine,
    AttributionModel,
    ChannelType,
    TouchPoint,
    AttributionResult,
    AttributionReport,
)


class TestAttributionEngine:
    """Test AttributionEngine class"""

    @pytest.fixture
    def config(self):
        """Test configuration"""
        return {
            'attribution_window': 30,
            'confidence_threshold': 0.7,
            'decay_half_life': 7,
        }

    @pytest.fixture
    def engine(self, config):
        """Create AttributionEngine instance"""
        return AttributionEngine(config=config)

    @pytest.fixture
    def sample_touchpoint(self):
        """Create a sample touchpoint"""
        return TouchPoint(
            channel='google',
            channel_type=ChannelType.PAID_SEARCH,
            campaign='summer_sale',
            ad_group='adgroup_1',
            keyword='running shoes',
            timestamp=datetime.now() - timedelta(days=5),
            value=100.0,
            conversions=2,
            impressions=1000,
            clicks=50,
            cost=20.0,
        )

    # ===== 初始化测试 =====
    def test_init_default(self):
        """Test initialization with default config"""
        engine = AttributionEngine()
        assert engine.attribution_window == 30
        assert engine.confidence_threshold == 0.7
        assert engine.decay_half_life == 7

    def test_init_custom_config(self, config):
        """Test initialization with custom config"""
        engine = AttributionEngine(config=config)
        assert engine.attribution_window == 30
        assert engine.confidence_threshold == 0.7
        assert engine.decay_half_life == 7

    def test_position_weights(self, engine):
        """Test position weights configuration"""
        assert engine.position_weights['first'] == 0.4
        assert engine.position_weights['middle'] == 0.2
        assert engine.position_weights['last'] == 0.4

    def test_channel_mapping(self, engine):
        """Test channel type mapping"""
        mapping = engine.channel_mapping
        assert isinstance(mapping, dict)
        assert 'google' in mapping
        assert mapping['google'] == ChannelType.PAID_SEARCH

    # ===== 归因分析测试 =====
    def test_analyze_first_touch(self, engine, sample_touchpoint):
        """Test analyze with first-touch model"""
        touchpoints = [sample_touchpoint]
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        report = engine.analyze(
            touchpoints=touchpoints,
            model=AttributionModel.FIRST_TOUCH,
            start_date=start_date,
            end_date=end_date,
        )
        assert isinstance(report, AttributionReport)

    def test_analyze_last_touch(self, engine, sample_touchpoint):
        """Test analyze with last-touch model"""
        touchpoints = [sample_touchpoint]
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        report = engine.analyze(
            touchpoints=touchpoints,
            model=AttributionModel.LAST_TOUCH,
            start_date=start_date,
            end_date=end_date,
        )
        assert isinstance(report, AttributionReport)

    def test_analyze_linear(self, engine, sample_touchpoint):
        """Test analyze with linear model"""
        touchpoints = [sample_touchpoint]
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        report = engine.analyze(
            touchpoints=touchpoints,
            model=AttributionModel.LINEAR,
            start_date=start_date,
            end_date=end_date,
        )
        assert isinstance(report, AttributionReport)

    def test_analyze_time_decay(self, engine, sample_touchpoint):
        """Test analyze with time-decay model"""
        touchpoints = [sample_touchpoint]
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        report = engine.analyze(
            touchpoints=touchpoints,
            model=AttributionModel.TIME_DECAY,
            start_date=start_date,
            end_date=end_date,
        )
        assert isinstance(report, AttributionReport)

    def test_analyze_position_based(self, engine, sample_touchpoint):
        """Test analyze with position-based model"""
        touchpoints = [sample_touchpoint]
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        report = engine.analyze(
            touchpoints=touchpoints,
            model=AttributionModel.POSITION_BASED,
            start_date=start_date,
            end_date=end_date,
        )
        assert isinstance(report, AttributionReport)

    # ===== 辅助方法测试 =====
    def test_group_by_journey(self, engine, sample_touchpoint):
        """Test _group_by_journey method"""
        touchpoints = [sample_touchpoint]
        journeys = engine._group_by_journey(touchpoints)
        assert isinstance(journeys, dict)

    def test_calculate_attribution(self, engine, sample_touchpoint):
        """Test _calculate_attribution method"""
        touchpoints = [sample_touchpoint]
        journeys = engine._group_by_journey(touchpoints)
        results = engine._calculate_attribution(journeys, AttributionModel.LINEAR)
        assert isinstance(results, dict)

    # ===== 报告生成测试 =====
    def test_analyze_returns_report(self, engine, sample_touchpoint):
        """Test that analyze returns AttributionReport"""
        touchpoints = [sample_touchpoint]
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        report = engine.analyze(
            touchpoints=touchpoints,
            model=AttributionModel.LINEAR,
            start_date=start_date,
            end_date=end_date,
        )
        assert isinstance(report, AttributionReport)

    def test_report_structure(self, engine, sample_touchpoint):
        """Test attribution report structure"""
        touchpoints = [sample_touchpoint]
        start_date = datetime.now() - timedelta(days=30)
        end_date = datetime.now()
        report = engine.analyze(
            touchpoints=touchpoints,
            model=AttributionModel.LINEAR,
            start_date=start_date,
            end_date=end_date,
        )
        assert report.report_id is not None
        assert report.model is not None
        assert report.total_conversions >= 0
        assert isinstance(report.channel_results, dict)


class TestTouchPoint:
    """Test TouchPoint dataclass"""

    def test_create_touchpoint(self):
        """Test TouchPoint creation"""
        tp = TouchPoint(
            channel='google',
            channel_type=ChannelType.PAID_SEARCH,
            campaign='summer_sale',
            ad_group='adgroup_1',
            keyword='running shoes',
            timestamp=datetime.now(),
        )
        assert tp.channel == 'google'
        assert tp.channel_type == ChannelType.PAID_SEARCH
        assert tp.value == 0.0  # default
        assert tp.conversions == 0  # default

    def test_touchpoint_with_value(self):
        """Test TouchPoint with value and conversions"""
        tp = TouchPoint(
            channel='facebook',
            channel_type=ChannelType.SOCIAL_MEDIA,
            campaign='brand_awareness',
            ad_group='',
            keyword='',
            timestamp=datetime.now(),
            value=500.0,
            conversions=10,
            impressions=5000,
            clicks=200,
            cost=100.0,
        )
        assert tp.value == 500.0
        assert tp.conversions == 10
        assert tp.cost == 100.0


class TestAttributionResult:
    """Test AttributionResult dataclass"""

    def test_create_attribution_result(self):
        """Test AttributionResult creation"""
        result = AttributionResult(
            channel='google',
            channel_type=ChannelType.PAID_SEARCH,
            model=AttributionModel.LAST_TOUCH,
            total_touchpoints=10,
            conversions=5,
            revenue=1000.0,
            cost=200.0,
            attributed_conversions=2.5,
            attributed_revenue=500.0,
            attribution_weight=0.5,
            roi=4.0,
            cpa=40.0,
            roas=5.0,
            conversion_rate=0.1,
            click_rate=0.05,
            ctr=0.02,
            confidence=0.85,
        )
        assert result.channel == 'google'
        assert result.attributed_conversions == 2.5
        assert result.confidence == 0.85


class TestEnums:
    """Test enums"""

    def test_attribution_model_values(self):
        """Test AttributionModel enum values"""
        assert AttributionModel.FIRST_TOUCH.value == 'first_touch'
        assert AttributionModel.LAST_TOUCH.value == 'last_touch'
        assert AttributionModel.LINEAR.value == 'linear'
        assert AttributionModel.TIME_DECAY.value == 'time_decay'
        assert AttributionModel.POSITION_BASED.value == 'position_based'
        assert AttributionModel.DATA_DRIVEN.value == 'data_driven'

    def test_channel_type_values(self):
        """Test ChannelType enum values"""
        assert ChannelType.ORGANIC_SEARCH.value == 'organic_search'
        assert ChannelType.PAID_SEARCH.value == 'paid_search'
        assert ChannelType.SOCIAL_MEDIA.value == 'social_media'
        assert ChannelType.VIDEO_PLATFORM.value == 'video_platform'
        assert ChannelType.ECOMMERCE.value == 'ecommerce'
