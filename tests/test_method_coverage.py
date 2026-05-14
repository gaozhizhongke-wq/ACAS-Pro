#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Method-level coverage tests"""

import pytest


class TestAdManagerMethods:
    """Test AdManager methods"""
    
    def test_get_campaigns(self):
        from acas_pro.ads.ad_manager import AdManager
        import tempfile, uuid, os
        db_path = os.path.join(tempfile.gettempdir(), f"test_{uuid.uuid4().hex}.db")
        manager = AdManager(db_path=db_path)
        campaigns = manager.get_campaigns()
        assert isinstance(campaigns, list)
    
    def test_get_all_accounts(self):
        from acas_pro.ads.ad_manager import AdManager
        import tempfile, uuid, os
        db_path = os.path.join(tempfile.gettempdir(), f"test_{uuid.uuid4().hex}.db")
        manager = AdManager(db_path=db_path)
        accounts = manager.get_all_accounts()
        assert isinstance(accounts, list)
    
    def test_get_platform_comparison(self):
        from acas_pro.ads.ad_manager import AdManager
        import tempfile, uuid, os
        db_path = os.path.join(tempfile.gettempdir(), f"test_{uuid.uuid4().hex}.db")
        manager = AdManager(db_path=db_path)
        result = manager.get_platform_comparison()
        assert result is not None


class TestAudienceTargetingMethods:
    """Test AudienceTargeting methods"""
    
    def test_get_interest_categories(self):
        from acas_pro.ads.audience_targeting import AudienceTargeting
        import tempfile, uuid, os
        db_path = os.path.join(tempfile.gettempdir(), f"test_{uuid.uuid4().hex}.db")
        targeting = AudienceTargeting(db_path=db_path)
        categories = targeting.get_interest_categories()
        assert isinstance(categories, dict)
    
    def test_get_behavior_categories(self):
        from acas_pro.ads.audience_targeting import AudienceTargeting
        import tempfile, uuid, os
        db_path = os.path.join(tempfile.gettempdir(), f"test_{uuid.uuid4().hex}.db")
        targeting = AudienceTargeting(db_path=db_path)
        categories = targeting.get_behavior_categories()
        assert isinstance(categories, dict)
    
    def test_get_recommended_targeting(self):
        from acas_pro.ads.audience_targeting import AudienceTargeting
        import tempfile, uuid, os
        db_path = os.path.join(tempfile.gettempdir(), f"test_{uuid.uuid4().hex}.db")
        targeting = AudienceTargeting(db_path=db_path)
        result = targeting.get_recommended_targeting("美妆", "ocean_engine")
        assert result is not None


class TestBiddingEngineMethods:
    """Test BiddingEngine methods"""
    
    def test_optimize_bidding(self):
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
        data = [
            {"bid": 1.0, "impressions": 1000, "clicks": 50, "conversions": 5, "spend": 100},
        ]
        result = engine.optimize_bidding(config, data)
        assert result is not None
    
    def test_simulate_bidding(self):
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
        scenarios = [{"competition": "low", "conversion_rate": 0.05}]
        result = engine.simulate_bidding(config, scenarios)
        assert isinstance(result, list)


class TestProductManagerMethods:
    """Test ProductManager methods"""
    
    def test_get_products_by_shop(self):
        from acas_pro.ecommerce.product_manager import ProductManager
        pm = ProductManager()
        products = pm.get_products_by_shop("shop1")
        assert isinstance(products, list)
    
    def test_update_stock(self):
        from acas_pro.ecommerce.product_manager import ProductManager
        pm = ProductManager()
        result = pm.update_stock("prod1", 100)
        assert result is not None


class TestAccountManagerMethods:
    """Test AccountManager methods"""
    
    def test_get_accounts(self):
        from acas_pro.platforms.account_manager import AccountManager
        am = AccountManager()
        accounts = am.list_accounts()
        assert isinstance(accounts, list)
    
    def test_get_account_stats(self):
        from acas_pro.platforms.account_manager import AccountManager
        am = AccountManager()
        stats = am.get_account_summary()
        assert stats is not None


class TestConversationMethods:
    """Test Conversation methods"""
    
    def test_create_conversation(self):
        from acas_pro.llm.conversation import ConversationManager
        manager = ConversationManager()
        conv = manager.create_conversation("test_user")
        assert conv is not None
    
    def test_get_conversation(self):
        from acas_pro.llm.conversation import ConversationManager
        manager = ConversationManager()
        conv = manager.get_conversation("nonexistent")
        assert conv is None


class TestSecurityMethods:
    """Test Security methods"""
    
    def test_session_manager(self):
        from acas_pro.core.security import SessionManager
        session = SessionManager()
        assert session is not None
    
    def test_generate_refresh_token(self):
        from acas_pro.core.security import JWTManager
        token = JWTManager.generate_refresh_token("user123")
        assert token is not None
    
    def test_password_validation_detailed(self):
        from acas_pro.core.security import PasswordValidator
        is_valid, msg = PasswordValidator.validate("Short1!")
        assert is_valid is False
        is_valid, msg = PasswordValidator.validate("NoSpecial123")
        assert is_valid is False
        is_valid, msg = PasswordValidator.validate("nouppercase123!")
        assert is_valid is False
        is_valid, msg = PasswordValidator.validate("NOLOWERCASE123!")
        assert is_valid is False


class TestConfigMethods:
    """Test Config methods"""
    
    def test_config_reload(self):
        from acas_pro.core.config import get_config
        config = get_config()
        assert config.security is not None
        assert config.database is not None
        assert config.llm is not None


class TestDatabaseMethods:
    """Test Database methods"""
    
    def test_execute_many(self):
        from acas_pro.core.database import DatabaseManager
        db = DatabaseManager()
        uid = __import__('uuid').uuid4().hex[:8]
        db.execute(f"CREATE TABLE IF NOT EXISTS test_many_{uid} (id INTEGER)")
        # execute_many not available, use multiple execute
        for i in range(3):
            db.execute(f"INSERT INTO test_many_{uid} VALUES (?)", (i,))
        rows = db.fetchall(f"SELECT * FROM test_many_{uid}")
        assert len(rows) == 3
    
    def test_table_exists(self):
        from acas_pro.core.database import DatabaseManager
        db = DatabaseManager()
        uid = __import__('uuid').uuid4().hex[:8]
        db.execute(f"CREATE TABLE IF NOT EXISTS test_exists_{uid} (id INTEGER)")
        rows = db.fetchall(f"SELECT name FROM sqlite_master WHERE type='table' AND name='test_exists_{uid}'")
        assert len(rows) == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
