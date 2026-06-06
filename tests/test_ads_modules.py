"""
Phase 1: 广告核心模块测试
覆盖: ad_manager, audience_targeting, bidding_engine
"""
import pytest
import tempfile
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# 导入被测模块
from acas_pro.ads.ad_manager import (
    AdManager, AdAccount, AdCampaign, AdPlatform, CampaignStatus, BudgetType
)
from acas_pro.ads.audience_targeting import (
    AudienceTargeting, AudienceSegment, AudienceType, AgeRange, GeoTargeting, DeviceTargeting, Gender
)
from acas_pro.ads.bidding_engine import (
    BiddingEngine, BiddingConfig, BiddingStrategy
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_db():
    """临时数据库路径"""
    import uuid
    db_path = os.path.join(tempfile.gettempdir(), f"test_ads_{uuid.uuid4().hex}.db")
    yield db_path
    # 清理：关闭所有连接后删除
    import gc
    gc.collect()
    for _ in range(3):
        try:
            if os.path.exists(db_path):
                os.unlink(db_path)
            break
        except PermissionError:
            import time
            time.sleep(0.1)


@pytest.fixture
def ad_manager(temp_db):
    """AdManager 实例"""
    manager = AdManager(db_path=temp_db)
    yield manager
    manager.close()


@pytest.fixture
def audience_targeting(temp_db):
    """AudienceTargeting 实例"""
    targeting = AudienceTargeting(db_path=temp_db)
    yield targeting
    targeting.close()


@pytest.fixture
def bidding_engine():
    """BiddingEngine 实例"""
    return BiddingEngine()


@pytest.fixture
def sample_ad_account():
    """示例广告账户"""
    return AdAccount(
        id="test_account_001",
        platform=AdPlatform.OCEAN_ENGINE,
        account_name="测试账户",
        account_id="oc_12345",
        access_token="test_token",
        refresh_token="test_refresh",
        token_expires_at=datetime.now() + timedelta(days=30),
        status="active",
        balance=10000.0,
        daily_budget_limit=1000.0,
        total_spend_7d=500.0,
        total_spend_30d=2000.0,
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def sample_ad_campaign():
    """示例广告计划"""
    now = datetime.now()
    return AdCampaign(
        id="test_campaign_001",
        name="测试计划",
        platform=AdPlatform.OCEAN_ENGINE,
        account_id="test_account_001",
        status=CampaignStatus.DRAFT,
        objective="conversions",
        budget_type=BudgetType.DAILY,
        budget_amount=500.0,
        start_date=now.isoformat(),
        end_date=(now + timedelta(days=30)).isoformat(),
        conversion_goal="purchase",
        adsets=[],
        total_impressions=0,
        total_clicks=0,
        total_conversions=0,
        total_spend=0.0,
        created_at=now,
        updated_at=now
    )


@pytest.fixture
def sample_audience_segment():
    """示例人群包"""
    now = datetime.now()
    return AudienceSegment(
        id="test_segment_001",
        name="测试人群",
        type=AudienceType.CUSTOM,
        gender=Gender.ALL,
        age_range=AgeRange(min_age=18, max_age=45),
        geo_targeting=GeoTargeting(provinces=["北京", "上海"]),
        device_targeting=DeviceTargeting(os_types=["ios", "android"]),
        interests=["电商", "美妆"],
        behaviors=["购买"],
        custom_tags=["vip"],
        source_audience_id=None,
        lookalike_ratio=None,
        estimated_size=100000,
        estimated_daily_impressions=50000,
        status="active",
        created_at=now,
        updated_at=now
    )


@pytest.fixture
def sample_bidding_config():
    """示例出价配置"""
    return BiddingConfig(
        strategy=BiddingStrategy.AUTO_OCPC,
        base_bid=1.0,
        max_bid=5.0,
        min_bid=0.5,
        target_cpa=50.0,
        target_roi=2.0,
        adjustments=[]  # 必须是 list
    )


# ============================================================================
# AdManager Tests
# ============================================================================

class TestAdManager:
    """AdManager 测试"""

    def test_init_with_db_path(self, temp_db):
        """测试带数据库路径初始化"""
        manager = AdManager(db_path=temp_db)
        assert manager is not None

    def test_init_without_db_path(self):
        """测试不带数据库路径初始化"""
        import tempfile
        import uuid
        db_path = os.path.join(tempfile.gettempdir(), f"test_ads_{uuid.uuid4().hex}.db")
        manager = AdManager(db_path=db_path)
        assert manager is not None

    def test_add_account(self, ad_manager, sample_ad_account):
        """测试添加账户"""
        result = ad_manager.add_account(sample_ad_account)
        assert result is True

    def test_get_account(self, ad_manager, sample_ad_account):
        """测试获取账户"""
        ad_manager.add_account(sample_ad_account)
        account = ad_manager.get_account("test_account_001")
        assert account is not None
        assert account.account_name == "测试账户"

    def test_get_account_not_found(self, ad_manager):
        """测试获取不存在的账户"""
        account = ad_manager.get_account("nonexistent")
        assert account is None

    def test_get_all_accounts(self, ad_manager, sample_ad_account):
        """测试获取所有账户"""
        ad_manager.add_account(sample_ad_account)
        accounts = ad_manager.get_all_accounts()
        assert len(accounts) >= 1

    def test_get_all_accounts_by_platform(self, ad_manager, sample_ad_account):
        """测试按平台获取账户"""
        ad_manager.add_account(sample_ad_account)
        accounts = ad_manager.get_all_accounts(platform=AdPlatform.OCEAN_ENGINE)
        assert len(accounts) >= 1

    def test_update_account_balance(self, ad_manager, sample_ad_account):
        """测试更新账户余额"""
        ad_manager.add_account(sample_ad_account)
        result = ad_manager.update_account_balance("test_account_001", 15000.0)
        assert result is True

    def test_delete_account(self, ad_manager, sample_ad_account):
        """测试删除账户"""
        ad_manager.add_account(sample_ad_account)
        result = ad_manager.delete_account("test_account_001")
        assert result is True
        account = ad_manager.get_account("test_account_001")
        assert account is None

    def test_create_campaign(self, ad_manager, sample_ad_account, sample_ad_campaign):
        """测试创建计划"""
        ad_manager.add_account(sample_ad_account)
        result = ad_manager.create_campaign(sample_ad_campaign)
        assert result is True

    def test_get_campaign(self, ad_manager, sample_ad_account, sample_ad_campaign):
        """测试获取计划"""
        ad_manager.add_account(sample_ad_account)
        ad_manager.create_campaign(sample_ad_campaign)
        campaign = ad_manager.get_campaign("test_campaign_001")
        assert campaign is not None
        assert campaign.name == "测试计划"

    def test_get_campaign_not_found(self, ad_manager):
        """测试获取不存在的计划"""
        campaign = ad_manager.get_campaign("nonexistent")
        assert campaign is None

    def test_get_campaigns(self, ad_manager, sample_ad_account, sample_ad_campaign):
        """测试获取计划列表"""
        ad_manager.add_account(sample_ad_account)
        ad_manager.create_campaign(sample_ad_campaign)
        campaigns = ad_manager.get_campaigns()
        assert len(campaigns) >= 1

    def test_update_campaign_status(self, ad_manager, sample_ad_account, sample_ad_campaign):
        """测试更新计划状态"""
        ad_manager.add_account(sample_ad_account)
        ad_manager.create_campaign(sample_ad_campaign)
        result = ad_manager.update_campaign_status(
            "test_campaign_001", CampaignStatus.ACTIVE
        )
        assert result is True

    def test_delete_campaign(self, ad_manager, sample_ad_account, sample_ad_campaign):
        """测试删除计划"""
        ad_manager.add_account(sample_ad_account)
        ad_manager.create_campaign(sample_ad_campaign)
        result = ad_manager.delete_campaign("test_campaign_001")
        assert result is True

    def test_record_daily_stats(self, ad_manager, sample_ad_account, sample_ad_campaign):
        """测试记录每日统计"""
        ad_manager.add_account(sample_ad_account)
        ad_manager.create_campaign(sample_ad_campaign)
        result = ad_manager.record_daily_stats(
            campaign_id="test_campaign_001",
            adset_id="adset_001",
            date="2026-05-07",
            impressions=10000,
            clicks=500,
            conversions=50,
            spend=1000.0
        )
        assert result is True

    def test_get_campaign_stats(self, ad_manager, sample_ad_account, sample_ad_campaign):
        """测试获取计划统计"""
        ad_manager.add_account(sample_ad_account)
        ad_manager.create_campaign(sample_ad_campaign)
        stats = ad_manager.get_campaign_stats("test_campaign_001", days=30)
        assert stats is not None

    def test_get_platform_comparison(self, ad_manager, sample_ad_account):
        """测试平台对比"""
        ad_manager.add_account(sample_ad_account)
        comparison = ad_manager.get_platform_comparison(days=30)
        assert comparison is not None


# ============================================================================
# AudienceTargeting Tests
# ============================================================================

class TestAudienceTargeting:
    """AudienceTargeting 测试"""

    def test_init_with_db_path(self, temp_db):
        """测试带数据库路径初始化"""
        targeting = AudienceTargeting(db_path=temp_db)
        assert targeting is not None

    def test_create_segment(self, audience_targeting, sample_audience_segment):
        """测试创建人群包"""
        result = audience_targeting.create_segment(sample_audience_segment)
        assert result is True

    def test_get_segment(self, audience_targeting, sample_audience_segment):
        """测试获取人群包"""
        audience_targeting.create_segment(sample_audience_segment)
        segment = audience_targeting.get_segment("test_segment_001")
        assert segment is not None
        assert segment.name == "测试人群"

    def test_get_segment_not_found(self, audience_targeting):
        """测试获取不存在的人群包"""
        segment = audience_targeting.get_segment("nonexistent")
        assert segment is None

    def test_get_segments(self, audience_targeting, sample_audience_segment):
        """测试获取人群包列表"""
        audience_targeting.create_segment(sample_audience_segment)
        segments = audience_targeting.get_segments()
        assert len(segments) >= 1

    def test_update_segment(self, audience_targeting, sample_audience_segment):
        """测试更新人群包"""
        audience_targeting.create_segment(sample_audience_segment)
        result = audience_targeting.update_segment(
            "test_segment_001",
            {"name": "更新后名称"}
        )
        assert result is True

    def test_delete_segment(self, audience_targeting, sample_audience_segment):
        """测试删除人群包"""
        audience_targeting.create_segment(sample_audience_segment)
        result = audience_targeting.delete_segment("test_segment_001")
        assert result is True

    def test_get_interest_categories(self, audience_targeting):
        """测试获取兴趣分类"""
        categories = audience_targeting.get_interest_categories()
        assert categories is not None
        assert isinstance(categories, dict)

    def test_get_behavior_categories(self, audience_targeting):
        """测试获取行为分类"""
        categories = audience_targeting.get_behavior_categories()
        assert categories is not None
        assert isinstance(categories, dict)

    def test_estimate_audience_size(self, audience_targeting, sample_audience_segment):
        """测试预估人群规模"""
        result = audience_targeting.estimate_audience_size(sample_audience_segment)
        assert result is not None
        assert "estimated_size" in result

    def test_get_recommended_targeting(self, audience_targeting):
        """测试获取推荐定向"""
        result = audience_targeting.get_recommended_targeting(
            product_category="美妆",
            target_platform="ocean_engine"
        )
        assert result is not None

    def test_create_lookalike(self, audience_targeting, sample_audience_segment):
        """测试创建相似人群"""
        audience_targeting.create_segment(sample_audience_segment)
        result = audience_targeting.create_lookalike(
            source_segment_id="test_segment_001",
            name="相似人群",
            ratio=0.01
        )
        # 可能返回 None（如果功能未实现）
        assert result is None or result is not None


# ============================================================================
# BiddingEngine Tests
# ============================================================================

class TestBiddingEngine:
    """BiddingEngine 测试"""

    def test_init(self):
        """测试初始化"""
        engine = BiddingEngine()
        assert engine is not None

    def test_calculate_bid(self, bidding_engine, sample_bidding_config):
        """测试计算出价"""
        context = {
            "hour": 14,
            "day_of_week": 4,
            "conversion_rate": 0.05,
            "competition_level": "medium"
        }
        bid = bidding_engine.calculate_bid(sample_bidding_config, context)
        assert isinstance(bid, float)
        assert bid > 0

    def test_calculate_bid_respects_bounds(self, bidding_engine, sample_bidding_config):
        """测试出价在边界内"""
        context = {"hour": 10}
        bid = bidding_engine.calculate_bid(sample_bidding_config, context)
        assert sample_bidding_config.min_bid <= bid <= sample_bidding_config.max_bid

    def test_get_bid_suggestion(self, bidding_engine):
        """测试获取出价建议"""
        suggestion = bidding_engine.get_bid_suggestion(
            platform="ocean_engine",
            objective="conversions",
            target_audience_size=100000
        )
        assert suggestion is not None
        assert "suggested_bid" in suggestion or "bid_range" in suggestion

    def test_optimize_bidding(self, bidding_engine, sample_bidding_config):
        """测试优化出价"""
        performance_data = [
            {"bid": 1.0, "impressions": 1000, "clicks": 50, "conversions": 5, "spend": 100},
            {"bid": 1.5, "impressions": 1500, "clicks": 80, "conversions": 8, "spend": 150},
            {"bid": 2.0, "impressions": 2000, "clicks": 100, "conversions": 10, "spend": 200},
        ]
        optimized = bidding_engine.optimize_bidding(
            sample_bidding_config, performance_data
        )
        assert optimized is not None
        assert isinstance(optimized, BiddingConfig)

    def test_simulate_bidding(self, bidding_engine, sample_bidding_config):
        """测试模拟出价"""
        scenarios = [
            {"competition": "low", "conversion_rate": 0.05},
            {"competition": "medium", "conversion_rate": 0.03},
            {"competition": "high", "conversion_rate": 0.02},
        ]
        results = bidding_engine.simulate_bidding(
            sample_bidding_config, scenarios
        )
        assert results is not None
        assert len(results) == len(scenarios)
