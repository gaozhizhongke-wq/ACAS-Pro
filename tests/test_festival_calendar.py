#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Festival Calendar Tests
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from acas_pro.analytics.festival_calendar import (
    FestivalCalendar, Festival, MarketingPlan,
    FestivalType, MarketType
)


class TestFestivalType:
    """Festival type enum tests"""
    
    def test_festival_type_values(self):
        """Test festival type values"""
        assert FestivalType.TRADITIONAL.value == "traditional"
        assert FestivalType.WESTERN.value == "western"
        assert FestivalType.SHOPPING.value == "shopping"
        assert FestivalType.CULTURAL.value == "cultural"
        assert FestivalType.RELIGIOUS.value == "religious"
        assert FestivalType.CUSTOM.value == "custom"


class TestMarketType:
    """Market type enum tests"""
    
    def test_market_type_values(self):
        """Test market type values"""
        assert MarketType.DOMESTIC.value == "domestic"
        assert MarketType.OVERSEAS.value == "overseas"
        assert MarketType.NORTHWEST.value == "northwest"
        assert MarketType.MIDDLE_EAST.value == "middle_east"
        assert MarketType.SOUTHEAST_ASIA.value == "southeast_asia"
        assert MarketType.GLOBAL.value == "global"


class TestFestival:
    """Festival dataclass tests"""
    
    def test_festival_creation(self):
        """Test festival creation"""
        festival = Festival(
            id="test_festival",
            name="测试节日",
            name_en="Test Festival",
            festival_type=FestivalType.TRADITIONAL,
            markets=[MarketType.DOMESTIC],
            month=1,
            day=1
        )
        
        assert festival.id == "test_festival"
        assert festival.name == "测试节日"
        assert festival.themes == []  # default
        assert festival.keywords == []  # default
    
    def test_festival_post_init(self):
        """Test festival post init defaults"""
        festival = Festival(
            id="test",
            name="Test",
            name_en="Test",
            festival_type=FestivalType.WESTERN,
            markets=[MarketType.GLOBAL],
            month=12,
            day=25
        )
        
        assert festival.themes == []
        assert festival.keywords == []
        assert festival.created_at is not None


class TestMarketingPlan:
    """Marketing plan tests"""
    
    def test_plan_creation(self):
        """Test plan creation"""
        plan = MarketingPlan(
            id="plan_001",
            festival_id="festival_001",
            name="春节营销计划",
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7),
            target_platforms=["douyin", "xhs"],
            target_accounts=["account1"],
            content_count=10,
            content_types=["video", "image"],
            budget=10000.0
        )
        
        assert plan.id == "plan_001"
        assert plan.status == "draft"  # default
        assert plan.budget == 10000.0


