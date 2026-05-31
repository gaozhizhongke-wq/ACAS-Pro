#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Translator Tests
"""

import pytest
from unittest.mock import Mock, patch, mock_open

from acas_pro.i18n.translator import Translator, t, set_language, get_language, available_languages


class TestTranslator:
    """Translator tests"""
    
    @pytest.fixture
    def translator(self):
        with patch('acas_pro.i18n.translator.Path') as mock_path:
            mock_path.return_value.__truediv__ = Mock(return_value=Mock(exists=Mock(return_value=False)))
            return Translator()
    
    def test_init(self, translator):
        """Test initialization"""
        assert translator._current_lang == "zh_CN"
    
    def test_set_language(self, translator):
        """Test set language"""
        translator._translations["en_US"] = {}
        
        result = translator.set_language("en_US")
        
        assert result is True
        assert translator._current_lang == "en_US"
    
    def test_set_language_invalid(self, translator):
        """Test set invalid language"""
        result = translator.set_language("invalid_lang")
        
        assert result is False
        assert translator._current_lang == "zh_CN"
    
    def test_get_language(self, translator):
        """Test get language"""
        lang = translator.get_language()
        assert lang == "zh_CN"
    
    def test_available_languages(self, translator):
        """Test available languages"""
        langs = translator.available_languages()
        assert isinstance(langs, list)
    
    def test_t_simple_key(self, translator):
        """Test translate simple key"""
        translator._translations["zh_CN"] = {"hello": "你好"}
        
        result = translator.t("hello")
        
        assert result == "你好"
    
    def test_t_nested_key(self, translator):
        """Test translate nested key"""
        translator._translations["zh_CN"] = {
            "user": {
                "name": "用户名"
            }
        }
        
        result = translator.t("user.name")
        
        assert result == "用户名"
    
    def test_t_missing_key(self, translator):
        """Test translate missing key"""
        translator._translations["zh_CN"] = {}
        
        result = translator.t("missing.key")
        
        assert result == "missing.key"
    
    def test_t_with_default(self, translator):
        """Test translate with default"""
        translator._translations["zh_CN"] = {}
        
        result = translator.t("missing", default="Default Value")
        
        assert result == "Default Value"
    
    def test_t_nested_dict_returns_key(self, translator):
        """Test that nested dict returns key"""
        translator._translations["zh_CN"] = {
            "user": {
                "profile": {
                    "name": "test"
                }
            }
        }
        
        result = translator.t("user.profile")
        assert result == "user.profile"


class TestGlobalFunctions:
    """Global function tests - minimal for coverage (no shared state)"""
    
    def test_t_returns_key_when_not_found(self):
        """Test t() returns key when translation not found"""
        result = t("nonexistent_key_abc123")
        assert result == "nonexistent_key_abc123"
    
    def test_t_with_default(self):
        """Test t() with default parameter"""
        result = t("nonexistent_key_abc123", default="默认值")
        assert result == "默认值"
    
    def test_set_language_nonexistent(self):
        """Test set_language with nonexistent language"""
        result = set_language("nonexistent_lang")
        assert result is False
    
    def test_get_language(self):
        """Test get_language returns a string"""
        result = get_language()
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_available_languages(self):
        """Test available_languages returns a list"""
        result = available_languages()
        assert isinstance(result, list)
        assert len(result) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
