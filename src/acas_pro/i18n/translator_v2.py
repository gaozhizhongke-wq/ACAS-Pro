"""ACAS Pro - Translator v2"""
from typing import Dict, Any, Optional

from ..core.config_v2 import AppConfig


class Translator:
    """Translator - testable with DI"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load()
        self._translations: Dict[str, Dict[str, str]] = {
            "en": {"hello": "Hello", "world": "World"},
            "zh": {"hello": "你好", "world": "世界"}
        }
    
    def translate(self, text: str, target_lang: str = "en") -> str:
        """Translate text"""
        translations = self._translations.get(target_lang, {})
        return translations.get(text.lower(), text)
    
    def add_translation(self, key: str, value: str, lang: str = "en") -> bool:
        """Add translation"""
        if lang not in self._translations:
            self._translations[lang] = {}
        self._translations[lang][key.lower()] = value
        return True
