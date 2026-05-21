#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for analytics/festival_calendar.py dataclasses and enums."""

from unittest.mock import MagicMock
import sys
import pytest

if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()


class TestFestivalTypeEnum:
    def test_values(self):
        from acas_pro.analytics.festival_calendar import FestivalType
        assert FestivalType.TRADITIONAL.value == "traditional"
        assert FestivalType.SHOPPING.value == "shopping"
        assert len(FestivalType) == 6

class TestMarketTypeEnum:
    def test_values(self):
        from acas_pro.analytics.festival_calendar import MarketType
        assert MarketType.DOMESTIC.value == "domestic"
        assert MarketType.OVERSEAS.value == "overseas"
        assert len(MarketType) >= 6

class TestFestival:
    def test_defaults(self):
        from acas_pro.analytics.festival_calendar import Festival, FestivalType, MarketType
        f = Festival(
            id="f1", name="春节", name_en="Spring Festival",
            festival_type=FestivalType.TRADITIONAL, markets=[MarketType.DOMESTIC],
            month=1, day=1
        )
        assert f.importance == 3
        assert f.duration_days == 1
        assert f.pre_heat_days == 7
        assert f.lunar == False  # default is False

    def test_custom_festival(self):
        from acas_pro.analytics.festival_calendar import Festival, FestivalType, MarketType
        f = Festival(
            id="f2", name="双11", name_en="Double 11",
            festival_type=FestivalType.SHOPPING, markets=[MarketType.GLOBAL],
            month=11, day=11, importance=5, duration_days=3, pre_heat_days=14,
            lunar=False
        )
        assert f.importance == 5
        assert f.duration_days == 3
        assert f.lunar == False
