#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Campaign Logic Tests
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock

from acas_pro.ui.logic.campaign_logic import (
    CampaignLogic, Campaign, CampaignStatus, CampaignType
)


class TestCampaignStatus:
    """Test campaign status enum"""
    
    def test_status_values(self):
        """Test status enum values"""
        assert CampaignStatus.DRAFT.value == "draft"
        assert CampaignStatus.RUNNING.value == "running"
        assert CampaignStatus.COMPLETED.value == "completed"


class TestCampaignType:
    """Test campaign type enum"""
    
    def test_type_values(self):
        """Test type enum values"""
        assert CampaignType.EMAIL.value == "email"
        assert CampaignType.SMS.value == "sms"
        assert CampaignType.ADS.value == "ads"


class TestCampaign:
    """Test campaign data structure"""
    
    def test_campaign_creation(self):
        """Test campaign creation"""
        campaign = Campaign(
            id="camp001",
            name="Test Campaign",
            type=CampaignType.EMAIL,
            status=CampaignStatus.DRAFT,
            subject="Test Subject",
            content="Test content",
            target_audience={"segment": "all"}
        )
        assert campaign.name == "Test Campaign"
        assert campaign.status == CampaignStatus.DRAFT
        assert campaign.sent_count == 0


class TestCampaignLogic:
    """Test campaign logic"""
    
    @pytest.fixture
    def logic(self):
        return CampaignLogic()
    
    def test_init(self, logic):
        """Test initialization"""
        assert logic._campaigns == {}
    
    def test_create_campaign(self, logic):
        """Test creating campaign"""
        campaign = logic.create_campaign(
            name="Summer Sale",
            campaign_type=CampaignType.EMAIL,
            subject="Summer Sale!",
            content="Get 50% off!",
            target_audience={"segment": "vip"}
        )
        
        assert campaign.name == "Summer Sale"
        assert campaign.type == CampaignType.EMAIL
        assert campaign.status == CampaignStatus.DRAFT
        assert len(campaign.id) == 8
    
    def test_schedule_campaign(self, logic):
        """Test scheduling campaign"""
        campaign = logic.create_campaign(
            name="Test", campaign_type=CampaignType.EMAIL,
            subject="Test", content="Test", target_audience={}
        )
        
        schedule_time = datetime.now() + timedelta(days=1)
        result = logic.schedule_campaign(campaign.id, schedule_time)
        
        assert result is True
        assert campaign.status == CampaignStatus.SCHEDULED
        assert campaign.schedule == schedule_time
    
    def test_schedule_non_draft_campaign(self, logic):
        """Test scheduling non-draft campaign fails"""
        campaign = logic.create_campaign(
            name="Test", campaign_type=CampaignType.EMAIL,
            subject="Test", content="Test", target_audience={}
        )
        campaign.status = CampaignStatus.RUNNING
        
        result = logic.schedule_campaign(campaign.id, datetime.now())
        
        assert result is False
    
    def test_launch_campaign(self, logic):
        """Test launching campaign"""
        campaign = logic.create_campaign(
            name="Test", campaign_type=CampaignType.EMAIL,
            subject="Test", content="Test", target_audience={}
        )
        
        result = logic.launch_campaign(campaign.id)
        
        assert result is True
        assert campaign.status == CampaignStatus.RUNNING
        assert campaign.started_at is not None
    
    def test_pause_campaign(self, logic):
        """Test pausing campaign"""
        campaign = logic.create_campaign(
            name="Test", campaign_type=CampaignType.EMAIL,
            subject="Test", content="Test", target_audience={}
        )
        logic.launch_campaign(campaign.id)
        
        result = logic.pause_campaign(campaign.id)
        
        assert result is True
        assert campaign.status == CampaignStatus.PAUSED
    
    def test_pause_non_running_campaign(self, logic):
        """Test pausing non-running campaign fails"""
        campaign = logic.create_campaign(
            name="Test", campaign_type=CampaignType.EMAIL,
            subject="Test", content="Test", target_audience={}
        )
        
        result = logic.pause_campaign(campaign.id)
        
        assert result is False
    
    def test_resume_campaign(self, logic):
        """Test resuming campaign"""
        campaign = logic.create_campaign(
            name="Test", campaign_type=CampaignType.EMAIL,
            subject="Test", content="Test", target_audience={}
        )
        logic.launch_campaign(campaign.id)
        logic.pause_campaign(campaign.id)
        
        result = logic.resume_campaign(campaign.id)
        
        assert result is True
        assert campaign.status == CampaignStatus.RUNNING
    
    def test_complete_campaign(self, logic):
        """Test completing campaign"""
        campaign = logic.create_campaign(
            name="Test", campaign_type=CampaignType.EMAIL,
            subject="Test", content="Test", target_audience={}
        )
        
        result = logic.complete_campaign(campaign.id)
        
        assert result is True
        assert campaign.status == CampaignStatus.COMPLETED
        assert campaign.completed_at is not None
    
    def test_update_stats(self, logic):
        """Test updating campaign stats"""
        campaign = logic.create_campaign(
            name="Test", campaign_type=CampaignType.EMAIL,
            subject="Test", content="Test", target_audience={}
        )
        
        result = logic.update_stats(campaign.id, sent=1000, opened=200, clicked=50)
        
        assert result is True
        assert campaign.sent_count == 1000
        assert campaign.open_count == 200
        assert campaign.click_count == 50
    
    def test_get_campaign(self, logic):
        """Test getting campaign"""
        campaign = logic.create_campaign(
            name="Test", campaign_type=CampaignType.EMAIL,
            subject="Test", content="Test", target_audience={}
        )
        
        fetched = logic.get_campaign(campaign.id)
        
        assert fetched == campaign
    
    def test_get_nonexistent_campaign(self, logic):
        """Test getting nonexistent campaign"""
        fetched = logic.get_campaign("nonexistent")
        
        assert fetched is None
    
    def test_list_campaigns(self, logic):
        """Test listing campaigns"""
        logic.create_campaign(
            name="Campaign 1", campaign_type=CampaignType.EMAIL,
            subject="Test", content="Test", target_audience={}
        )
        logic.create_campaign(
            name="Campaign 2", campaign_type=CampaignType.SMS,
            subject="Test", content="Test", target_audience={}
        )
        
        campaigns = logic.list_campaigns()
        
        assert len(campaigns) == 2
    
    def test_list_campaigns_by_status(self, logic):
        """Test listing campaigns by status"""
        campaign1 = logic.create_campaign(
            name="Draft", campaign_type=CampaignType.EMAIL,
            subject="Test", content="Test", target_audience={}
        )
        campaign2 = logic.create_campaign(
            name="Running", campaign_type=CampaignType.EMAIL,
            subject="Test", content="Test", target_audience={}
        )
        logic.launch_campaign(campaign2.id)
        
        draft_campaigns = logic.list_campaigns(status=CampaignStatus.DRAFT)
        
        assert len(draft_campaigns) == 1
        assert draft_campaigns[0].name == "Draft"
    
    def test_list_campaigns_by_type(self, logic):
        """Test listing campaigns by type"""
        logic.create_campaign(
            name="Email", campaign_type=CampaignType.EMAIL,
            subject="Test", content="Test", target_audience={}
        )
        logic.create_campaign(
            name="SMS", campaign_type=CampaignType.SMS,
            subject="Test", content="Test", target_audience={}
        )
        
        email_campaigns = logic.list_campaigns(campaign_type=CampaignType.EMAIL)
        
        assert len(email_campaigns) == 1
        assert email_campaigns[0].name == "Email"
    
    def test_get_performance_metrics(self, logic):
        """Test getting performance metrics"""
        campaign = logic.create_campaign(
            name="Test", campaign_type=CampaignType.EMAIL,
            subject="Test", content="Test", target_audience={}
        )
        logic.update_stats(campaign.id, sent=1000, opened=200, clicked=50)
        
        metrics = logic.get_performance_metrics(campaign.id)
        
        assert metrics["sent"] == 1000
        assert metrics["opened"] == 200
        assert metrics["clicked"] == 50
        assert metrics["open_rate"] == 20.0
        assert metrics["click_rate"] == 5.0
        assert metrics["ctr"] == 25.0
    
    def test_get_upcoming_campaigns(self, logic):
        """Test getting upcoming campaigns"""
        campaign = logic.create_campaign(
            name="Upcoming", campaign_type=CampaignType.EMAIL,
            subject="Test", content="Test", target_audience={}
        )
        schedule_time = datetime.now() + timedelta(days=3)
        logic.schedule_campaign(campaign.id, schedule_time)
        
        upcoming = logic.get_upcoming_campaigns(days=7)
        
        assert len(upcoming) == 1
        assert upcoming[0].name == "Upcoming"
    
    def test_duplicate_campaign(self, logic):
        """Test duplicating campaign"""
        original = logic.create_campaign(
            name="Original", campaign_type=CampaignType.EMAIL,
            subject="Subject", content="Content", target_audience={"seg": "vip"}
        )
        
        duplicate = logic.duplicate_campaign(original.id)
        
        assert duplicate is not None
        assert duplicate.name == "Original (Copy)"
        assert duplicate.type == original.type
        assert duplicate.subject == original.subject


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
