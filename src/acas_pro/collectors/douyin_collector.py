"""Douyin Collector - Stub implementation."""

from dataclasses import dataclass
from typing import List


@dataclass
class DouyinPost:
    """Douyin post data structure."""

    id: str
    title: str
    author: str
    play_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    share_count: int = 0
    create_time: str = ""


class DouyinCollector:
    """Douyin video collector - Stub implementation."""

    def __init__(self, api_key: str = "", **kwargs):
        self.api_key = api_key

    def collect(self, keyword: str, limit: int = 100) -> List[DouyinPost]:
        """Collect videos by keyword."""
        return []

    def get_trending(self) -> List[DouyinPost]:
        """Get trending videos."""
        return []
