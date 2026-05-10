#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Analytics Logic Tests
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from acas_pro.ui.logic.analytics_logic import (
    AnalyticsLogic, MetricData, AnalyticsReport,
    MetricType, TimeRange
)


class TestMetricType:
    """Test metric type enum"""
    
    def test_metric_type_values(self):
        """Test metric type enum values"""
        assert MetricType.VIEWS.value == "views"
        assert MetricType.LIKES.value == "likes"
        assert MetricType.REVENUE.value == "revenue"


class TestTimeRange:
    """Test time range enum"""
    
    def test_time_range_values(self):
        """Test time range enum values"""
        assert TimeRange.TODAY.value == "today"
        assert TimeRange.LAST_7_DAYS.value == "7d"
        assert TimeRange.CUSTOM.value == "custom"


class TestMetricData:
    """Test metric data structure"""
    
    def test_metric_data_creation(self):
        """Test metric data creation"""
        data = MetricData(
            timestamp=datetime.now(),
            value=100.0,
            platform="douyin",
            metric_type=MetricType.VIEWS
        )
        assert data.value == 100.0
        assert data.platform == "douyin"
    
    def test_metric_data_types(self):
        """Test metric data types"""
        now = datetime.now()
        data = MetricData(
            timestamp=now,
            value=50.5,
            platform="xiaohongshu",
            metric_type=MetricType.LIKES
        )
        assert isinstance(data.timestamp, datetime)
        assert isinstance(data.value, float)


class TestAnalyticsReport:
    """Test analytics report structure"""
    
    def test_report_creation(self):
        """Test report creation"""
        now = datetime.now()
        report = AnalyticsReport(
            period_start=now - timedelta(days=7),
            period_end=now,
            metrics={},
            summary={"total": 1000},
            trends={"growth": 5.5}
        )
        assert report.summary["total"] == 1000
        assert report.trends["growth"] == 5.5


