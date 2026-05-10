# -*- coding: utf-8 -*-
"""
ACAS Pro - Translation System
Multi-language support with JSON-based translations
"""

import json
from pathlib import Path
from typing import Dict, Optional

_locales_dir = Path(__file__).parent / "locales"

class Translator:
    """多语言翻译器"""
    
    def __init__(self):
        self._current_lang = "zh_CN"
        self._translations: Dict[str, dict] = {}
        self._load_language("zh_CN")
        self._load_language("en_US")
    
    def _load_language(self, lang: str) -> bool:
        """加载语言文件"""
        lang_file = _locales_dir / f"{lang}.json"
        if lang_file.exists():
            try:
                with open(lang_file, "r", encoding="utf-8") as f:
                    self._translations[lang] = json.load(f)
                return True
            except Exception as e:
                import logging
                logging.warning(f'Failed to load language file {lang_file}: {e}')
        return False
    
    def set_language(self, lang: str) -> bool:
        """设置当前语言"""
        if lang in self._translations or self._load_language(lang):
            self._current_lang = lang
            return True
        return False
    
    def get_language(self) -> str:
        """获取当前语言"""
        return self._current_lang
    
    def available_languages(self) -> list:
        """获取可用语言列表"""
        return list(self._translations.keys())
    
    def t(self, key: str, default: Optional[str] = None) -> str:
        """翻译文本"""
        trans = self._translations.get(self._current_lang, {})
        keys = key.split(".")
        value = trans
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default if default else key
        return str(value) if not isinstance(value, dict) else key

# 全局实例
translator = Translator()

def t(key: str, default: Optional[str] = None) -> str:
    """快捷翻译函数"""
    return translator.t(key, default)

def set_language(lang: str) -> bool:
    """设置语言"""
    return translator.set_language(lang)

def get_language() -> str:
    """获取当前语言"""
    return translator.get_language()

def available_languages() -> list:
    """获取可用语言"""
    return translator.available_languages()
