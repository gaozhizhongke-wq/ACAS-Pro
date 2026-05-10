#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Data Monitor Tests
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from acas_pro.analytics.data_monitor import (
    DataMonitor, MetricData, PerformanceReport,
    MetricType
)


class TestMetricType:
    """Metric type enum tests"""
    
    def test_metric_type_values(self):
        """Test metric type values"""
        assert MetricType.VIEWS.value == "views"
        assert MetricType.LIKES.value == "likes"
        assert MetricType.COMMENTS.value == "comments"
        assert MetricType.SHARES.value == "shares"
        assert MetricType.FOLLOWERS.value == "followers"
        assert MetricType.ORDERS.value == "orders"
        assert MetricType.REVENUE.value == "revenue"
        assert MetricType.CTR.value == "ctr"
        assert MetricType.CVR.value == "cvr"


class TestMetricData:
    """Metric data tests"""
    
    def test_metric_data_creation(self):
        """Test metric data creation"""
        data = MetricData(
            timestamp=datetime.now(),
            metric_type=MetricType.VIEWS,
            platform="douyin",
            account_id="acc_001",
            value=1000.0,
            content_id="content_001"
        )
        
        assert data.metric_type == MetricType.VIEWS
        assert data.value == 1000.0


class TestDataMonitor:
    """Data monitor tests"""
    
    @pytest.fixture
    def mock_db(self):
        mock = Mock()
        mock.execute = Mock()
        mock.fetchone = Mock(return_value=None)
        mock.fetchall = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def monitor(self, mock_db):
        return DataMonitor(db=mock_db)
    
    def test_init(self, monitor, mock_db):
        """Test initialization"""
        assert monitor.db == mock_db
        mock_db.execute.assert_called()
    
    def test_record_metric(self, monitor, mock_db):
        """Test record metric"""
        monitor.record_metric(
            metric_type=MetricType.VIEWS,
            platform="douyin",
            account_id="acc_001",
            value=1000.0,
            content_id="content_001"
        )
        
        mock_db.execute.assert_called()
    
    def test_get_metrics_empty(self, monitor, mock_db):
        """Test get metrics with no data"""
        mock_db.fetchall.return_value = []
        
        metrics = monitor.get_metrics(
            metric_type=MetricType.VIEWS,
            platform="douyin"
        )
        
        assert metrics == []
    
    def test_get_metrics_with_data(self, monitor, mock_db):
        """Test get metrics with data"""
        mock_db.fetchall.return_value = [
            {
                "timestamp": datetime.now().isoformat(),
                "metric_type": "views",
                "platform": "douyin",
                "account_id": "acc_001",
                "value": 1000.0,
                "content_id": "content_001"
            }
        ]
        
        metrics = monitor.get_metrics(
            metric_type=MetricType.VIEWS,
            platform="douyin"
        )
        
        assert len(metrics) == 1
        assert metrics[0].value == 1000.0
    
    def test_aggregate_daily(self, monitor, mock_db):
        """Test aggregate daily"""
        mock_db.fetchone.return_value = {
            "views": 1000,
            "likes": 100,
            "comments": 10,
            "shares": 5,
            "new_followers": 50,
            "orders": 2,
            "revenue": 200.0
        }
        
        monitor.aggregate_daily(
            platform="douyin",
            account_id="acc_001",
            date=datetime.now()
        )
        
        mock_db.execute.assert_called()
    
    def test_generate_report(self, monitor, mock_db):
        """Test generate report"""
        mock_db.fetchone.return_value = {
            "total_views": 10000,
            "total_likes": 1000,
            "total_comments": 100,
            "total_shares": 50,
            "follower_growth": 200,
            "total_orders": 10,
            "total_revenue": 1000.0,
            "days": 7,
            "views": 10000,
            "likes": 1000,
            "comments": 100,
            "shares": 50,
            "revenue": 1000.0,
            "orders": 10
        }
        
        start = datetime.now() - timedelta(days=7)
        end = datetime.now()
        
        report = monitor.generate_report(
            period_start=start,
            period_end=end,
            platform="douyin",
            account_id="acc_001"
        )
        
        assert report is not None
        assert report.total_views == 10000
        assert report.total_revenue == 1000.0
    
    def test_check_anomalies_empty(self, monitor, mock_db):
        """Test check anomalies with no data"""
        mock_db.fetchall.return_value = []
        
        alerts = monitor.check_anomalies("douyin", "acc_001")
        
        assert alerts == []
    
    def test_check_anomalies_views_drop(self, monitor, mock_db):
        """Test check anomalies with views drop"""
        mock_db.fetchall.return_value = [
            {"date": "2024-01-01", "views": 1000, "likes": 100, "comments": 10, "shares": 5},
            {"date": "2024-01-02", "views": 900, "likes": 90, "comments": 9, "shares": 4},
            {"date": "2024-01-03", "views": 100, "likes": 10, "comments": 1, "shares": 0},
        ]
        
        alerts = monitor.check_anomalies("douyin", "acc_001")
        
        assert len(alerts) > 0
        assert alerts[0]["type"] == "views_drop"
    
    def test_create_alert(self, monitor, mock_db):
        """Test create alert"""
        monitor.create_alert(
            alert_type="views_drop",
            message="Views dropped significantly",
            severity="warning",
            platform="douyin",
            account_id="acc_001"
        )
        
        mock_db.execute.assert_called()
    
    def test_get_alerts_empty(self, monitor, mock_db):
        """Test get alerts with no data"""
        mock_db.fetchall.return_value = []
        
        alerts = monitor.get_alerts()
        
        assert alerts == []
    
    def test_acknowledge_alert(self, monitor, mock_db):
        """Test acknowledge alert"""
        monitor.acknowledge_alert(alert_id=1, user="admin")
        
        mock_db.execute.assert_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
