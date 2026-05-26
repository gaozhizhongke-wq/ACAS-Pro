# -*- coding: utf-8 -*-
"""Tests for analytics/data_monitor.py"""

import pytest
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List

from acas_pro.analytics.data_monitor import (
    DataMonitor,
    MetricType,
    MetricData,
    PerformanceReport,
)
from unittest.mock import MagicMock, patch


class TestDataMonitor:
    """Test DataMonitor class"""

    @pytest.fixture
    def mock_db(self):
        """Mock DatabaseManager"""
        db = MagicMock()
        db.fetchone.return_value = None
        db.fetchall.return_value = []
        db.execute.return_value = None
        return db

    @pytest.fixture
    def monitor(self, mock_db):
        """Create DataMonitor with mocked DB"""
        with patch('acas_pro.analytics.data_monitor.DatabaseManager', return_value=mock_db):
            mon = DataMonitor(db=mock_db)
            mon.db = mock_db
            return mon

    @pytest.fixture
    def sample_metric_data(self):
        """Create sample metric data"""
        return MetricData(
            timestamp=datetime.now(),
            metric_type=MetricType.VIEWS,
            platform='douyin',
            account_id='acc_001',
            value=1000.0,
            content_id='vid_001',
        )

    # ===== 初始化测试 =====
    def test_init(self, mock_db):
        """Test DataMonitor initialization"""
        with patch('acas_pro.analytics.data_monitor.DatabaseManager', return_value=mock_db):
            mon = DataMonitor()
            assert mon.db is not None

    def test_init_with_db(self, mock_db):
        """Test initialization with provided DB"""
        mon = DataMonitor(db=mock_db)
        assert mon.db == mock_db

    def test_metric_type_values(self):
        """Test MetricType enum values"""
        assert MetricType.VIEWS.value == 'views'
        assert MetricType.LIKES.value == 'likes'
        assert MetricType.COMMENTS.value == 'comments'
        assert MetricType.SHARES.value == 'shares'
        assert MetricType.FOLLOWERS.value == 'followers'
        assert MetricType.ORDERS.value == 'orders'
        assert MetricType.REVENUE.value == 'revenue'
        assert MetricType.CTR.value == 'ctr'
        assert MetricType.CVR.value == 'cvr'

    # ===== 指标记录测试 =====
    def test_record_metric(self, monitor, mock_db):
        """Test recording a metric"""
        monitor.record_metric(
            metric_type=MetricType.VIEWS,
            platform='douyin',
            account_id='acc_001',
            value=1000.0,
            content_id='vid_001',
        )
        mock_db.execute.assert_called()

    def test_record_metric_with_timestamp(self, monitor, mock_db):
        """Test recording a metric with custom timestamp"""
        custom_time = datetime.now() - timedelta(hours=1)
        monitor.record_metric(
            metric_type=MetricType.LIKES,
            platform='xiaohongshu',
            account_id='acc_002',
            value=500.0,
            timestamp=custom_time,
        )
        mock_db.execute.assert_called()

    # ===== 指标查询测试 =====
    def test_get_metrics(self, monitor, mock_db, sample_metric_data):
        """Test getting metrics"""
        # Mock the database response
        mock_db.fetchall.return_value = [{
            'timestamp': datetime.now().isoformat(),
            'metric_type': 'views',
            'platform': 'douyin',
            'account_id': 'acc_001',
            'value': 1000.0,
            'content_id': 'vid_001',
        }]
        
        metrics = monitor.get_metrics(
            metric_type=MetricType.VIEWS,
            platform='douyin',
            account_id='acc_001',
            start_time=datetime.now() - timedelta(days=7),
            end_time=datetime.now(),
        )
        assert isinstance(metrics, list)

    def test_get_metrics_no_filters(self, monitor, mock_db):
        """Test getting metrics without filters"""
        mock_db.fetchall.return_value = []
        metrics = monitor.get_metrics(
            metric_type=MetricType.LIKES,
        )
        assert isinstance(metrics, list)

    # ===== 每日聚合测试 =====
    def test_aggregate_daily(self, monitor, mock_db):
        """Test daily aggregation"""
        mock_db.fetchone.return_value = {
            'views': 10000,
            'likes': 500,
            'comments': 100,
            'shares': 50,
            'new_followers': 20,
            'orders': 5,
            'revenue': 1000.0,
        }
        
        monitor.aggregate_daily(
            platform='douyin',
            account_id='acc_001',
            date=datetime.now(),
        )
        mock_db.execute.assert_called()

    # ===== 报告生成测试 =====
    def test_generate_report(self, monitor, mock_db):
        """Test generating performance report"""
        mock_db.fetchone.return_value = {
            'total_views': 100000,
            'total_likes': 5000,
            'total_comments': 1000,
            'total_shares': 500,
            'follower_growth': 200,
            'total_orders': 50,
            'total_revenue': 10000.0,
            'days': 7,
        }
        
        report = monitor.generate_report(
            period_start=datetime.now() - timedelta(days=7),
            period_end=datetime.now(),
            platform='douyin',
            account_id='acc_001',
        )
        assert isinstance(report, PerformanceReport)

    def test_generate_report_empty(self, monitor, mock_db):
        """Test generating report with no data"""
        mock_db.fetchone.return_value = None
        
        report = monitor.generate_report(
            period_start=datetime.now() - timedelta(days=7),
            period_end=datetime.now(),
        )
        assert isinstance(report, PerformanceReport)
        assert report.total_views == 0

    # ===== 异常检测测试 =====
    def test_check_anomalies(self, monitor, mock_db):
        """Test anomaly detection"""
        # Mock 7 days of data
        mock_db.fetchall.return_value = [
            {'date': (datetime.now() - timedelta(days=i)).date().isoformat(), 
             'views': 10000, 'likes': 500, 'comments': 100, 'shares': 50}
            for i in range(7)
        ]
        # Make the last day's views drop by 60%
        mock_db.fetchall.return_value[-1]['views'] = 4000
        
        alerts = monitor.check_anomalies(
            platform='douyin',
            account_id='acc_001',
        )
        assert isinstance(alerts, list)

    def test_check_anomalies_insufficient_data(self, monitor, mock_db):
        """Test anomaly detection with insufficient data"""
        mock_db.fetchall.return_value = []  # Less than 3 days
        
        alerts = monitor.check_anomalies(
            platform='douyin',
            account_id='acc_001',
        )
        assert alerts == []

    # ===== 预警管理测试 =====
    def test_create_alert(self, monitor, mock_db):
        """Test creating an alert"""
        monitor.create_alert(
            alert_type='views_drop',
            message='Views dropped by 60%',
            severity='warning',
            platform='douyin',
            account_id='acc_001',
        )
        mock_db.execute.assert_called()

    def test_get_alerts(self, monitor, mock_db):
        """Test getting alerts"""
        mock_db.fetchall.return_value = []
        
        alerts = monitor.get_alerts(
            acknowledged=False,
            severity='warning',
        )
        assert isinstance(alerts, list)

    def test_get_alerts_all(self, monitor, mock_db):
        """Test getting all alerts"""
        mock_db.fetchall.return_value = []
        
        alerts = monitor.get_alerts(acknowledged=False)
        assert isinstance(alerts, list)

    def test_acknowledge_alert(self, monitor, mock_db):
        """Test acknowledging an alert"""
        monitor.acknowledge_alert(alert_id=1, user='admin')
        mock_db.execute.assert_called()


