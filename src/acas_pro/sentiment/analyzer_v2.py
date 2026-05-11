"""ACAS Pro - Sentiment Analyzer v2"""
from typing import Dict, Any, List, Tuple

from ..core.config_v2 import AppConfig


class SentimentAnalyzer:
    """Sentiment analyzer - testable with DI"""
    
    def __init__(self, config=None):
        self.config = config or AppConfig.load()
        self._positive_words = {'good', 'great', 'excellent', 'amazing', 'love', 'best'}
        self._negative_words = {'bad', 'terrible', 'awful', 'hate', 'worst', 'poor'}
    
    def analyze(self, text: str) -> Tuple[bool, Dict[str, Any]]:
        """Analyze sentiment"""
        words = text.lower().split()
        
        positive_count = sum(1 for w in words if w in self._positive_words)
        negative_count = sum(1 for w in words if w in self._negative_words)
        
        total = positive_count + negative_count
        if total == 0:
            sentiment = "neutral"
            score = 0.5
        elif positive_count > negative_count:
            sentiment = "positive"
            score = positive_count / total
        else:
            sentiment = "negative"
            score = negative_count / total
        
        return True, {
            "sentiment": sentiment,
            "score": score,
            "positive_words": positive_count,
            "negative_words": negative_count
        }
    
    def batch_analyze(self, texts: List[str]) -> Tuple[bool, List[Dict[str, Any]]]:
        """Batch analyze"""
        results = []
        for text in texts:
            success, result = self.analyze(text)
            if success:
                results.append(result)
        return True, results
