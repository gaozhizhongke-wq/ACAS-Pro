"""V2 Extra Tests - More edge cases"""
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


class TestExtraCoverage:
    def test_config_edge_cases(self):
        from acas_pro.core.config_v2 import AppConfig, Environment
        
        config = AppConfig(environment=Environment.PRODUCTION)
        assert config.is_production
        assert not config.is_development
        
        is_valid, errors = config.validate()
        assert not is_valid  # Missing secret key

    def test_database_edge_cases(self):
        db, path = create_test_db()
        
        db.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)")
        db.execute("INSERT INTO test (name) VALUES ('a')")
        db.execute("INSERT INTO test (name) VALUES ('b')")
        db.execute("INSERT INTO test (name) VALUES ('c')")
        
        results = db.fetchall("SELECT * FROM test ORDER BY id")
        assert len(results) == 3
        assert results[0]['name'] == 'a'
        assert results[1]['name'] == 'b'
        assert results[2]['name'] == 'c'
        
        db.close()
        os.unlink(path)

    def test_user_service_edge_cases(self):
        from acas_pro.services.user_service_v2 import UserService
        db, path = create_test_db()
        service = UserService(db=db)
        
        # Register same user twice
        success, uid1 = service.register("testuser", "ValidPass123!")
        assert success
        success, uid2 = service.register("testuser", "ValidPass123!")
        assert not success  # Should fail
        
        db.close()
        os.unlink(path)

    def test_product_manager_edge_cases(self):
        from acas_pro.ecommerce.product_manager_v2 import ProductManager
        db, path = create_test_db()
        manager = ProductManager(db=db)
        
        success, pid = manager.create_product("Test", 99.99, 0)
        assert success
        
        product = manager.get_product(pid)
        assert product['stock'] == 0
        
        db.close()
        os.unlink(path)

    def test_sentiment_edge_cases(self):
        from acas_pro.sentiment.analyzer_v2 import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        
        success, result = analyzer.analyze("")
        assert success
        assert 'sentiment' in result
        
        success, result = analyzer.analyze("good bad good bad")
        assert success
        assert 'sentiment' in result

    def test_brand_reputation_edge_cases(self):
        from acas_pro.metrics.brand_reputation_v2 import BrandReputation
        reputation = BrandReputation()
        
        reputation.add_score("A", 1.0)
        reputation.add_score("B", 5.0)
        assert reputation.get_average() == 3.0
        
        reputation.add_score("A", 3.0)
        assert reputation.get_score("A") == 3.0

    def test_translator_edge_cases(self):
        from acas_pro.i18n.translator_v2 import Translator
        translator = Translator()
        
        assert translator.translate("", "zh") == ""
        assert translator.translate("unknown", "zh") == "unknown"
