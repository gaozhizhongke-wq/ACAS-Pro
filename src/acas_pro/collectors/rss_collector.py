#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - RSS News Collector
Multi-source RSS feed aggregation for market intelligence
"""

import feedparser
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RSSArticle:
    """RSS article data structure"""
    title: str
    content: str
    summary: str
    source: str
    source_url: str
    published_at: datetime
    language: str = "zh"
    tags: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "content": self.content,
            "summary": self.summary,
            "source": self.source,
            "source_url": self.source_url,
            "published_at": self.published_at.isoformat(),
            "language": self.language,
            "tags": self.tags
        }


class RSSCollector:
    """
    Multi-source RSS news collector
    - Concurrent feed fetching
    - Auto language detection
    - Deduplication
    - Error resilience
    """
    
    # Default RSS sources (Chinese news)
    DEFAULT_SOURCES = {
        # 财经新闻
        "sina_finance": "https://news.sina.com.cn/rss/finance.xml",
        "qq_finance": "https://news.qq.com/new/rss/finance.xml",
        "ifeng_finance": "https://finance.ifeng.com/rss/index.xml",
        
        # 科技新闻
        "36kr": "https://36kr.com/feed",
        "ithome": "https://www.ithome.com/rss/",
        
        # 综合新闻
        "people": "http://www.people.com.cn/rss/news.xml",
        "xinhua": "http://www.xinhuanet.com/politics/news_politics.xml",
        
        # 行业新闻
        "ftchinese": "http://www.ftchinese.com/rss/news",
        "caixin": "https://rsshub.app/caixin/finance",
    }
    
    # International sources
    INTERNATIONAL_SOURCES = {
        "reuters_business": "https://www.reuters.com/rssFeed/businessNews",
        "bloomberg": "https://rsshub.app/bloomberg/markets",
        "bbc_business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    }
    
    def __init__(self, custom_sources: Dict[str, str] = None, timeout: int = 30):
        """
        Initialize RSS collector
        
        Args:
            custom_sources: Additional RSS sources {name: url}
            timeout: Request timeout in seconds
        """
        self.sources = {**self.DEFAULT_SOURCES, **self.INTERNATIONAL_SOURCES}
        if custom_sources:
            self.sources.update(custom_sources)
        self.timeout = timeout
        self._cache: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(minutes=15)
    
    def collect(
        self,
        sources: List[str] = None,
        hours_back: int = 24,
        max_per_source: int = 50,
        include_international: bool = True
    ) -> List[RSSArticle]:
        """
        Collect articles from RSS feeds
        
        Args:
            sources: Specific sources to collect (None = all)
            hours_back: Only collect articles from last N hours
            max_per_source: Maximum articles per source
            include_international: Include international sources
        
        Returns:
            List of RSSArticle objects
        """
        # Determine which sources to use
        if sources:
            target_sources = {k: v for k, v in self.sources.items() if k in sources}
        else:
            target_sources = self.DEFAULT_SOURCES.copy()
            if include_international:
                target_sources.update(self.INTERNATIONAL_SOURCES)
        
        # Collect concurrently
        all_articles = []
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                executor.submit(self._fetch_feed, name, url): name
                for name, url in target_sources.items()
            }
            
            for future in as_completed(futures, timeout=self.timeout * len(target_sources)):
                source_name = futures[future]
                try:
                    articles = future.result()
                    # Filter by time
                    articles = [a for a in articles if a.published_at > cutoff_time]
                    # Limit per source
                    articles = articles[:max_per_source]
                    all_articles.extend(articles)
                    logger.info(f"Collected {len(articles)} articles from {source_name}")
                except Exception as e:
                    logger.error(f"Failed to collect from {source_name}: {e}")
        
        # Deduplicate by title similarity
        unique_articles = self._deduplicate(all_articles)
        
        # Sort by time
        unique_articles.sort(key=lambda x: x.published_at, reverse=True)
        
        logger.info(f"Total collected: {len(unique_articles)} unique articles")
        return unique_articles
    
    def _fetch_feed(self, source_name: str, url: str) -> List[RSSArticle]:
        """Fetch and parse a single RSS feed"""
        articles = []
        
        try:
            feed = feedparser.parse(url, timeout=self.timeout)
            
            if feed.bozo and feed.bozo_exception:
                logger.warning(f"Feed parse warning for {source_name}: {feed.bozo_exception}")
            
            # Detect language
            language = self._detect_language(feed.feed.get('title', ''))
            
            for entry in feed.entries:
                try:
                    # Parse publication time
                    published_at = self._parse_time(entry)
                    
                    # Extract content
                    content = entry.get('summary', '') or entry.get('description', '')
                    if hasattr(entry, 'content'):
                        content = entry.content[0].get('value', content)
                    
                    # Clean content
                    content = self._clean_content(content)
                    
                    article = RSSArticle(
                        title=entry.get('title', 'Untitled'),
                        content=content,
                        summary=content[:200] + "..." if len(content) > 200 else content,
                        source=feed.feed.get('title', source_name),
                        source_url=entry.get('link', ''),
                        published_at=published_at,
                        language=language,
                        tags=self._extract_tags(entry)
                    )
                    articles.append(article)
                    
                except Exception as e:
                    logger.debug(f"Failed to parse entry: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
        
        return articles
    
    def _parse_time(self, entry) -> datetime:
        """Parse publication time from entry"""
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            return datetime(*entry.published_parsed[:6])
        elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            return datetime(*entry.updated_parsed[:6])
        else:
            return datetime.now(timezone.utc)
    
    def _detect_language(self, text: str) -> str:
        """Detect language from text"""
        if not text:
            return "zh"
        # Check for Chinese characters
        chinese_ratio = sum(1 for c in text if '\u4e00' <= c <= '\u9fff') / len(text)
        return "zh" if chinese_ratio > 0.3 else "en"
    
    def _clean_content(self, content: str) -> str:
        """Clean HTML tags and normalize content"""
        import re
        # Remove HTML tags
        content = re.sub(r'<[^>]+>', '', content)
        # Normalize whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        return content
    
    def _extract_tags(self, entry) -> List[str]:
        """Extract tags from entry"""
        tags = []
        if hasattr(entry, 'tags') and entry.tags:
            tags = [tag.term for tag in entry.tags if hasattr(tag, 'term')]
        if hasattr(entry, 'category') and entry.category:
            tags.append(entry.category)
        return tags[:5]
    
    def _deduplicate(self, articles: List[RSSArticle]) -> List[RSSArticle]:
        """Remove duplicate articles by title similarity"""
        seen_titles = set()
        unique = []
        
        for article in articles:
            # Normalize title for comparison
            normalized = article.title.lower().strip()
            # Skip if very similar title seen
            if any(self._similarity(normalized, seen) > 0.8 for seen in seen_titles):
                continue
            seen_titles.add(normalized)
            unique.append(article)
        
        return unique
    
    def _similarity(self, s1: str, s2: str) -> float:
        """Calculate simple Jaccard similarity"""
        if not s1 or not s2:
            return 0.0
        words1 = set(s1)
        words2 = set(s2)
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        return intersection / union if union > 0 else 0.0
    
    def add_source(self, name: str, url: str):
        """Add a custom RSS source"""
        self.sources[name] = url
        logger.info(f"Added RSS source: {name}")
    
    def get_available_sources(self) -> List[str]:
        """Get list of available source names"""
        return list(self.sources.keys())


# Global instance
rss_collector = RSSCollector()


if __name__ == "__main__":
    # Test collection
    articles = rss_collector.collect(hours_back=48, max_per_source=10)
    print(f"Collected {len(articles)} articles")
    for article in articles[:5]:
        print(f"  [{article.source}] {article.title}")