class TestAnalyticsLogic:
    """Test analytics logic"""
    
    @pytest.fixture
    def logic(self):
        return AnalyticsLogic()
    
    def test_init(self, logic):
        """Test initialization"""
        assert logic._data_cache == {}
    
    def test_get_time_range_today(self, logic):
        """Test getting today's time range"""
        start, end = logic.get_time_range(TimeRange.TODAY)
        
        assert start.hour == 0
        assert start.minute == 0
        assert end <= datetime.now()
    
    def test_get_time_range_yesterday(self, logic):
        """Test getting yesterday's time range"""
        start, end = logic.get_time_range(TimeRange.YESTERDAY)
        
        assert (end - start).days == 1
        assert start.hour == 0
    
    def test_get_time_range_last_7_days(self, logic):
        """Test getting last 7 days range"""
        start, end = logic.get_time_range(TimeRange.LAST_7_DAYS)
        
        assert (end - start).days == 7
    
    def test_get_time_range_last_30_days(self, logic):
        """Test getting last 30 days range"""
        start, end = logic.get_time_range(TimeRange.LAST_30_DAYS)
        
        assert (end - start).days == 30
    
    def test_get_time_range_this_month(self, logic):
        """Test getting this month's range"""
        start, end = logic.get_time_range(TimeRange.THIS_MONTH)
        
        assert start.day == 1
        assert start.hour == 0
    
    def test_get_time_range_custom(self, logic):
        """Test getting custom range"""
        custom_start = datetime(2024, 1, 1)
        custom_end = datetime(2024, 1, 31)
        
        start, end = logic.get_time_range(
            TimeRange.CUSTOM,
            custom_start=custom_start,
            custom_end=custom_end
        )
        
        assert start == custom_start
        assert end == custom_end
    
    def test_get_time_range_default(self, logic):
        """Test default time range"""
        start, end = logic.get_time_range(TimeRange.CUSTOM)
        
        assert (end - start).days == 7
    
    def test_aggregate_metrics_by_day(self, logic):
        """Test aggregating metrics by day"""
        now = datetime.now()
        data = [
            MetricData(timestamp=now, value=10, platform="p1", metric_type=MetricType.VIEWS),
            MetricData(timestamp=now, value=20, platform="p2", metric_type=MetricType.VIEWS),
        ]
        
        result = logic.aggregate_metrics(data, group_by="day")
        
        assert len(result) == 1
        key = now.strftime("%Y-%m-%d")
        assert key in result
        assert result[key][0].value == 30
    
    def test_aggregate_metrics_by_hour(self, logic):
        """Test aggregating metrics by hour"""
        now = datetime.now()
        data = [
            MetricData(timestamp=now, value=10, platform="p1", metric_type=MetricType.VIEWS),
        ]
        
        result = logic.aggregate_metrics(data, group_by="hour")
        
        key = now.strftime("%Y-%m-%d %H:00")
        assert key in result
    
    def test_calculate_growth_rate_positive(self, logic):
        """Test positive growth rate"""
        rate = logic.calculate_growth_rate(110, 100)
        assert rate == 10.0
    
    def test_calculate_growth_rate_negative(self, logic):
        """Test negative growth rate"""
        rate = logic.calculate_growth_rate(90, 100)
        assert rate == -10.0
    
    def test_calculate_growth_rate_zero_previous(self, logic):
        """Test growth rate with zero previous"""
        rate = logic.calculate_growth_rate(100, 0)
        assert rate == 100.0
    
    def test_calculate_growth_rate_zero_current(self, logic):
        """Test growth rate with zero current"""
        rate = logic.calculate_growth_rate(0, 0)
        assert rate == 0.0
    
    def test_calculate_engagement_rate(self, logic):
        """Test engagement rate calculation"""
        rate = logic.calculate_engagement_rate(50, 1000)
        assert rate == 5.0
    
    def test_calculate_engagement_rate_zero_views(self, logic):
        """Test engagement rate with zero views"""
        rate = logic.calculate_engagement_rate(50, 0)
        assert rate == 0.0
    
    def test_generate_summary(self, logic):
        """Test summary generation"""
        now = datetime.now()
        data = [
            MetricData(timestamp=now, value=10, platform="p1", metric_type=MetricType.VIEWS),
            MetricData(timestamp=now, value=20, platform="p2", metric_type=MetricType.VIEWS),
            MetricData(timestamp=now, value=30, platform="p3", metric_type=MetricType.VIEWS),
        ]
        
        summary = logic.generate_summary(data)
        
        assert summary["total"] == 60
        assert summary["average"] == 20
        assert summary["max"] == 30
        assert summary["min"] == 10
    
    def test_generate_summary_empty(self, logic):
        """Test summary with empty data"""
        summary = logic.generate_summary([])
        
        assert summary["total"] == 0
        assert summary["average"] == 0
    
    def test_compare_periods(self, logic):
        """Test period comparison"""
        now = datetime.now()
        current = [
            MetricData(timestamp=now, value=110, platform="p1", metric_type=MetricType.VIEWS),
        ]
        previous = [
            MetricData(timestamp=now - timedelta(days=7), value=100, platform="p1", metric_type=MetricType.VIEWS),
        ]
        
        result = logic.compare_periods(current, previous)
        
        assert result["growth_rate"] == 10.0
        assert result["current_total"] == 110
        assert result["previous_total"] == 100
        assert result["difference"] == 10
    
    def test_export_report(self, logic):
        """Test report export"""
        now = datetime.now()
        report = AnalyticsReport(
            period_start=now - timedelta(days=7),
            period_end=now,
            metrics={},
            summary={"total": 1000},
            trends={"growth": 5.5}
        )
        
        exported = logic.export_report(report)
        
        assert "period" in exported
        assert "summary" in exported
        assert "1000" in exported
    
    def test_detect_anomalies(self, logic):
        """Test anomaly detection"""
        now = datetime.now()
        data = [
            MetricData(timestamp=now + timedelta(hours=i), value=10, platform="p1", metric_type=MetricType.VIEWS)
            for i in range(10)
        ]
        # Add an outlier
        data.append(MetricData(timestamp=now + timedelta(hours=10), value=1000, platform="p1", metric_type=MetricType.VIEWS))
        
        anomalies = logic.detect_anomalies(data, threshold=2.0)
        
        assert len(anomalies) >= 1
        assert anomalies[0].value == 1000
    
    def test_detect_anomalies_empty(self, logic):
        """Test anomaly detection with empty data"""
        anomalies = logic.detect_anomalies([])
        assert anomalies == []
    
    def test_detect_anomalies_single_item(self, logic):
        """Test anomaly detection with single item"""
        now = datetime.now()
        data = [MetricData(timestamp=now, value=10, platform="p1", metric_type=MetricType.VIEWS)]
        
        anomalies = logic.detect_anomalies(data)
        assert anomalies == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
