"""Comprehensive V2 Tests - All Modules"""
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


class TestProductManagerV2:
    def test_product_lifecycle(self):
        from acas_pro.ecommerce.product_manager_v2 import ProductManager
        db, path = create_test_db()
        manager = ProductManager(db=db)
        
        success, product_id = manager.create_product("Test Product", 99.99, 100, "Electronics")
        assert success
        
        product = manager.get_product(product_id)
        assert product['name'] == "Test Product"
        assert product['price'] == 99.99
        
        success, msg = manager.update_stock(product_id, 50)
        assert success
        
        product = manager.get_product(product_id)
        assert product['stock'] == 150
        
        products = manager.list_products()
        assert len(products) >= 1
        
        db.close()
        os.unlink(path)


class TestFestivalCalendarV2:
    def test_festivals(self):
        from acas_pro.analytics.festival_calendar_v2 import FestivalCalendar
        db, path = create_test_db()
        calendar = FestivalCalendar(db=db)
        
        calendar.add_festival("Christmas", "2024-12-25", "Holiday", "Christmas Day")
        calendar.add_festival("New Year", "2024-01-01", "Holiday", "New Year's Day")
        
        festivals = calendar.get_festivals()
        assert len(festivals) >= 2
        
        db.close()
        os.unlink(path)


class TestScriptGeneratorV2:
    def test_generate(self):
        from acas_pro.content.script_generator_v2 import ScriptGenerator
        generator = ScriptGenerator()
        
        success, script = generator.generate("AI Technology", "professional", 500)
        assert success
        assert "AI Technology" in script
    
    def test_keywords(self):
        from acas_pro.content.script_generator_v2 import ScriptGenerator
        generator = ScriptGenerator()
        
        success, keywords = generator.analyze_keywords("machine learning artificial intelligence")
        assert success
        assert len(keywords) > 0


class TestVideoMakerV2:
    def test_create_video(self):
        from acas_pro.video.video_maker_v2 import VideoMaker
        maker = VideoMaker()
        
        success, video_id = maker.create_video("Test Video", "intro", 60)
        assert success
        assert len(video_id) > 0
    
    def test_templates(self):
        from acas_pro.video.video_maker_v2 import VideoMaker
        maker = VideoMaker()
        
        templates = maker.list_templates()
        assert len(templates) >= 3
        
        template = maker.get_template("intro")
        assert template is not None


class TestSettlementEngineV2:
    def test_settlement_lifecycle(self):
        from acas_pro.blockchain.settlement_engine_v2 import SettlementEngine
        db, path = create_test_db()
        engine = SettlementEngine(db=db)
        
        success, settlement_id = engine.create_settlement(1000.0, "USD")
        assert success
        
        settlement = engine.get_settlement(settlement_id)
        assert settlement['amount'] == 1000.0
        assert settlement['status'] == 'pending'
        
        success, msg = engine.complete_settlement(settlement_id)
        assert success
        
        settlement = engine.get_settlement(settlement_id)
        assert settlement['status'] == 'completed'
        
        db.close()
        os.unlink(path)


class TestSentimentAnalyzerV2:
    def test_positive(self):
        from acas_pro.sentiment.analyzer_v2 import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        
        success, result = analyzer.analyze("This is great and amazing!")
        assert success
        assert result['sentiment'] == 'positive'
    
    def test_negative(self):
        from acas_pro.sentiment.analyzer_v2 import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        
        success, result = analyzer.analyze("This is terrible and awful!")
        assert success
        assert result['sentiment'] == 'negative'
    
    def test_batch(self):
        from acas_pro.sentiment.analyzer_v2 import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        
        texts = ["Good product", "Bad service", "Excellent quality"]
        success, results = analyzer.batch_analyze(texts)
        assert success
        assert len(results) == 3


class TestPublishManagerV2:
    def test_publication_lifecycle(self):
        from acas_pro.publisher.publish_manager_v2 import PublishManager
        db, path = create_test_db()
        manager = PublishManager(db=db)
        
        success, pub_id = manager.create_publication("Test Title", "Test Content", "Twitter")
        assert success
        
        pub = manager.get_publication(pub_id)
        assert pub['title'] == "Test Title"
        assert pub['status'] == 'draft'
        
        success, msg = manager.schedule_publication(pub_id, "2024-12-01T10:00:00")
        assert success
        
        pub = manager.get_publication(pub_id)
        assert pub['status'] == 'scheduled'
        
        success, msg = manager.publish(pub_id)
        assert success
        
        pub = manager.get_publication(pub_id)
        assert pub['status'] == 'published'
        
        db.close()
        os.unlink(path)
