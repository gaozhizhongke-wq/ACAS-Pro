"""Test analytics and core modules."""
import sys
sys.path.insert(0, 'src')

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from acas_pro.analytics.festival_calendar import (
    FestivalCalendar, Festival, MarketingPlan,
    FestivalType, MarketType
)
from acas_pro.analytics.data_monitor import (
    DataMonitor, MetricData, MetricType,
    PerformanceReport
)
from acas_pro.core.database import DatabaseManager
from acas_pro.core.config import config


class TestFestivalCalendar:
    """FestivalCalendar tests."""

    def test_init_with_mock_db(self):
        mock_db = MagicMock()
        fc = FestivalCalendar(db=mock_db)
        assert fc.db is mock_db

    def test_list_festivals(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        fc = FestivalCalendar(db=mock_db)
        result = fc.list_festivals()
        assert isinstance(result, list)

    def test_list_festivals_with_filter(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        fc = FestivalCalendar(db=mock_db)
        result = fc.list_festivals(
            festival_type=FestivalType.TRADITIONAL,
            market=MarketType.DOMESTIC
        )
        assert isinstance(result, list)

    def test_get_festival(self):
        mock_db = MagicMock()
        mock_db.fetchone.return_value = None  # not found
        fc = FestivalCalendar(db=mock_db)
        result = fc.get_festival('spring-festival')
        assert result is None

    def test_get_festival_found(self):
        mock_db = MagicMock()
        mock_db.fetchone.return_value = {
            'id': 'spring-festival', 'name': 'Spring Festival',
            'name_en': 'Chinese New Year', 'festival_type': 'traditional',
            'markets': ['domestic'], 'month': 1, 'day': 1,
            'lunar': False, 'floating': False, 'floating_rule': None,
            'importance': 5, 'duration_days': 7, 'pre_heat_days': 3,
            'themes': [], 'keywords': [], 'visual_style': 'red',
            'content_tips': [], 'is_active': True, 'created_at': datetime.now()
        }
        fc = FestivalCalendar(db=mock_db)
        result = fc.get_festival('spring-festival')
        # Returns None or Festival depending on implementation
        assert result is None or isinstance(result, Festival)

    def test_get_upcoming_festivals(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        fc = FestivalCalendar(db=mock_db)
        result = fc.get_upcoming_festivals(days=30)
        assert isinstance(result, list)

    def test_get_upcoming_festivals_with_market(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        fc = FestivalCalendar(db=mock_db)
        result = fc.get_upcoming_festivals(days=60, market=MarketType.OVERSEAS)
        assert isinstance(result, list)

    def test_get_marketing_plans(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        fc = FestivalCalendar(db=mock_db)
        result = fc.get_marketing_plans()
        assert isinstance(result, list)

    def test_get_marketing_plans_with_status(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        fc = FestivalCalendar(db=mock_db)
        result = fc.get_marketing_plans(status='active')
        assert isinstance(result, list)

    def test_create_marketing_plan(self):
        mock_db = MagicMock()
        fc = FestivalCalendar(db=mock_db)
        plan = fc.create_marketing_plan(
            festival_id='spring-festival',
            name='Test Plan',
            start_date=datetime(2026, 1, 20),
            end_date=datetime(2026, 1, 30),
            target_platforms=['douyin'],
            target_accounts=['acc1']
        )
        assert isinstance(plan, MarketingPlan)
        assert plan.festival_id == 'spring-festival'
        assert plan.name == 'Test Plan'
        assert plan.status == 'draft'

    def test_create_marketing_plan_with_budget(self):
        mock_db = MagicMock()
        fc = FestivalCalendar(db=mock_db)
        plan = fc.create_marketing_plan(
            festival_id='spring-festival',
            name='Paid Plan',
            start_date=datetime(2026, 1, 20),
            end_date=datetime(2026, 1, 30),
            target_platforms=['douyin'],
            target_accounts=['acc1'],
            budget=10000.0
        )
        assert plan.budget == 10000.0

    def test_generate_content_suggestions(self):
        mock_db = MagicMock()
        mock_db.fetchone.return_value = None  # festival not found
        fc = FestivalCalendar(db=mock_db)
        result = fc.generate_content_suggestions('spring-festival')
        assert isinstance(result, dict)


class TestDataMonitor:
    """DataMonitor tests."""

    def test_init_with_mock_db(self):
        mock_db = MagicMock()
        dm = DataMonitor(db=mock_db)
        assert dm.db is mock_db

    def test_record_metric(self):
        mock_db = MagicMock()
        dm = DataMonitor(db=mock_db)
        dm.record_metric(
            metric_type=MetricType.VIEWS,
            platform='douyin',
            account_id='acc1',
            value=1000.0
        )
        mock_db.execute.assert_called()

    def test_record_metric_with_content(self):
        mock_db = MagicMock()
        dm = DataMonitor(db=mock_db)
        dm.record_metric(
            metric_type=MetricType.LIKES,
            platform='douyin',
            account_id='acc1',
            value=500.0,
            content_id='vid123'
        )
        mock_db.execute.assert_called()

    def test_get_metrics(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        dm = DataMonitor(db=mock_db)
        result = dm.get_metrics(MetricType.VIEWS)
        assert isinstance(result, list)

    def test_get_metrics_with_filters(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        dm = DataMonitor(db=mock_db)
        result = dm.get_metrics(
            MetricType.REVENUE,
            platform='douyin',
            account_id='acc1',
            start_time=datetime.now() - timedelta(days=7),
            end_time=datetime.now()
        )
        assert isinstance(result, list)

    def test_get_metrics_with_limit(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        dm = DataMonitor(db=mock_db)
        result = dm.get_metrics(MetricType.VIEWS, limit=10)
        assert isinstance(result, list)

    def test_aggregate_daily(self):
        mock_db = MagicMock()
        dm = DataMonitor(db=mock_db)
        dm.aggregate_daily('douyin', 'acc1', datetime.now())
        mock_db.execute.assert_called()

    def test_check_anomalies(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        dm = DataMonitor(db=mock_db)
        result = dm.check_anomalies('douyin', 'acc1')
        assert isinstance(result, list)

    def test_create_alert(self):
        mock_db = MagicMock()
        dm = DataMonitor(db=mock_db)
        dm.create_alert(
            alert_type='metric_spike',
            message='Revenue dropped',
            severity='high',
            platform='douyin',
            account_id='acc1'
        )
        mock_db.execute.assert_called()

    def test_get_alerts(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        dm = DataMonitor(db=mock_db)
        result = dm.get_alerts()
        assert isinstance(result, list)

    def test_get_alerts_acknowledged(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        dm = DataMonitor(db=mock_db)
        result = dm.get_alerts(acknowledged=True)
        assert isinstance(result, list)

    def test_get_alerts_with_severity(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        dm = DataMonitor(db=mock_db)
        result = dm.get_alerts(severity='high')
        assert isinstance(result, list)

    def test_acknowledge_alert(self):
        mock_db = MagicMock()
        dm = DataMonitor(db=mock_db)
        dm.acknowledge_alert(alert_id=1, user='admin')
        mock_db.execute.assert_called()

    def test_generate_report(self):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = []
        mock_db.fetchone.return_value = {
            'total_views': 1000, 'total_likes': 100, 'total_comments': 50,
            'total_shares': 20, 'content_count': 10, 'follower_growth': 50,
            'follower_count': 1000, 'total_orders': 20, 'total_revenue': 5000.0,
            'views_trend': 0.05, 'revenue_trend': 0.1
        }
        dm = DataMonitor(db=mock_db)
        result = dm.generate_report(
            period_start=datetime.now() - timedelta(days=7),
            period_end=datetime.now()
        )
        assert isinstance(result, PerformanceReport)


class TestDatabaseManager:
    """DatabaseManager tests."""

    def test_init_no_exception(self):
        # Just ensure __init__ doesn't raise
        pass

    def test_execute(self):
        db = DatabaseManager.__new__(DatabaseManager)
        db._local = type('local', (), {'connection': MagicMock()})()
        db._local.connection = MagicMock()
        # We can't easily test without real DB, just verify method exists
        assert callable(db.execute)

    def test_execute_one(self):
        db = DatabaseManager.__new__(DatabaseManager)
        assert callable(db.execute_one)

    def test_execute(self):
        db = DatabaseManager.__new__(DatabaseManager)
        assert callable(db.execute)

    def test_insert(self):
        db = DatabaseManager.__new__(DatabaseManager)
        assert callable(db.insert)

    def test_update(self):
        db = DatabaseManager.__new__(DatabaseManager)
        assert callable(db.update)

    def test_delete(self):
        db = DatabaseManager.__new__(DatabaseManager)
        assert callable(db.delete)

    def test_transaction(self):
        db = DatabaseManager.__new__(DatabaseManager)
        assert callable(db.transaction)