class TestFestivalCalendar:
    """Festival calendar tests"""
    
    @pytest.fixture
    def mock_db(self):
        mock = Mock()
        mock.execute = Mock()
        mock.fetchone = Mock(return_value=None)
        mock.fetchall = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def calendar(self, mock_db):
        with patch('acas_pro.analytics.festival_calendar.DatabaseManager', return_value=mock_db):
            return FestivalCalendar(db=mock_db)
    
    def test_init(self, calendar, mock_db):
        """Test initialization"""
        assert calendar.db == mock_db
        mock_db.execute.assert_called()
    
    def test_default_festivals_exist(self, calendar):
        """Test default festivals are loaded"""
        assert len(calendar.DEFAULT_FESTIVALS) > 0
        
        # Check for major festivals
        festival_ids = [f.id for f in calendar.DEFAULT_FESTIVALS]
        assert "spring_festival" in festival_ids
        assert "christmas" in festival_ids
        assert "singles_day" in festival_ids
    
    def test_get_festival_not_found(self, calendar, mock_db):
        """Test get festival not found"""
        mock_db.fetchone.return_value = None
        
        result = calendar.get_festival("nonexistent")
        
        assert result is None
    
    def test_list_festivals_empty(self, calendar, mock_db):
        """Test list festivals empty"""
        mock_db.fetchall.return_value = []
        
        festivals = calendar.list_festivals()
        
        assert festivals == []
    
    def test_list_festivals_by_type(self, calendar, mock_db):
        """Test list festivals by type"""
        mock_db.fetchall.return_value = []
        
        festivals = calendar.list_festivals(
            festival_type=FestivalType.TRADITIONAL
        )
        
        assert isinstance(festivals, list)
    
    def test_list_festivals_by_market(self, calendar, mock_db):
        """Test list festivals by market"""
        # Need to return some data for market filtering
        mock_db.fetchall.return_value = [
            {
                'id': 'test',
                'name': 'Test',
                'name_en': 'Test',
                'festival_type': 'traditional',
                'markets': '["domestic"]',
                'month': 1,
                'day': 1,
                'lunar': 0,
                'floating': 0,
                'floating_rule': None,
                'importance': 3,
                'duration_days': 1,
                'pre_heat_days': 7,
                'themes': '[]',
                'keywords': '[]',
                'visual_style': None,
                'content_tips': None,
                'is_active': 1,
                'created_at': datetime.now().isoformat()
            }
        ]
        
        festivals = calendar.list_festivals(market=MarketType.DOMESTIC)
        
        assert len(festivals) == 1
        assert MarketType.DOMESTIC in festivals[0].markets
    
    def test_get_upcoming_festivals(self, calendar, mock_db):
        """Test get upcoming festivals"""
        # Return festivals with future dates
        mock_db.fetchall.return_value = [
            {
                'id': 'christmas',
                'name': '圣诞节',
                'name_en': 'Christmas',
                'festival_type': 'western',
                'markets': '["global"]',
                'month': 12,
                'day': 25,
                'lunar': 0,
                'floating': 0,
                'floating_rule': None,
                'importance': 4,
                'duration_days': 3,
                'pre_heat_days': 14,
                'themes': '["礼物", "家庭"]',
                'keywords': '["圣诞", "礼物"]',
                'visual_style': '红绿配色',
                'content_tips': None,
                'is_active': 1,
                'created_at': datetime.now().isoformat()
            }
        ]
        
        upcoming = calendar.get_upcoming_festivals(days=365)
        
        assert isinstance(upcoming, list)
    
    def test_create_marketing_plan(self, calendar, mock_db):
        """Test create marketing plan"""
        start = datetime.now()
        end = start + timedelta(days=7)
        
        plan = calendar.create_marketing_plan(
            festival_id="spring_festival",
            name="春节营销",
            start_date=start,
            end_date=end,
            target_platforms=["douyin"],
            target_accounts=["account1"],
            content_count=10,
            budget=5000.0
        )
        
        assert plan.festival_id == "spring_festival"
        assert plan.name == "春节营销"
        assert plan.budget == 5000.0
        mock_db.execute.assert_called()
    
    def test_get_marketing_plans_empty(self, calendar, mock_db):
        """Test get marketing plans empty"""
        mock_db.fetchall.return_value = []
        
        plans = calendar.get_marketing_plans()
        
        assert plans == []
    
    def test_get_marketing_plans_by_status(self, calendar, mock_db):
        """Test get marketing plans by status"""
        mock_db.fetchall.return_value = []
        
        plans = calendar.get_marketing_plans(status="active")
        
        assert isinstance(plans, list)
    
    def test_generate_content_suggestions_not_found(self, calendar, mock_db):
        """Test generate content suggestions for non-existent festival"""
        mock_db.fetchone.return_value = None
        
        suggestions = calendar.generate_content_suggestions("nonexistent")
        
        assert suggestions == {}
    
    def test_generate_content_suggestions(self, calendar, mock_db):
        """Test generate content suggestions"""
        mock_db.fetchone.return_value = {
            'id': 'spring_festival',
            'name': '春节',
            'name_en': 'Spring Festival',
            'festival_type': 'traditional',
            'markets': '["domestic", "global"]',
            'month': 1,
            'day': 1,
            'lunar': 1,
            'floating': 0,
            'floating_rule': None,
            'importance': 5,
            'duration_days': 7,
            'pre_heat_days': 15,
            'themes': '["团圆", "年货"]',
            'keywords': '["过年", "春节"]',
            'visual_style': '红色、金色',
            'content_tips': '强调家庭团聚',
            'is_active': 1,
            'created_at': datetime.now().isoformat()
        }
        
        suggestions = calendar.generate_content_suggestions("spring_festival")
        
        assert "festival_name" in suggestions
        assert "themes" in suggestions
        assert "suggested_hashtags" in suggestions
        assert suggestions["festival_name"] == "春节"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
