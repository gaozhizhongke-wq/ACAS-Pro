#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for ads/ad_manager.py dataclasses and enums."""

from unittest.mock import MagicMock, patch
import sys
import pytest

if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()


class TestAdPlatformEnum:
    def test_values(self):
        from acas_pro.ads.ad_manager import AdPlatform
        assert AdPlatform.OCEAN_ENGINE.value == "ocean_engine"
        assert AdPlatform.TENCENT_ADS.value == "tencent"

class TestCampaignStatusEnum:
    def test_values(self):
        from acas_pro.ads.ad_manager import CampaignStatus
        assert CampaignStatus.ACTIVE.value == "active"
        assert CampaignStatus.PAUSED.value == "paused"
        assert len(CampaignStatus) >= 7

class TestBudgetTypeEnum:
    def test_values(self):
        from acas_pro.ads.ad_manager import BudgetType
        assert BudgetType.DAILY.value == "daily"
        assert BudgetType.TOTAL.value == "total"

class TestAdCreative:
    def test_to_dict(self):
        from acas_pro.ads.ad_manager import AdCreative
        c = AdCreative(
            id="c1", name="test", type="video",
            material_urls=["http://img.png"], title="T",
            description="D", call_to_action="Buy", landing_page="http://x.com"
        )
        d = c.to_dict()
        assert d["id"] == "c1"
        assert d["type"] == "video"

    def test_from_dict(self):
        from acas_pro.ads.ad_manager import AdCreative
        data = {
            "id": "c2", "name": "test2", "type": "image",
            "material_urls": [], "title": "T2", "description": "D2",
            "call_to_action": "Shop", "landing_page": "http://y.com"
        }
        c = AdCreative.from_dict(data)
        assert c.id == "c2"

class TestAdSet:
    def test_to_dict(self):
        from acas_pro.ads.ad_manager import AdSet, CampaignStatus, BudgetType, AdCreative
        s = AdSet(
            id="s1", name="adset1", campaign_id="camp1",
            status=CampaignStatus.ACTIVE,
            audience_targeting={"age": [18, 35]},
            geo_targeting=["Beijing"],
            device_targeting=["mobile"],
            time_targeting={"hours": [18, 19, 20]},
            bidding_strategy="cpm", bid_amount=10.0,
            budget_type=BudgetType.DAILY, budget_amount=100.0,
            creatives=[]
        )
        d = s.to_dict()
        assert d["status"] == "active"
        assert d["budget_type"] == "daily"

class TestAdCampaign:
    def test_to_dict(self):
        from acas_pro.ads.ad_manager import AdCampaign, AdPlatform, CampaignStatus, BudgetType
        c = AdCampaign(
            id="camp1", name="Test Campaign", platform=AdPlatform.OCEAN_ENGINE,
            account_id="acc1", status=CampaignStatus.ACTIVE, objective="sales",
            budget_type=BudgetType.DAILY, budget_amount=500.0, start_date="2026-01-01",
            adsets=[]
        )
        d = c.to_dict()
        assert d["platform"] == "ocean_engine"
        assert d["status"] == "active"

    def test_from_dict(self):
        from acas_pro.ads.ad_manager import AdCampaign
        data = {
            "id": "camp2", "name": "C2", "platform": "tencent",
            "account_id": "a1", "status": "draft", "objective": "traffic",
            "budget_type": "daily", "budget_amount": 200.0, "start_date": "2026-05-01",
            "adsets": []
        }
        # Test that it parses enums correctly
        c = AdCampaign.from_dict(data)
        assert c.platform.value == "tencent"
        assert c.status.value == "draft"
