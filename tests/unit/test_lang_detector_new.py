# -*- coding: utf-8 -*-
"""Tests for language detection module"""
from acas_pro.i18n.lang_detector import LangDetector


class TestLangDetector:
    """Test LangDetector class"""
    
    def setup_method(self):
        """Setup detector for each test"""
        self.detector = LangDetector()
    
    def test_detect_chinese(self):
        """Test Chinese language detection"""
        assert self.detector.detect("你好世界") == "zh"
        assert self.detector.detect("这是一个测试") == "zh"
    
    def test_detect_japanese(self):
        """Test Japanese language detection"""
        assert self.detector.detect("こんにちは") == "ja"
        assert self.detector.detect("おはようございます") == "ja"
    
    def test_detect_korean(self):
        """Test Korean language detection"""
        assert self.detector.detect("안녕하세요") == "ko"
        assert self.detector.detect("감사합니다") == "ko"
    
    def test_detect_russian(self):
        """Test Russian language detection"""
        assert self.detector.detect("Привет мир") == "ru"
        assert self.detector.detect("Спасибо") == "ru"
    
    def test_detect_english(self):
        """Test English language detection (default)"""
        assert self.detector.detect("Hello world") == "en"
        assert self.detector.detect("This is a test") == "en"
    
    def test_detect_empty_string(self):
        """Test empty string detection"""
        assert self.detector.detect("") == "unknown"
    
    def test_detect_none(self):
        """Test None input"""
        # Should handle None gracefully
        result = self.detector.detect(None)
        assert result == "unknown"
    
    def test_confidence_with_text(self):
        """Test confidence score with valid text"""
        confidence = self.detector.confidence("Hello world")
        assert 0.0 <= confidence <= 1.0
        assert confidence == 0.9  # Stub returns 0.9
    
    def test_confidence_empty(self):
        """Test confidence score with empty text"""
        assert self.detector.confidence("") == 0.0
    
    def test_confidence_none(self):
        """Test confidence score with None"""
        result = self.detector.confidence(None)
        assert result == 0.0
    
    def test_is_cjk_chinese(self):
        """Test is_cjk for Chinese"""
        assert self.detector.is_cjk("你好") is True
    
    def test_is_cjk_japanese(self):
        """Test is_cjk for Japanese"""
        assert self.detector.is_cjk("こんにちは") is True
    
    def test_is_cjk_korean(self):
        """Test is_cjk for Korean"""
        assert self.detector.is_cjk("안녕") is True
    
    def test_is_cjk_english(self):
        """Test is_cjk for English (non-CJK)"""
        assert self.detector.is_cjk("Hello") is False
    
    def test_is_cjk_empty(self):
        """Test is_cjk for empty string"""
        assert self.detector.is_cjk("") is False
    
    def test_mixed_text_chinese_english(self):
        """Test mixed Chinese and English text"""
        # Should detect Chinese first
        assert self.detector.detect("Hello 世界") == "zh"
    
    def test_multiple_cjk_chars(self):
        """Test text with multiple CJK characters"""
        text = "你好こんにちは안녕"
        # Should detect the first CJK script found
        result = self.detector.detect(text)
        assert result in ["zh", "ja", "ko"]
