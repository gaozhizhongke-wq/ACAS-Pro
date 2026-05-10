#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Settlement Engine Tests
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from acas_pro.blockchain.settlement_engine import (
    SettlementEngine, SettlementRecord, SettlementParty,
    SettlementStatus, SettlementType
)


class TestSettlementStatus:
    """Settlement status enum tests"""
    
    def test_status_values(self):
        """Test status values"""
        assert SettlementStatus.PENDING.value == "pending"
        assert SettlementStatus.PROCESSING.value == "processing"
        assert SettlementStatus.COMPLETED.value == "completed"
        assert SettlementStatus.FAILED.value == "failed"
        assert SettlementStatus.DISPUTED.value == "disputed"


class TestSettlementType:
    """Settlement type enum tests"""
    
    def test_type_values(self):
        """Test type values"""
        assert SettlementType.REVENUE_SHARE.value == "revenue_share"
        assert SettlementType.COST_SPLIT.value == "cost_split"
        assert SettlementType.COMMISSION.value == "commission"
        assert SettlementType.BONUS.value == "bonus"
        assert SettlementType.REFUND.value == "refund"


class TestSettlementParty:
    """Settlement party tests"""
    
    def test_party_creation(self):
        """Test party creation"""
        party = SettlementParty(
            party_id="user_001",
            party_type="creator",
            name="张三",
            share_percentage=50.0
        )
        
        assert party.party_id == "user_001"
        assert party.share_percentage == 50.0
    
    def test_calculate_share_percentage(self):
        """Test calculate share by percentage"""
        party = SettlementParty(
            party_id="user_001",
            party_type="creator",
            name="张三",
            share_percentage=30.0
        )
        
        amount = party.calculate_share(1000.0)
        assert amount == 300.0
    
    def test_calculate_share_fixed(self):
        """Test calculate share by fixed amount"""
        party = SettlementParty(
            party_id="user_001",
            party_type="creator",
            name="张三",
            fixed_amount=200.0
        )
        
        amount = party.calculate_share(1000.0)
        assert amount == 200.0


class TestSettlementRecord:
    """Settlement record tests"""
    
    def test_record_creation(self):
        """Test record creation"""
        record = SettlementRecord(
            id="stl_001",
            settlement_type=SettlementType.REVENUE_SHARE,
            source_id="order_001",
            source_type="order",
            total_amount=1000.0
        )
        
        assert record.id == "stl_001"
        assert record.currency == "CNY"  # default
        assert record.status == SettlementStatus.PENDING  # default
    
    def test_calculate_distribution(self):
        """Test calculate distribution"""
        record = SettlementRecord(
            id="stl_001",
            settlement_type=SettlementType.REVENUE_SHARE,
            source_id="order_001",
            source_type="order",
            total_amount=1000.0,
            parties=[
                SettlementParty(party_id="p1", party_type="platform", name="平台", share_percentage=30),
                SettlementParty(party_id="p2", party_type="creator", name="创作者", share_percentage=70),
            ]
        )
        
        distribution = record.calculate_distribution()
        
        assert distribution["p1"] == 300.0
        assert distribution["p2"] == 700.0
    
    def test_generate_hash(self):
        """Test generate hash"""
        record = SettlementRecord(
            id="stl_001",
            settlement_type=SettlementType.REVENUE_SHARE,
            source_id="order_001",
            source_type="order",
            total_amount=1000.0
        )
        
        hash1 = record.generate_hash()
        
        assert len(hash1) == 64  # SHA256 hex
        assert hash1 == record.generate_hash()  # deterministic


class TestSettlementEngine:
    """Settlement engine tests"""
    
    @pytest.fixture
    def mock_db(self):
        mock = Mock()
        mock.execute = Mock()
        mock.fetch_one = Mock(return_value=None)
        mock.fetch_all = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def engine(self, mock_db):
        with patch('acas_pro.blockchain.settlement_engine.DatabaseManager', return_value=mock_db):
            return SettlementEngine()
    
    def test_init(self, engine, mock_db):
        """Test initialization"""
        mock_db.execute.assert_called()
    
    def test_templates_exist(self, engine):
        """Test templates exist"""
        assert 'content_revenue' in engine.SETTLEMENT_TEMPLATES
        assert 'ad_revenue' in engine.SETTLEMENT_TEMPLATES
        assert 'ecommerce_sale' in engine.SETTLEMENT_TEMPLATES
        assert 'live_streaming' in engine.SETTLEMENT_TEMPLATES
    
    def test_create_settlement(self, engine, mock_db):
        """Test create settlement"""
        record = engine.create_settlement(
            settlement_type=SettlementType.REVENUE_SHARE,
            source_id="order_001",
            total_amount=1000.0,
            parties=[
                SettlementParty(party_id="p1", party_type="platform", name="平台", share_percentage=30),
                SettlementParty(party_id="p2", party_type="creator", name="创作者", share_percentage=70),
            ]
        )
        
        assert record.settlement_type == SettlementType.REVENUE_SHARE
        assert record.total_amount == 1000.0
        assert len(record.parties) == 2
        mock_db.execute.assert_called()
    
    def test_create_from_template(self, engine, mock_db):
        """Test create from template"""
        record = engine.create_from_template(
            template_name="content_revenue",
            source_id="content_001",
            total_amount=1000.0,
            party_configs=[
                {'party_id': 'platform', 'name': '平台', 'wallet': '0x123'},
                {'party_id': 'creator', 'name': '创作者', 'wallet': '0x456'},
                {'party_id': 'affiliate', 'name': '推广者', 'wallet': '0x789'},
            ]
        )
        
        assert record is not None
        assert record.total_amount == 1000.0
        assert len(record.parties) == 3
    
    def test_create_from_template_invalid(self, engine):
        """Test create from invalid template"""
        record = engine.create_from_template(
            template_name="invalid_template",
            source_id="order_001",
            total_amount=1000.0,
            party_configs=[]
        )
        
        assert record is None
    
    def test_get_settlement_not_found(self, engine, mock_db):
        """Test get settlement not found"""
        mock_db.fetch_one.return_value = None
        
        result = engine.get_settlement("nonexistent")
        
        assert result is None
    
    def test_get_settlements_by_source_empty(self, engine, mock_db):
        """Test get settlements by source empty"""
        mock_db.fetch_all.return_value = []
        
        settlements = engine.get_settlements_by_source("order_001")
        
        assert settlements == []
    
    def test_execute_settlement_not_found(self, engine, mock_db):
        """Test execute settlement not found"""
        mock_db.fetch_one.return_value = None
        
        result = engine.execute_settlement("nonexistent")
        
        assert result['success'] is False
    
    def test_get_settlement_statistics_empty(self, engine, mock_db):
        """Test get settlement statistics empty"""
        mock_db.fetch_all.return_value = []
        
        stats = engine.get_settlement_statistics("2024-01-01", "2024-01-31")
        
        assert stats['total_settlements'] == 0
        assert stats['total_amount'] == 0.0
        assert stats['completion_rate'] == 0
    
    def test_verify_settlement_not_found(self, engine, mock_db):
        """Test verify settlement not found"""
        mock_db.fetch_one.return_value = None
        
        result = engine.verify_settlement("nonexistent")
        
        assert result['verified'] is False
    
    def test_get_templates(self, engine):
        """Test get templates"""
        templates = engine.get_templates()
        
        assert 'content_revenue' in templates
        assert 'name' in templates['content_revenue']
        assert 'parties' in templates['content_revenue']


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
