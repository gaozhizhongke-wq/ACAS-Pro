"""Translation registry and lookup."""

from typing import Dict, Optional


class _Translations:
    """Simple translation lookup."""

    def __init__(self):
        self._catalog: Dict[str, Dict[str, str]] = {"zh": {}, "en": {}}
        self._default_lang = "zh"

    def get(self, key: str, lang: Optional[str] = None, **kwargs) -> str:
        language = lang or self._default_lang
        text = self._catalog.get(language, {}).get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, IndexError):
                pass
        return text

    def register(self, lang: str, catalog: Dict[str, str]):
        if lang not in self._catalog:
            self._catalog[lang] = {}
        self._catalog[lang].update(catalog)

    def set_default_lang(self, lang: str):
        self._default_lang = lang

    def available_languages(self):
        return list(self._catalog.keys())


translations = _Translations()
