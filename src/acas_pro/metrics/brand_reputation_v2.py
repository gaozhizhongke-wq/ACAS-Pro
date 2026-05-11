"""ACAS Pro - Brand Reputation v2"""
from typing import Dict, Any, List, Optional, Tuple

from ..core.config_v2 import AppConfig


class BrandReputation:
    """Brand reputation - testable with DI"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load()
        self._scores: Dict[str, float] = {}
    
    def add_score(self, platform: str, score: float) -> bool:
        """Add score"""
        self._scores[platform] = score
        return True
    
    def get_score(self, platform: str) -> float:
        """Get score"""
        return self._scores.get(platform, 0.0)
    
    def get_average(self) -> float:
        """Get average"""
        if not self._scores:
            return 0.0
        return sum(self._scores.values()) / len(self._scores)
    
    def get_all(self) -> Dict[str, float]:
        """Get all scores"""
        return self._scores.copy()
