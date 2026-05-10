#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Marketing Campaign Business Logic
Extracted from campaign pages for testability
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from enum import Enum


class CampaignStatus(Enum):
    """Campaign status"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class CampaignType(Enum):
    """Campaign type"""
    EMAIL = "email"
    SMS = "sms"
    SOCIAL = "social"
    ADS = "ads"
    PUSH = "push"


@dataclass
class Campaign:
    """Campaign data"""
    id: str
    name: str
    type: CampaignType
    status: CampaignStatus
    subject: str
    content: str
    target_audience: Dict
    schedule: Optional[datetime] = None
    sent_count: int = 0
    open_count: int = 0
    click_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class CampaignLogic:
    """Campaign management business logic"""
    
    def __init__(self):
        self._campaigns: Dict[str, Campaign] = {}
    
    def create_campaign(self, name: str, campaign_type: CampaignType,
                       subject: str, content: str,
                       target_audience: Dict) -> Campaign:
        """Create new campaign"""
        import uuid
        
        campaign = Campaign(
            id=str(uuid.uuid4())[:8],
            name=name,
            type=campaign_type,
            status=CampaignStatus.DRAFT,
            subject=subject,
            content=content,
            target_audience=target_audience,
            created_at=datetime.now()
        )
        
        self._campaigns[campaign.id] = campaign
        return campaign
    
    def schedule_campaign(self, campaign_id: str, schedule_time: datetime) -> bool:
        """Schedule campaign"""
        campaign = self._campaigns.get(campaign_id)
        if not campaign or campaign.status != CampaignStatus.DRAFT:
            return False
        
        campaign.schedule = schedule_time
        campaign.status = CampaignStatus.SCHEDULED
        return True
    
    def launch_campaign(self, campaign_id: str) -> bool:
        """Launch campaign immediately"""
        campaign = self._campaigns.get(campaign_id)
        if not campaign or campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]:
            return False
        
        campaign.status = CampaignStatus.RUNNING
        campaign.started_at = datetime.now()
        return True
    
    def pause_campaign(self, campaign_id: str) -> bool:
        """Pause running campaign"""
        campaign = self._campaigns.get(campaign_id)
        if not campaign or campaign.status != CampaignStatus.RUNNING:
            return False
        
        campaign.status = CampaignStatus.PAUSED
        return True
    
    def resume_campaign(self, campaign_id: str) -> bool:
        """Resume paused campaign"""
        campaign = self._campaigns.get(campaign_id)
        if not campaign or campaign.status != CampaignStatus.PAUSED:
            return False
        
        campaign.status = CampaignStatus.RUNNING
        return True
    
    def complete_campaign(self, campaign_id: str) -> bool:
        """Mark campaign as completed"""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return False
        
        campaign.status = CampaignStatus.COMPLETED
        campaign.completed_at = datetime.now()
        return True
    
    def update_stats(self, campaign_id: str, sent: int = 0, 
                    opened: int = 0, clicked: int = 0) -> bool:
        """Update campaign statistics"""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return False
        
        campaign.sent_count += sent
        campaign.open_count += opened
        campaign.click_count += clicked
        return True
    
    def get_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Get campaign by ID"""
        return self._campaigns.get(campaign_id)
    
    def list_campaigns(self, status: Optional[CampaignStatus] = None,
                      campaign_type: Optional[CampaignType] = None) -> List[Campaign]:
        """List campaigns with filters"""
        campaigns = list(self._campaigns.values())
        
        if status:
            campaigns = [c for c in campaigns if c.status == status]
        
        if campaign_type:
            campaigns = [c for c in campaigns if c.type == campaign_type]
        
        # Sort by created_at desc
        campaigns.sort(key=lambda c: c.created_at, reverse=True)
        return campaigns
    
    def get_performance_metrics(self, campaign_id: str) -> Dict:
        """Get campaign performance metrics"""
        campaign = self._campaigns.get(campaign_id)
        if not campaign:
            return {}
        
        sent = campaign.sent_count
        
        return {
            "sent": sent,
            "opened": campaign.open_count,
            "clicked": campaign.click_count,
            "open_rate": (campaign.open_count / sent * 100) if sent > 0 else 0,
            "click_rate": (campaign.click_count / sent * 100) if sent > 0 else 0,
            "ctr": (campaign.click_count / campaign.open_count * 100) if campaign.open_count > 0 else 0
        }
    
    def get_upcoming_campaigns(self, days: int = 7) -> List[Campaign]:
        """Get campaigns scheduled in next X days"""
        cutoff = datetime.now() + timedelta(days=days)
        
        return [
            c for c in self._campaigns.values()
            if c.status == CampaignStatus.SCHEDULED
            and c.schedule
            and c.schedule <= cutoff
        ]
    
    def duplicate_campaign(self, campaign_id: str) -> Optional[Campaign]:
        """Duplicate existing campaign"""
        original = self._campaigns.get(campaign_id)
        if not original:
            return None
        
        return self.create_campaign(
            name=f"{original.name} (Copy)",
            campaign_type=original.type,
            subject=original.subject,
            content=original.content,
            target_audience=original.target_audience.copy()
        )
