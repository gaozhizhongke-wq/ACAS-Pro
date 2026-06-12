# -*- coding: utf-8 -*-
"""Tests for analytics/festival_calendar.py"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from acas_pro.analytics.festival_calendar import (
    FestivalCalendar,
    Festival,
    FestivalType,
    MarketType,
    MarketingPlan,
)


class TestFestivalCalendar:
    """Test FestivalCalendar class"""

    @pytest.fixture
    def mock_db(self):
        """Mock DatabaseManager"""
        db = MagicMock()
        db.fetchone.return_value = None
        db.fetchall.return_value = []
        db.execute.return_value = None
        return db

    @pytest.fixture
    def calendar(self, mock_db):
        """Create FestivalCalendar with mocked DB"""
        with patch('acas_pro.analytics.festival_calendar.DatabaseManager', return_value=mock_db):
            cal = FestivalCalendar(db=mock_db)
            cal.db = mock_db
            return cal

    @pytest.fixture
    def sample_festival(self):
        """Create a sample festival"""
        return Festival(
            id='test_festival',
            name='测试节日',
            name_en='Test Festival',
            festival_type=FestivalType.TRADITIONAL,
            markets=[MarketType.DOMESTIC],
            month=1,
            day=1,
            lunar=True,
            importance=5,
            duration_days=3,
            pre_heat_days=7,
            themes=['团圆', '测试'],
            keywords=['测试', '节日'],
            visual_style='红色',
            content_tips='测试建议',
        )

    @pytest.fixture
    def sample_marketing_plan(self):
        """Create a sample marketing plan"""
        return MarketingPlan(
            id='plan_001',
            festival_id='test_festival',
            name='测试营销计划',
            start_date=datetime.now(),
            end_date=datetime.now() + timedelta(days=7),
            target_platforms=['douyin', 'xiaohongshu'],
            target_accounts=['acc1', 'acc2'],
            content_count=10,
            content_types=['video', 'image'],
            budget=1000.0,
            status='draft',
        )

    # ===== 初始化测试 =====
    def test_init(self, mock_db):
        """Test FestivalCalendar initialization"""
        with patch('acas_pro.analytics.festival_calendar.DatabaseManager', return_value=mock_db):
            cal = FestivalCalendar()
            assert cal.db is not None

    def test_init_with_db(self, mock_db):
        """Test initialization with provided DB"""
        cal = FestivalCalendar(db=mock_db)
        assert cal.db == mock_db

    def test_default_festivals(self, calendar):
        """Test DEFAULT_FESTIVALS constant"""
        assert len(FestivalCalendar.DEFAULT_FESTIVALS) > 0
        assert any(f.id == 'spring_festival' for f in FestivalCalendar.DEFAULT_FESTIVALS)

    # ===== 节日管理测试 =====
    def test_get_festival_found(self, calendar, mock_db, sample_festival):
        """Test getting an existing festival"""
        # Mock the database row
        mock_db.fetchone.return_value = {
            'id': sample_festival.id,
            'name': sample_festival.name,
            'name_en': sample_festival.name_en,
            'festival_type': sample_festival.festival_type.value,
            'markets': '["domestic"]',
            'month': sample_festival.month,
            'day': sample_festival.day,
            'lunar': 1,
            'floating': 0,
            'floating_rule': None,
            'importance': sample_festival.importance,
            'duration_days': sample_festival.duration_days,
            'pre_heat_days': sample_festival.pre_heat_days,
            'themes': '["团圆", "测试"]',
            'keywords': '["测试", "节日"]',
            'visual_style': sample_festival.visual_style,
            'content_tips': sample_festival.content_tips,
            'is_active': 1,
            'created_at': datetime.now().isoformat(),
        }
        festival = calendar.get_festival(sample_festival.id)
        assert festival is not None
        assert festival.id == sample_festival.id

    def test_get_festival_not_found(self, calendar, mock_db):
        """Test getting non-existent festival"""
        mock_db.fetchone.return_value = None
        festival = calendar.get_festival('nonexistent')
        assert festival is None

    def test_list_festivals(self, calendar, mock_db):
        """Test listing festivals"""
        mock_db.fetchall.return_value = []
        festivals = calendar.list_festivals()
        assert isinstance(festivals, list)

    def test_list_festivals_by_type(self, calendar, mock_db):
        """Test listing festivals by type"""
        mock_db.fetchall.return_value = []
        festivals = calendar.list_festivals(festival_type=FestivalType.TRADITIONAL)
        assert isinstance(festivals, list)

    def test_get_upcoming_festivals(self, calendar, mock_db):
        """Test getting upcoming festivals"""
        mock_db.fetchall.return_value = []
        upcoming = calendar.get_upcoming_festivals(days=30)
        assert isinstance(upcoming, list)

    # ===== 营销计划测试 =====
    def test_create_marketing_plan(self, calendar, mock_db, sample_festival):
        """Test creating a marketing plan"""
        mock_db.fetchone.return_value = {'id': sample_festival.id}
        
        start = datetime.now()
        end = start + timedelta(days=7)
        
        plan = calendar.create_marketing_plan(
            festival_id=sample_festival.id,
            name='测试计划',
            start_date=start,
            end_date=end,
            target_platforms=['douyin'],
            target_accounts=['acc1'],
            content_count=5,
            content_types=['video'],
            budget=500.0,
        )
        
        assert plan is not None
        assert plan.festival_id == sample_festival.id
        assert plan.name == '测试计划'

    def test_get_marketing_plans(self, calendar, mock_db):
        """Test getting marketing plans"""
        mock_db.fetchall.return_value = []
        plans = calendar.get_marketing_plans()
        assert isinstance(plans, list)

    def test_get_marketing_plans_by_status(self, calendar, mock_db):
        """Test getting marketing plans by status"""
        mock_db.fetchall.return_value = []
        plans = calendar.get_marketing_plans(status='draft')
        assert isinstance(plans, list)

    # ===== 内容建议测试 =====
    def test_generate_content_suggestions(self, calendar, mock_db, sample_festival):
        """Test generating content suggestions"""
        mock_db.fetchone.return_value = {
            'id': sample_festival.id,
            'name': sample_festival.name,
            'name_en': sample_festival.name_en,
            'festival_type': sample_festival.festival_type.value,
            'markets': '["domestic"]',
            'month': sample_festival.month,
            'day': sample_festival.day,
            'lunar': 1,
            'floating': 0,
            'floating_rule': None,
            'importance': sample_festival.importance,
            'duration_days': sample_festival.duration_days,
            'pre_heat_days': sample_festival.pre_heat_days,
            'themes': '["团圆", "测试"]',
            'keywords': '["测试", "节日"]',
            'visual_style': sample_festival.visual_style,
            'content_tips': sample_festival.content_tips,
            'is_active': 1,
            'created_at': datetime.now().isoformat(),
        }
        
        suggestions = calendar.generate_content_suggestions(sample_festival.id)
        assert isinstance(suggestions, dict)
        assert 'festival_name' in suggestions
        assert 'themes' in suggestions
        assert 'keywords' in suggestions

    def test_generate_content_suggestions_not_found(self, calendar, mock_db):
        """Test generating suggestions for non-existent festival"""
        mock_db.fetchone.return_value = None
        suggestions = calendar.generate_content_suggestions('nonexistent')
        assert suggestions == {}


class TestFestival:
    """Test Festival dataclass"""

    def test_festival_creation(self):
        """Test Festival creation"""
        festival = Festival(
            id='test_001',
            name='测试节日',
            name_en='Test Festival',
            festival_type=FestivalType.TRADITIONAL,
            markets=[MarketType.DOMESTIC],
            month=1,
            day=1,
        )
        assert festival.id == 'test_001'
        assert festival.name == '测试节日'
        assert festival.themes == []  # default
        assert festival.keywords == []  # default

    def test_festival_post_init(self):
        """Test Festival __post_init__"""
        festival = Festival(
            id='test_002',
            name='测试',
            name_en='Test',
            festival_type=FestivalType.WESTERN,
            markets=[MarketType.GLOBAL],
            month=12,
            day=25,
        )
        assert festival.themes == []
        assert festival.keywords == []
        assert festival.created_at is not None


class TestMarketingPlan:
    """Test MarketingPlan dataclass"""

    def test_marketing_plan_creation(self):
        """Test MarketingPlan creation"""
        start = datetime.now()
        end = start + timedelta(days=7)
        
        plan = MarketingPlan(
            id='plan_001',
            festival_id='festival_001',
            name='测试计划',
            start_date=start,
            end_date=end,
            target_platforms=['douyin'],
            target_accounts=['acc1'],
            content_count=10,
            content_types=['video', 'image'],
            budget=1000.0,
        )
        assert plan.id == 'plan_001'
        assert plan.status == 'draft'  # default
        assert plan.created_at is not None

    def test_marketing_plan_post_init(self):
        """Test MarketingPlan __post_init__"""
        start = datetime.now()
        end = start + timedelta(days=3)
        
        plan = MarketingPlan(
            id='plan_002',
            festival_id='festival_002',
            name='测试',
            start_date=start,
            end_date=end,
            target_platforms=[],
            target_accounts=[],
            content_count=5,
            content_types=[],
            budget=500.0,
        )
        assert plan.created_at is not None


class TestEnums:
    """Test enums"""

    def test_festival_type_values(self):
        """Test FestivalType enum values"""
        assert FestivalType.TRADITIONAL.value == 'traditional'
        assert FestivalType.WESTERN.value == 'western'
        assert FestivalType.SHOPPING.value == 'shopping'
        assert FestivalType.CULTURAL.value == 'cultural'
        assert FestivalType.RELIGIOUS.value == 'religious'
        assert FestivalType.CUSTOM.value == 'custom'

    def test_market_type_values(self):
        """Test MarketType enum values"""
        assert MarketType.DOMESTIC.value == 'domestic'
        assert MarketType.OVERSEAS.value == 'overseas'
        assert MarketType.NORTHWEST.value == 'northwest'
        assert MarketType.MIDDLE_EAST.value == 'middle_east'
        assert MarketType.SOUTHEAST_ASIA.value == 'southeast_asia'
        assert MarketType.GLOBAL.value == 'global'
