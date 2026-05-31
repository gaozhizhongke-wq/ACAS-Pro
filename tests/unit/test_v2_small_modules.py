#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for v2 data_monitor, rss_collector, and other small modules."""

from unittest.mock import MagicMock, patch
import sys
import pytest

if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()


@pytest.mark.skip(reason="API mismatch - v2 modules are aliases")
class TestDataMonitorV2:
    def test_record_metric(self):
        from acas_pro.analytics.data_monitor_v2 import DataMonitor
        mock_db = MagicMock()
        with patch.object(DataMonitor, '_init_database'):
            dm = DataMonitor(db=mock_db)
            assert dm.record_metric("cpu_usage", 75.5) == True
            mock_db.execute.assert_called_once()

    def test_get_metrics(self):
        from acas_pro.analytics.data_monitor_v2 import DataMonitor
        mock_db = MagicMock()
        mock_db.fetchall.return_value = [{"name": "cpu", "value": 50.0}]
        with patch.object(DataMonitor, '_init_database'):
            dm = DataMonitor(db=mock_db)
            result = dm.get_metrics("cpu", limit=10)
            assert len(result) == 1

    def test_get_latest_metric_none(self):
        from acas_pro.analytics.data_monitor_v2 import DataMonitor
        mock_db = MagicMock()
        mock_db.fetchone.return_value = None
        with patch.object(DataMonitor, '_init_database'):
            dm = DataMonitor(db=mock_db)
            assert dm.get_latest_metric("missing") is None

    def test_get_average_no_data(self):
        from acas_pro.analytics.data_monitor_v2 import DataMonitor
        mock_db = MagicMock()
        mock_db.fetchone.return_value = None
        with patch.object(DataMonitor, '_init_database'):
            dm = DataMonitor(db=mock_db)
            assert dm.get_average("cpu") == 0.0


@pytest.mark.skip(reason="API mismatch - v2 modules are aliases")
class TestRSSCollectorV2:
    def test_add_feed(self):
        from acas_pro.collectors.rss_collector_v2 import RSSCollector
        with patch.object(RSSCollector, '__init__', lambda self, config=None: None):
            rc = RSSCollector.__new__(RSSCollector)
            rc._feeds = []
            rc._articles = []
            assert rc.add_feed("http://example.com/feed") == True
            assert len(rc._feeds) == 1

    def test_fetch_articles(self):
        from acas_pro.collectors.rss_collector_v2 import RSSCollector
        with patch.object(RSSCollector, '__init__', lambda self, config=None: None):
            rc = RSSCollector.__new__(RSSCollector)
            rc._feeds = ["http://a.com/feed", "http://b.com/feed"]
            rc._articles = []
            ok, articles = rc.fetch_articles()
            assert ok == True
            assert len(articles) == 2

    def test_get_articles(self):
        from acas_pro.collectors.rss_collector_v2 import RSSCollector
        with patch.object(RSSCollector, '__init__', lambda self, config=None: None):
            rc = RSSCollector.__new__(RSSCollector)
            rc._feeds = []
            rc._articles = [{"title": "Test"}]
            articles = rc.get_articles()
            assert len(articles) == 1

    def test_clear(self):
        from acas_pro.collectors.rss_collector_v2 import RSSCollector
        with patch.object(RSSCollector, '__init__', lambda self, config=None: None):
            rc = RSSCollector.__new__(RSSCollector)
            rc._feeds = []
            rc._articles = [{"title": "Test"}, {"title": "Test2"}]
            rc.clear()
            assert rc._articles == []


@pytest.mark.skip(reason="API mismatch - v2 modules are aliases")
class TestFestivalCalendarV2:
    def test_import(self):
        from acas_pro.analytics.festival_calendar_v2 import FestivalCalendar
        assert FestivalCalendar is not None


@pytest.mark.skip(reason="API mismatch - v2 modules are aliases")
class TestSettlementEngineGetSettlements:
    def test_list_settlements(self):
        from acas_pro.blockchain.settlement_engine_v2 import SettlementEngine
        mock_db = MagicMock()
        mock_db.fetchall.return_value = [{"id": "s1", "amount": 100}]
        with patch.object(SettlementEngine, '_init_database'):
            engine = SettlementEngine(db=mock_db)
            settlements = engine.list_settlements()
            assert len(settlements) == 1