class TestMetricData:
    """Test MetricData dataclass"""

    def test_metric_data_creation(self):
        """Test MetricData creation"""
        md = MetricData(
            timestamp=datetime.now(),
            metric_type=MetricType.VIEWS,
            platform='douyin',
            account_id='acc_001',
            value=1000.0,
        )
        assert md.metric_type == MetricType.VIEWS
        assert md.platform == 'douyin'
        assert md.value == 1000.0
        assert md.content_id is None  # default

    def test_metric_data_with_content(self):
        """Test MetricData with content_id"""
        md = MetricData(
            timestamp=datetime.now(),
            metric_type=MetricType.LIKES,
            platform='xiaohongshu',
            account_id='acc_002',
            value=500.0,
            content_id='post_001',
        )
        assert md.content_id == 'post_001'


class TestPerformanceReport:
    """Test PerformanceReport dataclass"""

    def test_performance_report_creation(self):
        """Test PerformanceReport creation"""
        report = PerformanceReport(
            period_start=datetime.now() - timedelta(days=7),
            period_end=datetime.now(),
            platform='douyin',
            account_id='acc_001',
        )
        assert report.platform == 'douyin'
        assert report.total_views == 0  # default
        assert report.total_likes == 0  # default
        assert report.engagement_rate == 0.0  # default

    def test_performance_report_calculations(self):
        """Test PerformanceReport with calculated values"""
        report = PerformanceReport(
            period_start=datetime.now() - timedelta(days=7),
            period_end=datetime.now(),
            platform='douyin',
            account_id='acc_001',
            total_views=100000,
            total_likes=5000,
            total_comments=1000,
            total_shares=500,
            follower_growth=200,
            total_orders=50,
            total_revenue=10000.0,
        )
        assert report.total_views == 100000
        assert report.engagement_rate == 0.0  # calculated later
        assert report.avg_order_value == 0.0  # calculated later
