"""V2 More Tests - Additional coverage"""
import pytest
import tempfile
import os

from acas_pro.core.config_v2 import AppConfig
from acas_pro.core.database_v2 import DatabaseManager


def create_test_db():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    config = AppConfig()
    config.database.path = db_path
    config.database.type = 'sqlite'
    db = DatabaseManager(config.database)
    return db, db_path


class TestConfigMore:
    def test_config_dict(self):
        config = AppConfig()
        data = config.to_dict()
        assert 'environment' in data
        assert 'debug' in data

    def test_config_properties(self):
        config = AppConfig()
        assert config.is_development
        assert not config.is_production


class TestDatabaseMore:
    def test_multiple_tables(self):
        db, path = create_test_db()
        db.execute("CREATE TABLE users (id INTEGER)")
        db.execute("CREATE TABLE orders (id INTEGER)")
        db.execute("INSERT INTO users VALUES (1)")
        db.execute("INSERT INTO orders VALUES (1)")
        users = db.fetchall("SELECT * FROM users")
        orders = db.fetchall("SELECT * FROM orders")
        assert len(users) == 1
        assert len(orders) == 1
        db.close()
        os.unlink(path)


class TestUserServiceMore:
    def test_multiple_users(self):
        from acas_pro.services.user_service_v2 import UserService
        db, path = create_test_db()
        service = UserService(db=db)
        
        success, uid1 = service.register("user1", "ValidPass123!")
        assert success
        success, uid2 = service.register("user2", "ValidPass123!")
        assert success
        
        success, token1 = service.login("user1", "ValidPass123!")
        assert success
        success, token2 = service.login("user2", "ValidPass123!")
        assert success
        
        db.close()
        os.unlink(path)


class TestProductManagerMore:
    def test_product_list(self):
        from acas_pro.ecommerce.product_manager_v2 import ProductManager
        db, path = create_test_db()
        manager = ProductManager(db=db)
        
        success, pid1 = manager.create_product("Product1", 10.0, 100)
        assert success
        success, pid2 = manager.create_product("Product2", 20.0, 200)
        assert success
        
        products = manager.list_products()
        assert len(products) == 2
        
        db.close()
        os.unlink(path)


class TestSentimentMore:
    def test_sentiment_scores(self):
        from acas_pro.sentiment.analyzer_v2 import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        
        success, result = analyzer.analyze("great amazing product")
        assert success
        assert 'score' in result
        
        success, result = analyzer.analyze("terrible awful bad")
        assert success
        assert 'score' in result


class TestRSSCollectorMore:
    def test_multiple_feeds(self):
        from acas_pro.collectors.rss_collector_v2 import RSSCollector
        collector = RSSCollector()
        collector.add_feed("http://test1.com")
        collector.add_feed("http://test2.com")
        success, articles = collector.fetch_articles()
        assert success
        assert len(articles) >= 2


class TestBrandReputationMore:
    def test_multiple_platforms(self):
        from acas_pro.metrics.brand_reputation_v2 import BrandReputation
        reputation = BrandReputation()
        reputation.add_score("Twitter", 4.5)
        reputation.add_score("Facebook", 3.5)
        reputation.add_score("Instagram", 5.0)
        avg = reputation.get_average()
        assert avg > 0


class TestTranslatorMore:
    def test_basic_translation(self):
        from acas_pro.i18n.translator_v2 import Translator
        translator = Translator()
        assert translator.translate("hello", "zh") == "你好"


class TestLLMClientMore:
    def test_llm_config(self):
        from acas_pro.llm.llm_client_v2 import LLMClient
        client = LLMClient()
        success, response = client.chat("Test")
        assert success
        assert len(response) > 0
