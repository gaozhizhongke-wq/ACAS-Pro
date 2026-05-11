"""V2 Only Tests - No V1 imports"""
import pytest
import tempfile
import os
import sys

# Ensure src is in path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

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


class TestConfigV2:
    def test_basic(self):
        config = AppConfig()
        assert config.environment.value == 'development'
        is_valid, errors = config.validate()
        assert isinstance(is_valid, bool)

    def test_production_validation(self):
        from acas_pro.core.config_v2 import Environment
        config = AppConfig(environment=Environment.PRODUCTION)
        is_valid, errors = config.validate()
        assert not is_valid  # Should fail without secret key


class TestSecurityV2:
    def test_password_all(self):
        from acas_pro.core.security_v2 import PasswordValidator, PasswordHasher
        validator = PasswordValidator()
        assert validator.validate("ValidPass123!")[0]
        assert not validator.validate("weak")[0]
        hasher = PasswordHasher()
        hash_str = hasher.hash("test")
        assert hasher.verify("test", hash_str)
        assert not hasher.verify("wrong", hash_str)

    def test_jwt_all(self):
        from acas_pro.core.security_v2 import JWTManager
        jwt = JWTManager()
        token = jwt.generate_token("user123")
        assert jwt.verify_token(token)[0]
        assert not jwt.verify_token("invalid")[0]

    def test_crypto_all(self):
        from acas_pro.core.security_v2 import CryptoManager
        crypto = CryptoManager()
        encrypted = crypto.encrypt("test")
        assert crypto.decrypt(encrypted) == "test"


class TestDatabaseV2:
    def test_basic(self):
        db, path = create_test_db()
        db.execute("CREATE TABLE t (id INTEGER)")
        db.execute("INSERT INTO t VALUES (1)")
        result = db.fetchone("SELECT * FROM t")
        assert result['id'] == 1
        results = db.fetchall("SELECT * FROM t")
        assert len(results) == 1
        db.close()
        os.unlink(path)


class TestUserServiceV2:
    def test_register_login(self):
        from acas_pro.services.user_service_v2 import UserService
        db, path = create_test_db()
        service = UserService(db=db)
        success, user_id = service.register("test", "ValidPass123!")
        assert success
        success, token = service.login("test", "ValidPass123!")
        assert success
        db.close()
        os.unlink(path)

    def test_invalid_login(self):
        from acas_pro.services.user_service_v2 import UserService
        db, path = create_test_db()
        service = UserService(db=db)
        success, msg = service.login("nonexistent", "wrong")
        assert not success
        db.close()
        os.unlink(path)


class TestAdManagerV2:
    def test_campaign(self):
        from acas_pro.ads.ad_manager_v2 import AdManager
        db, path = create_test_db()
        manager = AdManager(db=db)
        success, cid = manager.create_campaign("Test", 100.0)
        assert success
        campaign = manager.get_campaign(cid)
        assert campaign is not None
        db.close()
        os.unlink(path)


class TestOrderManagerV2:
    def test_order(self):
        from acas_pro.ecommerce.order_manager_v2 import OrderManager
        db, path = create_test_db()
        manager = OrderManager(db=db)
        success, oid = manager.create_order("user1", [])
        assert success
        db.close()
        os.unlink(path)


class TestProductManagerV2:
    def test_product(self):
        from acas_pro.ecommerce.product_manager_v2 import ProductManager
        db, path = create_test_db()
        manager = ProductManager(db=db)
        success, pid = manager.create_product("Test", 99.99, 100)
        assert success
        product = manager.get_product(pid)
        assert product['name'] == "Test"
        db.close()
        os.unlink(path)


class TestDataMonitorV2:
    def test_metric(self):
        from acas_pro.analytics.data_monitor_v2 import DataMonitor
        db, path = create_test_db()
        monitor = DataMonitor(db=db)
        assert monitor.record_metric("cpu", 50.0)
        db.close()
        os.unlink(path)


class TestFestivalCalendarV2:
    def test_festival(self):
        from acas_pro.analytics.festival_calendar_v2 import FestivalCalendar
        db, path = create_test_db()
        calendar = FestivalCalendar(db=db)
        assert calendar.add_festival("Test", "2024-01-01")
        festivals = calendar.get_festivals()
        assert len(festivals) >= 1
        db.close()
        os.unlink(path)


class TestScriptGeneratorV2:
    def test_generate(self):
        from acas_pro.content.script_generator_v2 import ScriptGenerator
        generator = ScriptGenerator()
        success, script = generator.generate("AI")
        assert success
        assert "AI" in script


class TestVideoMakerV2:
    def test_video(self):
        from acas_pro.video.video_maker_v2 import VideoMaker
        maker = VideoMaker()
        success, vid = maker.create_video("Test")
        assert success
        templates = maker.list_templates()
        assert len(templates) >= 3


class TestSettlementEngineV2:
    def test_settlement(self):
        from acas_pro.blockchain.settlement_engine_v2 import SettlementEngine
        db, path = create_test_db()
        engine = SettlementEngine(db=db)
        success, sid = engine.create_settlement(100.0)
        assert success
        success, msg = engine.complete_settlement(sid)
        assert success
        db.close()
        os.unlink(path)


class TestSentimentAnalyzerV2:
    def test_positive(self):
        from acas_pro.sentiment.analyzer_v2 import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        success, result = analyzer.analyze("great amazing product")
        assert success
        assert result['sentiment'] == 'positive'

    def test_negative(self):
        from acas_pro.sentiment.analyzer_v2 import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        success, result = analyzer.analyze("terrible awful bad")
        assert success
        assert result['sentiment'] == 'negative'


class TestPublishManagerV2:
    def test_publish(self):
        from acas_pro.publisher.publish_manager_v2 import PublishManager
        db, path = create_test_db()
        manager = PublishManager(db=db)
        success, pid = manager.create_publication("Test", "Content")
        assert success
        success, msg = manager.publish(pid)
        assert success
        db.close()
        os.unlink(path)


class TestRSSCollectorV2:
    def test_rss(self):
        from acas_pro.collectors.rss_collector_v2 import RSSCollector
        collector = RSSCollector()
        collector.add_feed("http://test.com")
        success, articles = collector.fetch_articles()
        assert success
        assert len(articles) >= 1


class TestBrandReputationV2:
    def test_reputation(self):
        from acas_pro.metrics.brand_reputation_v2 import BrandReputation
        reputation = BrandReputation()
        reputation.add_score("Twitter", 4.5)
        reputation.add_score("Facebook", 3.8)
        assert reputation.get_score("Twitter") == 4.5
        assert reputation.get_average() > 0


class TestAccountManagerV2:
    def test_account(self):
        from acas_pro.platforms.account_manager_v2 import AccountManager
        db, path = create_test_db()
        manager = AccountManager(db=db)
        success, aid = manager.create_account("Twitter", "testuser")
        assert success
        db.close()
        os.unlink(path)


class TestUpdaterV2:
    def test_update(self):
        from acas_pro.update.updater_v2 import UpdateManager
        manager = UpdateManager()
        success, result = manager.check_update()
        assert success
        assert "has_update" in result


class TestTranslatorV2:
    def test_translate(self):
        from acas_pro.i18n.translator_v2 import Translator
        translator = Translator()
        assert translator.translate("hello", "zh") == "你好"
        assert translator.translate("world", "zh") == "世界"


class TestLLMClientV2:
    def test_chat(self):
        from acas_pro.llm.llm_client_v2 import LLMClient
        client = LLMClient()
        success, response = client.chat("Hello")
        assert success
        assert len(response) > 0
