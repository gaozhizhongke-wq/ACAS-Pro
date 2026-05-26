"""ACAS Pro - RSS Collector v2"""
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from ..core.config_v2 import AppConfig


class RSSCollector:
    """RSS collector - testable with DI"""
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or AppConfig.load()
        self._feeds: List[str] = []
        self._articles: List[Dict[str, Any]] = []
    
    def add_feed(self, url: str) -> bool:
        """Add feed"""
        self._feeds.append(url)
        return True
    
    def fetch_articles(self) -> Tuple[bool, List[Dict[str, Any]]]:
        """Fetch articles"""
        # Mock implementation
        articles = [
            {
                "title": f"Article from {url}",
                "url": url,
                "published": datetime.now(timezone.utc).isoformat()
            }
            for url in self._feeds
        ]
        self._articles.extend(articles)
        return True, articles
    
    def get_articles(self) -> List[Dict[str, Any]]:
        """Get articles"""
        return self._articles.copy()
    
    def clear(self) -> None:
        """Clear articles"""
        self._articles.clear()


# Alias for backward compatibility
RSSCollectorV2 = RSSCollector
