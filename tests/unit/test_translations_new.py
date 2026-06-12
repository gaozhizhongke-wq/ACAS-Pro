# -*- coding: utf-8 -*-
"""Tests for translations module"""
from acas_pro.i18n.translations import translations, _Translations


class TestTranslations:
    """Test _Translations class"""
    
    def setup_method(self):
        """Create a fresh instance for each test"""
        self.t = _Translations()
    
    def test_init(self):
        """Test initialization"""
        assert self.t._default_lang == "zh"
        assert "zh" in self.t._catalog
        assert "en" in self.t._catalog
    
    def test_get_existing_key(self):
        """Test getting existing translation"""
        # Register a test translation
        self.t.register("en", {"hello": "Hello"})
        result = self.t.get("hello", lang="en")
        assert result == "Hello"
    
    def test_get_missing_key_returns_key(self):
        """Test getting missing key returns key itself"""
        result = self.t.get("nonexistent")
        assert result == "nonexistent"
    
    def test_get_with_default_lang(self):
        """Test getting translation with default language"""
        self.t.register("zh", {"hello": "你好"})
        result = self.t.get("hello")  # Uses default lang "zh"
        assert result == "你好"
    
    def test_get_with_kwargs(self):
        """Test getting translation with keyword arguments"""
        self.t.register("en", {"greeting": "Hello, {name}!"})
        result = self.t.get("greeting", lang="en", name="World")
        assert result == "Hello, World!"
    
    def test_get_with_kwargs_missing_key(self):
        """Test getting translation with missing kwargs"""
        self.t.register("en", {"greeting": "Hello, {name}!"})
        # Missing 'name' key should return original text
        result = self.t.get("greeting", lang="en")
        assert result == "Hello, {name}!"
    
    def test_register_new_language(self):
        """Test registering a new language"""
        self.t.register("ja", {"hello": "こんにちは"})
        assert "ja" in self.t._catalog
        assert self.t.get("hello", lang="ja") == "こんにちは"
    
    def test_register_existing_language(self):
        """Test registering translations for existing language"""
        self.t.register("en", {"hello": "Hello"})
        self.t.register("en", {"bye": "Goodbye"})
        assert self.t.get("hello", lang="en") == "Hello"
        assert self.t.get("bye", lang="en") == "Goodbye"
    
    def test_set_default_lang(self):
        """Test setting default language"""
        self.t.set_default_lang("en")
        assert self.t._default_lang == "en"
    
    def test_available_languages(self):
        """Test getting available languages"""
        langs = self.t.available_languages()
        assert "zh" in langs
        assert "en" in langs
    
    def test_singleton_instance(self):
        """Test that translations is a singleton instance"""
        assert isinstance(translations, _Translations)
    
    def test_get_with_none_lang(self):
        """Test getting translation with None lang (uses default)"""
        self.t.register("zh", {"hello": "你好"})
        result = self.t.get("hello", lang=None)
        assert result == "你好"
    
    def test_format_error_handling(self):
        """Test handling of format errors"""
        self.t.register("en", {"test": "Hello {name} and {friend}"})
        # Provide only one kwarg - should handle gracefully
        result = self.t.get("test", lang="en", name="World")
        # Should either format with available args or return as-is
        assert result is not None


class TestTranslationsIntegration:
    """Integration tests for translations singleton"""
    
    def test_global_translations(self):
        """Test global translations instance"""
        # Register a test translation
        translations.register("en", {"test_key": "Test Value"})
        result = translations.get("test_key", lang="en")
        assert result == "Test Value"
    
    def test_multiple_languages(self):
        """Test switching between languages"""
        translations.register("en", {"hello": "Hello"})
        translations.register("zh", {"hello": "你好"})
        translations.register("ja", {"hello": "こんにちは"})
        
        assert translations.get("hello", lang="en") == "Hello"
        assert translations.get("hello", lang="zh") == "你好"
        assert translations.get("hello", lang="ja") == "こんにちは"
