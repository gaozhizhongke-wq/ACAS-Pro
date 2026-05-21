#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for sentiment/analyzer.py module."""

from datetime import datetime
from unittest.mock import MagicMock, patch
import sys
import pytest

if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()

from acas_pro.sentiment.analyzer import (
    SentimentLevel, AspectSentiment, SentimentResult, SentimentAnalyzer
)


class TestSentimentLevel:
    def test_values(self):
        assert SentimentLevel.VERY_NEGATIVE.value == "very_negative"
        assert SentimentLevel.NEGATIVE.value == "negative"
        assert SentimentLevel.NEUTRAL.value == "neutral"
        assert SentimentLevel.POSITIVE.value == "positive"
        assert SentimentLevel.VERY_POSITIVE.value == "very_positive"


class TestAspectSentiment:
    def test_creation(self):
        a = AspectSentiment(aspect="quality", sentiment=0.8, mentions=5, keywords=["good", "great"])
        assert a.aspect == "quality"
        assert a.sentiment == 0.8
        assert a.mentions == 5


class TestSentimentResult:
    def test_to_dict(self):
        result = SentimentResult(
            text="Great product!", overall_sentiment=SentimentLevel.POSITIVE,
            sentiment_score=0.8, confidence=0.9,
            aspects=[AspectSentiment("quality", 0.9, 1, ["great"])],
            key_phrases=["great product"], entities=["product"],
            language="en", analyzed_at=datetime.now().isoformat()
        )
        d = result.to_dict()
        assert d["overall_sentiment"] == "positive"
        assert d["sentiment_score"] == 0.8
        assert len(d["aspects"]) == 1
        assert "key_phrases" in d


class TestSentimentAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return SentimentAnalyzer()
    
    def test_init(self, analyzer):
        assert analyzer.patterns is not None
        assert 'en_pos' in analyzer.patterns
        assert 'en_neg' in analyzer.patterns
        assert 'zh_pos' in analyzer.patterns
        assert 'zh_neg' in analyzer.patterns
    
    def test_analyze_english_positive(self, analyzer):
        result = analyzer.analyze("Strong growth and profit increase this quarter")
        assert result is not None
        assert isinstance(result, SentimentResult)
        assert result.language == "en"
    
    def test_analyze_english_negative(self, analyzer):
        result = analyzer.analyze("Severe decline and loss in revenue")
        assert result is not None
        assert result.language == "en"
    
    def test_analyze_chinese_positive(self, analyzer):
        result = analyzer.analyze("市场增长强劲，利润持续上升")
        assert result is not None
        assert result.language == "zh"
    
    def test_analyze_chinese_negative(self, analyzer):
        result = analyzer.analyze("收入下降，面临亏损风险")
        assert result is not None
        assert result.language == "zh"
    
    def test_analyze_empty_text(self, analyzer):
        result = analyzer.analyze("")
        assert result is not None
    
    def test_score_to_level(self, analyzer):
        assert analyzer._score_to_level(0.8) in [SentimentLevel.POSITIVE, SentimentLevel.VERY_POSITIVE]
        assert analyzer._score_to_level(-0.8) in [SentimentLevel.NEGATIVE, SentimentLevel.VERY_NEGATIVE]
        assert analyzer._score_to_level(0.0) == SentimentLevel.NEUTRAL
    
    def test_detect_language(self, analyzer):
        assert analyzer._detect_language("Hello world") == "en"
        assert analyzer._detect_language("你好世界") == "zh"
    
    def test_extract_aspects(self, analyzer):
        aspects = analyzer._extract_aspects("supply chain shortage and revenue decline", "en")
        assert isinstance(aspects, list)
