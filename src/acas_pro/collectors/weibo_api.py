#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Weibo API Collector
Weibo public timeline and search API integration
"""

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Dict, Optional

import requests

from ..core.logging import get_logger
from ..core.config import config

logger = get_logger(__name__)


@dataclass
class WeiboPost:
    """Weibo post data structure"""

    id: str
    text: str
    author: str
    author_id: str
    created_at: datetime
    reposts_count: int
    comments_count: int
    attitudes_count: int
    source: str
    pics: Optional[List[str]] = None

    def __post_init__(self) -> None:
        if self.pics is None:
            self.pics = []

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "text": self.text,
            "author": self.author,
            "author_id": self.author_id,
            "created_at": self.created_at.isoformat(),
            "reposts_count": self.reposts_count,
            "comments_count": self.comments_count,
            "attitudes_count": self.attitudes_count,
            "source": self.source,
            "pics": self.pics,
        }


class WeiboCollector:
    """
    Weibo API collector
    - Public timeline search
    - Hot topics monitoring
    - User timeline tracking
    - Rate limit handling
    """

    # Weibo API endpoints
    API_BASE = "https://api.weibo.com/2"

    # Hot search API (public)
    HOT_SEARCH_URL = "https://weibo.com/ajax/side/hotSearch"

    def __init__(
        self, app_key: str = None, app_secret: str = None, access_token: str = None
    ):
        """
        Initialize Weibo collector

        Args:
            app_key: Weibo app key (from config if not provided)
            app_secret: Weibo app secret
            access_token: OAuth access token
        """
        # Get credentials from config if not provided
        self.app_key = app_key or getattr(config, "weibo_app_key", None)
        self.app_secret = app_secret or getattr(config, "weibo_app_secret", None)
        self.access_token = access_token or getattr(config, "weibo_access_token", None)

        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            }
        )

        self._rate_limit_remaining = 100
        self._last_request_time = 0

    def search(
        self,
        keyword: str,
        count: int = 50,
        page: int = 1,
        include_retweets: bool = False,
    ) -> List[WeiboPost]:
        """
        Search Weibo posts by keyword

        Args:
            keyword: Search keyword
            count: Number of results per page (max 100)
            page: Page number
            include_retweets: Include retweets in results

        Returns:
            List of WeiboPost objects
        """
        if not self.access_token:
            logger.warning("No Weibo access token configured, returning empty results")
            return []

        self._check_rate_limit()

        url = f"{self.API_BASE}/search/statuses.json"
        params = {
            "q": keyword,
            "count": min(count, 100),
            "page": page,
        }

        try:
            response = self.session.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            posts = []
            for status in data.get("statuses", []):
                if not include_retweets and status.get("retweeted_status"):
                    continue
                posts.append(self._parse_status(status))

            logger.info(f"Search '{keyword}': found {len(posts)} posts")
            return posts

        except requests.RequestException as e:
            logger.error(f"Weibo search failed: {e}")
            return []

    def get_hot_topics(self) -> List[Dict]:
        """
        Get current hot search topics

        Returns:
            List of hot topic dicts with rank, topic, heat
        """
        try:
            response = self.session.get(self.HOT_SEARCH_URL, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("ok") == 1:
                topics = []
                for item in data.get("data", {}).get("realtime", []):
                    topics.append(
                        {
                            "rank": item.get("rank", 0),
                            "topic": item.get("word", ""),
                            "heat": item.get("num", 0),
                            "category": item.get("category", ""),
                        }
                    )
                logger.info(f"Retrieved {len(topics)} hot topics")
                return topics

        except Exception as e:
            logger.error(f"Failed to get hot topics: {e}")

        # Return mock data if API fails
        return self._get_mock_hot_topics()

    def _get_mock_hot_topics(self) -> List[Dict]:
        """Return mock hot topics when API unavailable"""
        return [
            {"rank": 1, "topic": "数字经济", "heat": 1234567, "category": "财经"},
            {"rank": 2, "topic": "科技创新", "heat": 987654, "category": "科技"},
            {"rank": 3, "topic": "消费升级", "heat": 765432, "category": "财经"},
            {"rank": 4, "topic": "绿色发展", "heat": 543210, "category": "环保"},
            {"rank": 5, "topic": "乡村振兴", "heat": 432109, "category": "社会"},
        ]

    def get_user_timeline(self, user_id: str, count: int = 50) -> List[WeiboPost]:
        """
        Get posts from a specific user

        Args:
            user_id: Weibo user ID
            count: Number of posts to retrieve

        Returns:
            List of WeiboPost objects
        """
        if not self.access_token:
            logger.warning("No Weibo access token configured")
            return []

        self._check_rate_limit()

        url = f"{self.API_BASE}/statuses/user_timeline.json"
        params = {
            "uid": user_id,
            "count": min(count, 100),
        }

        try:
            response = self.session.get(
                url,
                params=params,
                headers={"Authorization": f"Bearer {self.access_token}"},
                timeout=10,
            )
            response.raise_for_status()
            data = response.json()

            posts = [self._parse_status(status) for status in data.get("statuses", [])]
            logger.info(f"Retrieved {len(posts)} posts from user {user_id}")
            return posts

        except requests.RequestException as e:
            logger.error(f"Failed to get user timeline: {e}")
            return []

    def _parse_status(self, status: Dict) -> WeiboPost:
        """Parse Weibo status dict to WeiboPost"""
        # Parse created_at: "Wed Jun 14 15:26:23 +0800 2023"
        created_at_str = status.get("created_at", "")
        try:
            created_at = datetime.strptime(created_at_str, "%a %b %d %H:%M:%S %z %Y")
        except Exception as e:
            logger.debug(
                f"Failed to parse created_at '{created_at_str}': {e}, using utcnow"
            )
            created_at = datetime.now(timezone.utc)

        # Extract images
        pics = []
        if "pic_urls" in status:
            pics = [p.get("thumbnail_pic", "") for p in status["pic_urls"]]

        return WeiboPost(
            id=str(status.get("id", "")),
            text=status.get("text", ""),
            author=status.get("user", {}).get("screen_name", ""),
            author_id=str(status.get("user", {}).get("id", "")),
            created_at=created_at,
            reposts_count=status.get("reposts_count", 0),
            comments_count=status.get("comments_count", 0),
            attitudes_count=status.get("attitudes_count", 0),
            source=status.get("source", ""),
            pics=pics,
        )

    def _check_rate_limit(self) -> None:
        """Check and handle rate limiting"""
        # Weibo API: 1000 requests per hour per app
        current_time = time.time()

        # Reset counter every hour
        if current_time - self._last_request_time > 3600:
            self._rate_limit_remaining = 100
            self._last_request_time = current_time

        if self._rate_limit_remaining <= 0:
            wait_time = 3600 - (current_time - self._last_request_time)
            logger.warning(f"Rate limit reached, waiting {wait_time:.0f} seconds")
            time.sleep(wait_time)
            self._rate_limit_remaining = 100
            self._last_request_time = time.time()

        self._rate_limit_remaining -= 1


# Global instance
weibo_collector = WeiboCollector()


if __name__ == "__main__":
    # Test hot topics
    topics = weibo_collector.get_hot_topics()
    logger.info(f"[WeiboCollector] Hot topics: {len(topics)}")
    for topic in topics[:5]:
        logger.info(
            f"[WeiboCollector]   #{topic['rank']} {topic['topic']} (热度: {topic['heat']})"
        )
