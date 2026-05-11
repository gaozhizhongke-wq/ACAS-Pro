"""Test V2 Business Modules"""
import pytest
import tempfile
import os

from acas_pro.core.config_v2 import AppConfig
from acas_pro.core.database_v2 import DatabaseManager


def create_test_db():
    """Create test database"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    config = AppConfig()
    config.database.path = db_path
    config.database.type = 'sqlite'
    db = DatabaseManager(config.database)
    return db, db_path


class TestAdManagerV2:
    def test_create_campaign(self):
        from acas_pro.ads.ad_manager_v2 import AdManager
        db, path = create_test_db()
        manager = AdManager(db=db)
        
        success, campaign_id = manager.create_campaign("Test Campaign", 1000.0)
        assert success
        assert len(campaign_id) > 0
        
        campaign = manager.get_campaign(campaign_id)
        assert campaign['name'] == "Test Campaign"
        
        db.close()
        os.unlink(path)
    
    def test_list_campaigns(self):
        from acas_pro.ads.ad_manager_v2 import AdManager
        db, path = create_test_db()
        manager = AdManager(db=db)
        
        manager.create_campaign("Campaign 1", 100.0)
        manager.create_campaign("Campaign 2", 200.0)
        
        campaigns = manager.list_campaigns()
        assert len(campaigns) >= 2
        
        db.close()
        os.unlink(path)
    
    def test_create_ad(self):
        from acas_pro.ads.ad_manager_v2 import AdManager
        db, path = create_test_db()
        manager = AdManager(db=db)
        
        success, campaign_id = manager.create_campaign("Test", 100.0)
        success, ad_id = manager.create_ad(campaign_id, "Ad Title", "Ad Content")
        
        assert success
        ad = manager.get_ad(ad_id)
        assert ad['title'] == "Ad Title"
        
        db.close()
        os.unlink(path)


class TestOrderManagerV2:
    def test_create_order(self):
        from acas_pro.ecommerce.order_manager_v2 import OrderManager
        db, path = create_test_db()
        manager = OrderManager(db=db)
        
        items = [
            {'product_id': 'p1', 'quantity': 2, 'price': 10.0},
            {'product_id': 'p2', 'quantity': 1, 'price': 20.0}
        ]
        
        success, order_id = manager.create_order("user1", items)
        assert success
        
        order = manager.get_order(order_id)
        assert order['total_amount'] == 40.0
        
        db.close()
        os.unlink(path)
    
    def test_update_status(self):
        from acas_pro.ecommerce.order_manager_v2 import OrderManager
        db, path = create_test_db()
        manager = OrderManager(db=db)
        
        success, order_id = manager.create_order("user1", [])
        success, msg = manager.update_status(order_id, "shipped")
        
        assert success
        order = manager.get_order(order_id)
        assert order['status'] == "shipped"
        
        db.close()
        os.unlink(path)


class TestDataMonitorV2:
    def test_record_metric(self):
        from acas_pro.analytics.data_monitor_v2 import DataMonitor
        db, path = create_test_db()
        monitor = DataMonitor(db=db)
        
        assert monitor.record_metric("cpu_usage", 75.5)
        
        metrics = monitor.get_metrics("cpu_usage")
        assert len(metrics) >= 1
        
        db.close()
        os.unlink(path)
    
    def test_get_average(self):
        from acas_pro.analytics.data_monitor_v2 import DataMonitor
        db, path = create_test_db()
        monitor = DataMonitor(db=db)
        
        monitor.record_metric("temperature", 20.0)
        monitor.record_metric("temperature", 30.0)
        
        avg = monitor.get_average("temperature")
        assert avg == 25.0
        
        db.close()
        os.unlink(path)


class TestLLMClientV2:
    def test_chat(self):
        from acas_pro.llm.llm_client_v2 import LLMClient
        client = LLMClient()
        
        success, response = client.chat("Hello")
        assert success
        assert len(response) > 0
    
    def test_history(self):
        from acas_pro.llm.llm_client_v2 import LLMClient
        client = LLMClient()
        
        client.chat("Message 1")
        client.chat("Message 2")
        
        history = client.get_history()
        assert len(history) == 4  # 2 user + 2 assistant
    
    def test_sentiment(self):
        from acas_pro.llm.llm_client_v2 import LLMClient
        client = LLMClient()
        
        success, result = client.analyze_sentiment("Great product!")
        assert success
        assert result['sentiment'] == 'positive'
    
    def test_summary(self):
        from acas_pro.llm.llm_client_v2 import LLMClient
        client = LLMClient()
        
        success, summary = client.generate_summary("Short text", max_length=100)
        assert success
        assert len(summary) <= 103


class TestAuthRoutesV2:
    def test_blueprint_exists(self):
        from acas_pro.web.routes.auth_v2 import bp
        assert bp is not None
        assert bp.name == 'auth_v2'
