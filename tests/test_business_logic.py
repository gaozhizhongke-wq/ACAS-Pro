#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Business logic coverage tests - simplified"""

import pytest


class TestAdManagerBusiness:
    """Test AdManager business logic"""

    def _make_manager(self):
        """Create AdManager with auto-cleanup."""
        import tempfile, uuid, os
        from acas_pro.ads.ad_manager import AdManager
        db_path = os.path.join(tempfile.gettempdir(), f"test_ads_{uuid.uuid4().hex}.db")
        manager = AdManager(db_path=db_path)
        # Store db_path for later cleanup
        manager._db_path_for_cleanup = db_path
        return manager

    def _close_manager(self, manager):
        """Explicitly close the manager to avoid ResourceWarning."""
        if manager is not None:
            import os as _os
            try:
                manager.close()
            except Exception:
                pass
            # Also clean up the temp db file
            db_path = getattr(manager, '_db_path_for_cleanup', None)
            if db_path and _os.path.exists(db_path):
                try:
                    _os.remove(db_path)
                except Exception:
                    pass

    def test_create_campaign(self):
        from acas_pro.ads.ad_manager import AdManager, AdCampaign, AdPlatform, CampaignStatus, BudgetType
        manager = self._make_manager()
        try:
            from datetime import datetime
            campaign = AdCampaign(
                id="test_campaign",
                name="Test Campaign",
                platform=AdPlatform.OCEAN_ENGINE,
                account_id="test_account",
                status=CampaignStatus.DRAFT,
                objective="conversions",
                budget_type=BudgetType.DAILY,
                budget_amount=500.0,
                start_date=datetime.now().isoformat(),
                end_date=datetime.now().isoformat(),
                conversion_goal="purchase",
                adsets=[],
                total_impressions=0,
                total_clicks=0,
                total_conversions=0,
                total_spend=0.0,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            result = manager.create_campaign(campaign)
            assert result is True
        finally:
            self._close_manager(manager)

    def test_add_account(self):
        from acas_pro.ads.ad_manager import AdManager, AdAccount, AdPlatform
        manager = self._make_manager()
        try:
            from datetime import datetime
            account = AdAccount(
                id="test_account",
                platform=AdPlatform.OCEAN_ENGINE,
                account_name="Test Account",
                account_id="oc_12345",
                access_token="test_token",
                refresh_token="test_refresh",
                token_expires_at=datetime.now(),
                status="active",
                balance=10000.0,
                daily_budget_limit=1000.0,
                total_spend_7d=500.0,
                total_spend_30d=2000.0,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            result = manager.add_account(account)
            assert result is True
        finally:
            self._close_manager(manager)


class TestAudienceTargetingBusiness:
    """Test AudienceTargeting business logic"""

    def _make_targeting(self):
        """Create AudienceTargeting with auto-cleanup."""
        import tempfile, uuid, os
        from acas_pro.ads.audience_targeting import AudienceTargeting
        db_path = os.path.join(tempfile.gettempdir(), f"test_aud_{uuid.uuid4().hex}.db")
        targeting = AudienceTargeting(db_path=db_path)
        targeting._db_path_for_cleanup = db_path
        return targeting

    def _close_targeting(self, targeting):
        """Explicitly close to avoid ResourceWarning."""
        if targeting is not None:
            import os as _os
            try:
                targeting.close()
            except Exception:
                pass
            db_path = getattr(targeting, '_db_path_for_cleanup', None)
            if db_path and _os.path.exists(db_path):
                try:
                    _os.remove(db_path)
                except Exception:
                    pass

    def test_create_segment(self):
        from acas_pro.ads.audience_targeting import AudienceTargeting, AudienceSegment, AudienceType, Gender, AgeRange, GeoTargeting, DeviceTargeting
        targeting = self._make_targeting()
        try:
            from datetime import datetime
            segment = AudienceSegment(
                id="test_segment",
                name="Test Segment",
                type=AudienceType.CUSTOM,
                gender=Gender.ALL,
                age_range=AgeRange(min_age=18, max_age=45),
                geo_targeting=GeoTargeting(provinces=["北京"]),
                device_targeting=DeviceTargeting(os_types=["ios"]),
                interests=["电商"],
                behaviors=["购买"],
                custom_tags=["vip"],
                source_audience_id=None,
                lookalike_ratio=None,
                estimated_size=100000,
                estimated_daily_impressions=50000,
                status="active",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            result = targeting.create_segment(segment)
            assert result is True
        finally:
            self._close_targeting(targeting)

    def test_estimate_audience_size(self):
        from acas_pro.ads.audience_targeting import AudienceTargeting, AudienceSegment, AudienceType, Gender, AgeRange, GeoTargeting, DeviceTargeting
        targeting = self._make_targeting()
        try:
            from datetime import datetime
            segment = AudienceSegment(
                id="test_segment",
                name="Test",
                type=AudienceType.CUSTOM,
                gender=Gender.ALL,
                age_range=AgeRange(min_age=18, max_age=45),
                geo_targeting=GeoTargeting(provinces=["北京"]),
                device_targeting=DeviceTargeting(os_types=["ios"]),
                interests=["电商"],
                behaviors=["购买"],
                custom_tags=["vip"],
                source_audience_id=None,
                lookalike_ratio=None,
                estimated_size=100000,
                estimated_daily_impressions=50000,
                status="active",
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            result = targeting.estimate_audience_size(segment)
            assert result is not None
        finally:
            self._close_targeting(targeting)


class TestBiddingEngineBusiness:
    """Test BiddingEngine business logic"""
    
    def test_calculate_bid(self):
        from acas_pro.ads.bidding_engine import BiddingEngine, BiddingConfig, BiddingStrategy
        engine = BiddingEngine()
        config = BiddingConfig(
            strategy=BiddingStrategy.AUTO_OCPC,
            base_bid=1.0,
            max_bid=5.0,
            min_bid=0.5,
            target_cpa=50.0,
            target_roi=2.0,
            adjustments=[]
        )
        context = {"hour": 14, "day_of_week": 4}
        bid = engine.calculate_bid(config, context)
        assert isinstance(bid, float)
        assert bid > 0
    
    def test_get_bid_suggestion(self):
        from acas_pro.ads.bidding_engine import BiddingEngine
        engine = BiddingEngine()
        suggestion = engine.get_bid_suggestion("ocean_engine", "conversions", 100000)
        assert suggestion is not None


class TestProductManagerBusiness:
    """Test ProductManager business logic"""
    
    def test_init(self):
        from acas_pro.ecommerce.product_manager import ProductManager
        manager = ProductManager()
        assert manager is not None
    
    def test_get_low_stock(self):
        from acas_pro.ecommerce.product_manager import ProductManager
        manager = ProductManager()
        products = manager.get_low_stock_products(shop_id="shop1")
        assert isinstance(products, list)


class TestSettlementEngineBusiness:
    """Test SettlementEngine business logic"""
    
    def test_init(self):
        from acas_pro.blockchain.settlement_engine import SettlementEngine
        engine = SettlementEngine()
        assert engine is not None


class TestAccountManagerBusiness:
    """Test AccountManager business logic"""
    
    def test_init(self):
        from acas_pro.platforms.account_manager import AccountManager
        manager = AccountManager()
        assert manager is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
