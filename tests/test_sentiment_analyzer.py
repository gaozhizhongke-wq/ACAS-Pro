#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Sentiment Analyzer Tests
"""

import pytest
from unittest.mock import Mock

from acas_pro.sentiment.analyzer import (
    SentimentAnalyzer, SentimentResult, AspectSentiment,
    SentimentLevel, sentiment_analyzer
)


class TestSentimentLevel:
    """Sentiment level enum tests"""
    
    def test_sentiment_level_values(self):
        """Test sentiment level values"""
        assert SentimentLevel.VERY_NEGATIVE.value == "very_negative"
        assert SentimentLevel.NEGATIVE.value == "negative"
        assert SentimentLevel.NEUTRAL.value == "neutral"
        assert SentimentLevel.POSITIVE.value == "positive"
        assert SentimentLevel.VERY_POSITIVE.value == "very_positive"


class TestAspectSentiment:
    """Aspect sentiment tests"""
    
    def test_aspect_sentiment_creation(self):
        """Test aspect sentiment creation"""
        aspect = AspectSentiment(
            aspect="supply_chain",
            sentiment=0.5,
            mentions=3,
            keywords=["supply", "shortage"]
        )
        
        assert aspect.aspect == "supply_chain"
        assert aspect.sentiment == 0.5
        assert aspect.mentions == 3


class TestSentimentAnalyzer:
    """Sentiment analyzer tests"""
    
    @pytest.fixture
    def analyzer(self):
        return SentimentAnalyzer()
    
    def test_init(self, analyzer):
        """Test initialization"""
        assert hasattr(analyzer, 'patterns')
        assert 'en_pos' in analyzer.patterns
        assert 'en_neg' in analyzer.patterns
    
    def test_detect_language_english(self, analyzer):
        """Test detect English language"""
        lang = analyzer._detect_language("This is an English text")
        assert lang == "en"
    
    def test_detect_language_chinese(self, analyzer):
        """Test detect Chinese language"""
        lang = analyzer._detect_language("这是一个中文文本")
        assert lang == "zh"
    
    def test_analyze_positive_english(self, analyzer):
        """Test analyze positive English text"""
        result = analyzer.analyze("The company shows strong growth and profit increase.")
        
        assert isinstance(result, SentimentResult)
        assert result.sentiment_score > 0
        assert result.language == "en"
    
    def test_analyze_negative_english(self, analyzer):
        """Test analyze negative English text"""
        result = analyzer.analyze("The market shows decline and risk of crisis.")
        
        assert isinstance(result, SentimentResult)
        assert result.sentiment_score < 0
    
    def test_analyze_neutral(self, analyzer):
        """Test analyze neutral text"""
        result = analyzer.analyze("The report was submitted yesterday.")
        
        assert isinstance(result, SentimentResult)
    
    def test_score_to_level_very_positive(self, analyzer):
        """Test score to very positive"""
        level = analyzer._score_to_level(0.8)
        assert level == SentimentLevel.VERY_POSITIVE
    
    def test_score_to_level_positive(self, analyzer):
        """Test score to positive"""
        level = analyzer._score_to_level(0.4)
        assert level == SentimentLevel.POSITIVE
    
    def test_score_to_level_neutral(self, analyzer):
        """Test score to neutral"""
        level = analyzer._score_to_level(0.0)
        assert level == SentimentLevel.NEUTRAL
    
    def test_score_to_level_negative(self, analyzer):
        """Test score to negative"""
        level = analyzer._score_to_level(-0.4)
        assert level == SentimentLevel.NEGATIVE
    
    def test_score_to_level_very_negative(self, analyzer):
        """Test score to very negative"""
        level = analyzer._score_to_level(-0.8)
        assert level == SentimentLevel.VERY_NEGATIVE
    
    def test_extract_aspects(self, analyzer):
        """Test extract aspects"""
        text = "Supply chain shortage affects production and inventory levels."
        aspects = analyzer._extract_aspects(text, "en")
        
        assert len(aspects) > 0
        aspect_names = [a.aspect for a in aspects]
        assert "supply_chain" in aspect_names
    
    def test_extract_key_phrases(self, analyzer):
        """Test extract key phrases"""
        text = "Market Growth and Innovation are key factors for Success."
        phrases = analyzer._extract_key_phrases(text, "en")
        
        assert len(phrases) > 0
    
    def test_extract_entities(self, analyzer):
        """Test extract entities"""
        text = "Apple Inc. reported 25% growth in Q3 2024."
        entities = analyzer._extract_entities(text)
        
        assert len(entities) > 0
    
    def test_tokenize_sentences(self, analyzer):
        """Test tokenize sentences"""
        text = "First sentence. Second sentence! Third?"
        sentences = analyzer._tokenize_sentences(text, "en")
        
        assert len(sentences) == 3
    
    def test_batch_analyze(self, analyzer):
        """Test batch analyze"""
        texts = [
            "Positive growth outlook.",
            "Negative decline risk.",
            "Neutral statement."
        ]
        results = analyzer.batch_analyze(texts)
        
        assert len(results) == 3
        assert all(isinstance(r, SentimentResult) for r in results)
    
    def test_analyze_with_context(self, analyzer):
        """Test analyze with context"""
        result = analyzer.analyze(
            text="Strong performance in supply chain operations.",
            context="supply_chain"
        )
        
        assert isinstance(result, SentimentResult)
        assert result.confidence > 0
    
    def test_result_to_dict(self, analyzer):
        """Test result to dict conversion"""
        result = analyzer.analyze("Growth and profit increase.")
        data = result.to_dict()
        
        assert "overall_sentiment" in data
        assert "sentiment_score" in data
        assert "confidence" in data
        assert "aspects" in data


class TestGlobalInstance:
    """Test global sentiment analyzer instance"""
    
    def test_global_instance_exists(self):
        """Test global instance exists"""
        assert sentiment_analyzer is not None
        assert isinstance(sentiment_analyzer, SentimentAnalyzer)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
