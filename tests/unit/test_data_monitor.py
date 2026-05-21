#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for analytics/data_monitor.py module."""

from datetime import datetime
from unittest.mock import MagicMock, patch
import sys
import pytest

if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()

from acas_pro.analytics.data_monitor import (
    MetricType, MetricData, PerformanceReport, DataMonitor
)


class TestMetricType:
    def test_values(self):
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
    def test_creation(self):
        m = MetricData(
            timestamp=datetime.now(), metric_type=MetricType.VIEWS,
            platform="douyin", account_id="acct1", value=1000.0
        )
        assert m.metric_type == MetricType.VIEWS
        assert m.value == 1000.0
        assert m.content_id is None
    
    def test_with_content_id(self):
        m = MetricData(
            timestamp=datetime.now(), metric_type=MetricType.LIKES,
            platform="wechat", account_id="acct2", value=50.0,
            content_id="post_001"
        )
        assert m.content_id == "post_001"


class TestPerformanceReport:
    def test_default_report(self):
        r = PerformanceReport(
            period_start=datetime(2026, 1, 1),
            period_end=datetime(2026, 1, 31),
            platform="douyin", account_id="acct1"
        )
        assert r.total_views == 0
        assert r.total_revenue == 0.0
        assert r.engagement_rate == 0.0
        assert r.views_trend == 0.0
    
    def test_custom_report(self):
        r = PerformanceReport(
            period_start=datetime(2026, 5, 1),
            period_end=datetime(2026, 5, 17),
            platform="douyin", account_id="acct1",
            total_views=50000, total_likes=3000,
            total_orders=100, total_revenue=15000.0,
            engagement_rate=0.06
        )
        assert r.total_views == 50000
        assert r.total_orders == 100
        assert r.engagement_rate == 0.06
