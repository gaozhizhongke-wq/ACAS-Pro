#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for blockchain/settlement_engine.py"""

from datetime import datetime
from acas_pro.blockchain.settlement_engine import (
    SettlementType, SettlementParty, SettlementRecord,
    SettlementEngine
)


class TestSettlementParty:
    def test_calculate_share_percentage(self):
        party = SettlementParty(
            party_id="p1", party_type="creator", name="Test",
            share_percentage=50
        )
        assert party.calculate_share(1000) == 500.0

    def test_calculate_share_fixed(self):
        party = SettlementParty(
            party_id="p1", party_type="creator", name="Test",
            fixed_amount=200
        )
        assert party.calculate_share(1000) == 200.0


class TestSettlementRecord:
    def test_calculate_distribution(self):
        record = SettlementRecord(
            id="stl_1",
            settlement_type=SettlementType.REVENUE_SHARE,
            source_id="order_1",
            source_type="order",
            total_amount=1000,
            parties=[
                SettlementParty("p1", "platform", "Platform", share_percentage=30),
                SettlementParty("p2", "creator", "Creator", share_percentage=70)
            ]
        )
        dist = record.calculate_distribution()
        assert dist["p1"] == 300.0
        assert dist["p2"] == 700.0

    def test_calculate_distribution_with_fixed(self):
        record = SettlementRecord(
            id="stl_1",
            settlement_type=SettlementType.REVENUE_SHARE,
            source_id="order_1",
            source_type="order",
            total_amount=1000,
            parties=[
                SettlementParty("p1", "platform", "Platform", fixed_amount=100),
                SettlementParty("p2", "creator", "Creator", share_percentage=100)
            ]
        )
        dist = record.calculate_distribution()
        assert dist["p1"] == 100.0
        assert dist["p2"] == 900.0

    def test_generate_hash(self):
        record = SettlementRecord(
            id="stl_1",
            settlement_type=SettlementType.REVENUE_SHARE,
            source_id="order_1",
            source_type="order",
            total_amount=1000,
            parties=[],
            distribution={"p1": 500}
        )
        hash1 = record.generate_hash()
        assert isinstance(hash1, str)
        assert len(hash1) == 64


class TestSettlementEngine:
    def setup_method(self):
        self.engine = SettlementEngine()

    def test_init(self):
        assert self.engine is not None
        assert self.engine.db is not None

    def test_create_settlement(self):
        record = self.engine.create_settlement(
            settlement_type=SettlementType.REVENUE_SHARE,
            source_id="order_123",
            total_amount=1000,
            parties=[
                SettlementParty("p1", "platform", "Platform", share_percentage=30),
                SettlementParty("p2", "creator", "Creator", share_percentage=70)
            ],
            description="Test settlement"
        )
        assert record is not None
        assert record.id.startswith("stl_")
        assert record.total_amount == 1000
        assert len(record.distribution) == 2

    def test_create_from_template_content(self):
        record = self.engine.create_from_template(
            template_name="content_revenue",
            source_id="content_1",
            total_amount=1000,
            party_configs=[
                {"party_id": "plat", "name": "Platform", "wallet": "0x1"},
                {"party_id": "creator", "name": "Creator", "wallet": "0x2"},
                {"party_id": "aff", "name": "Affiliate", "wallet": "0x3"}
            ]
        )
        assert record is not None
        assert len(record.parties) == 3

    def test_create_from_template_ad(self):
        record = self.engine.create_from_template(
            template_name="ad_revenue",
            source_id="ad_1",
            total_amount=5000,
            party_configs=[
                {"party_id": "plat", "name": "Platform"},
                {"party_id": "adv", "name": "Advertiser"},
                {"party_id": "ag", "name": "Agency"}
            ]
        )
        assert record is not None

    def test_create_from_template_ecommerce(self):
        record = self.engine.create_from_template(
            template_name="ecommerce_sale",
            source_id="sale_1",
            total_amount=2000,
            party_configs=[
                {"party_id": "plat", "name": "Platform"},
                {"party_id": "seller", "name": "Seller"},
                {"party_id": "log", "name": "Logistics"}
            ]
        )
        assert record is not None

    def test_create_from_template_live(self):
        record = self.engine.create_from_template(
            template_name="live_streaming",
            source_id="live_1",
            total_amount=3000,
            party_configs=[
                {"party_id": "plat", "name": "Platform"},
                {"party_id": "streamer", "name": "Streamer"},
                {"party_id": "guild", "name": "Guild"}
            ]
        )
        assert record is not None

    def test_create_from_template_invalid(self):
        record = self.engine.create_from_template(
            template_name="nonexistent",
            source_id="test",
            total_amount=100,
            party_configs=[]
        )
        assert record is None

    def test_get_settlement(self):
        created = self.engine.create_settlement(
            settlement_type=SettlementType.COMMISSION,
            source_id="src_1",
            total_amount=500,
            parties=[SettlementParty("p1", "platform", "P", share_percentage=100)]
        )
        fetched = self.engine.get_settlement(created.id)
        assert fetched is not None
        assert fetched.id == created.id

    def test_get_settlement_not_found(self):
        result = self.engine.get_settlement("nonexistent")
        assert result is None

    def test_get_settlements_by_source(self):
        self.engine.create_settlement(
            settlement_type=SettlementType.BONUS,
            source_id="shared_src",
            total_amount=100,
            parties=[SettlementParty("p1", "platform", "P", share_percentage=100)]
        )
        results = self.engine.get_settlements_by_source("shared_src")
        assert isinstance(results, list)
        assert len(results) >= 1

    def test_execute_settlement(self):
        created = self.engine.create_settlement(
            settlement_type=SettlementType.COST_SPLIT,
            source_id="cs_1",
            total_amount=200,
            parties=[SettlementParty("p1", "platform", "P", share_percentage=100)]
        )
        result = self.engine.execute_settlement(created.id)
        assert result is not None

    def test_execute_settlement_not_found(self):
        result = self.engine.execute_settlement("nonexistent")
        # Returns dict with success=False
        if isinstance(result, dict):
            assert result.get("success") is False or "error" in result
        else:
            assert result is False or result is None

    def test_verify_settlement(self):
        created = self.engine.create_settlement(
            settlement_type=SettlementType.REVENUE_SHARE,
            source_id="bc_1",
            total_amount=1000,
            parties=[SettlementParty("p1", "platform", "P", share_percentage=100)]
        )
        result = self.engine.verify_settlement(created.id)
        assert result is not None

    def test_get_settlement_statistics(self):
        from datetime import timedelta
        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        result = self.engine.get_settlement_statistics(start, end)
        assert isinstance(result, dict)

    def test_get_templates(self):
        templates = self.engine.get_templates()
        assert isinstance(templates, (list, dict))
        if isinstance(templates, list):
            assert len(templates) > 0
        elif isinstance(templates, dict):
            assert len(templates) > 0

    def test_settlement_templates(self):
        assert "content_revenue" in SettlementEngine.SETTLEMENT_TEMPLATES
        assert "ad_revenue" in SettlementEngine.SETTLEMENT_TEMPLATES
        assert "ecommerce_sale" in SettlementEngine.SETTLEMENT_TEMPLATES
        assert "live_streaming" in SettlementEngine.SETTLEMENT_TEMPLATES
