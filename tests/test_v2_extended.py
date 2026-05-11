"""V2 Extended Tests - More coverage"""
import pytest
import tempfile
import os

from acas_pro.core.config_v2 import AppConfig, DatabaseConfig, SecurityConfig, LLMConfig
from acas_pro.core.database_v2 import DatabaseManager


def create_test_db():
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    config = AppConfig()
    config.database.path = db_path
    config.database.type = 'sqlite'
    db = DatabaseManager(config.database)
    return db, db_path


class TestConfigExtended:
    def test_database_config(self):
        db_config = DatabaseConfig()
        assert db_config.type == 'sqlite'
        assert db_config.host == 'localhost'

    def test_security_config(self):
        sec_config = SecurityConfig()
        assert sec_config.password_min_length == 8

    def test_llm_config(self):
        llm_config = LLMConfig()
        assert llm_config.provider == 'deepseek'

    def test_config_save_load(self):
        config = AppConfig()
        config.environment.value == 'development'
        is_valid, errors = config.validate()
        assert isinstance(is_valid, bool)


class TestSecurityExtended:
    def test_password_validator_edge_cases(self):
        from acas_pro.core.security_v2 import PasswordValidator
        validator = PasswordValidator()
        assert not validator.validate("short")[0]
        assert not validator.validate("nouppercase123!")[0]
        assert not validator.validate("NOLOWERCASE123!")[0]
        assert not validator.validate("NoSpecialChar123")[0]

    def test_jwt_expiration(self):
        from acas_pro.core.security_v2 import JWTManager
        jwt = JWTManager()
        token = jwt.generate_token("user123")
        assert jwt.verify_token(token)[0]

    def test_crypto_edge_cases(self):
        from acas_pro.core.security_v2 import CryptoManager
        crypto = CryptoManager()
        encrypted = crypto.encrypt("")
        assert crypto.decrypt(encrypted) == ""


class TestDatabaseExtended:
    def test_transaction(self):
        db, path = create_test_db()
        db.execute("CREATE TABLE t (id INTEGER)")
        db.execute("INSERT INTO t VALUES (1)")
        db.execute("INSERT INTO t VALUES (2)")
        results = db.fetchall("SELECT * FROM t")
        assert len(results) == 2
        db.close()
        os.unlink(path)

    def test_fetchone_none(self):
        db, path = create_test_db()
        db.execute("CREATE TABLE t (id INTEGER)")
        result = db.fetchone("SELECT * FROM t WHERE id = 999")
        assert result is None
        db.close()
        os.unlink(path)


class TestUserServiceExtended:
    def test_user_crud(self):
        from acas_pro.services.user_service_v2 import UserService
        db, path = create_test_db()
        service = UserService(db=db)
        
        # Register
        success, user_id = service.register("testuser", "ValidPass123!")
        assert success
        
        # Login
        success, token = service.login("testuser", "ValidPass123!")
        assert success
        
        # Invalid login
        success, msg = service.login("testuser", "wrongpass")
        assert not success
        
        db.close()
        os.unlink(path)


class TestAdManagerExtended:
    def test_campaign_lifecycle(self):
        from acas_pro.ads.ad_manager_v2 import AdManager
        db, path = create_test_db()
        manager = AdManager(db=db)
        
        success, cid = manager.create_campaign("Test", 100.0)
        assert success
        
        campaign = manager.get_campaign(cid)
        assert campaign is not None
        assert campaign['name'] == "Test"
        
        db.close()
        os.unlink(path)


class TestProductManagerExtended:
    def test_product_stock(self):
        from acas_pro.ecommerce.product_manager_v2 import ProductManager
        db, path = create_test_db()
        manager = ProductManager(db=db)
        
        success, pid = manager.create_product("Test", 99.99, 100)
        assert success
        
        success, msg = manager.update_stock(pid, 50)
        assert success
        
        product = manager.get_product(pid)
        assert product['stock'] == 150
        
        db.close()
        os.unlink(path)


class TestSentimentExtended:
    def test_sentiment_neutral(self):
        from acas_pro.sentiment.analyzer_v2 import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        success, result = analyzer.analyze("the weather is okay")
        assert success
        assert result['sentiment'] == 'neutral'

    def test_sentiment_batch(self):
        from acas_pro.sentiment.analyzer_v2 import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        texts = ["great product", "terrible service", "okay experience"]
        success, results = analyzer.batch_analyze(texts)
        assert success
        assert len(results) == 3


class TestBrandReputationExtended:
    def test_average_calculation(self):
        from acas_pro.metrics.brand_reputation_v2 import BrandReputation
        reputation = BrandReputation()
        reputation.add_score("Twitter", 4.5)
        reputation.add_score("Facebook", 3.5)
        assert reputation.get_average() == 4.0

    def test_empty_reputation(self):
        from acas_pro.metrics.brand_reputation_v2 import BrandReputation
        reputation = BrandReputation()
        assert reputation.get_average() == 0.0


class TestTranslatorExtended:
    def test_add_translation(self):
        from acas_pro.i18n.translator_v2 import Translator
        translator = Translator()
        translator.add_translation("test", "测试", "zh")
        assert translator.translate("test", "zh") == "测试"

    def test_missing_translation(self):
        from acas_pro.i18n.translator_v2 import Translator
        translator = Translator()
        assert translator.translate("missing", "zh") == "missing"
