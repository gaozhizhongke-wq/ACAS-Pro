"""Language detection utility."""

import re


class LangDetector:
    """Detect the language of a text string."""

    # Simplified patterns
    _ZH_PATTERN = re.compile(r"[\u4e00-\u9fff]")
    _JA_PATTERN = re.compile(r"[\u3040-\u309f\u30a0-\u30ff]")
    _KO_PATTERN = re.compile(r"[\uac00-\ud7af]")
    _RU_PATTERN = re.compile(r"[\u0400-\u04ff]")

    def detect(self, text: str) -> str:
        """Return ISO 639-1 language code."""
        if not text:
            return "unknown"
        if self._ZH_PATTERN.search(text):
            return "zh"
        if self._JA_PATTERN.search(text):
            return "ja"
        if self._KO_PATTERN.search(text):
            return "ko"
        if self._RU_PATTERN.search(text):
            return "ru"
        # Default to English for Latin-based scripts
        return "en"

    def confidence(self, text: str) -> float:
        """Return confidence score 0-1 for detected language."""
        if not text:
            return 0.0
        lang = self.detect(text)
        if lang == "unknown":
            return 0.0
        return 0.9  # Stub confidence

    def is_cjk(self, text: str) -> bool:
        return self.detect(text) in ("zh", "ja", "ko")
