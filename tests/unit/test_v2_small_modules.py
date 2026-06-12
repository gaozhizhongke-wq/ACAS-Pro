#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for v2 module aliases."""


class TestDataMonitorV2:
    """Test data_monitor_v2 is a valid alias."""

    def test_import(self):
        from acas_pro.analytics.data_monitor_v2 import DataMonitor
        assert DataMonitor is not None


class TestRSSCollectorV2:
    """Test rss_collector_v2 is a valid alias."""

    def test_import(self):
        from acas_pro.collectors.rss_collector_v2 import RSSCollectorV2
        assert RSSCollectorV2 is not None


class TestFestivalCalendarV2:
    """Test festival_calendar_v2 was removed."""

    def test_module_removed(self):
        import importlib.util
        spec = importlib.util.find_spec("acas_pro.analytics.festival_calendar_v2")
        assert spec is None


class TestSettlementEngineV2:
    """Test settlement_engine_v2 is a valid alias."""

    def test_import(self):
        from acas_pro.blockchain.settlement_engine_v2 import SettlementEngine
        assert SettlementEngine is not None
