"""Xiaohongshu Platform API - Stub implementation."""


class XiaohongshuAPI:
    """Xiaohongshu API client - Stub implementation."""

    def __init__(self, api_key: str = "", **kwargs):
        self.api_key = api_key

    def get_post_info(self, post_id: str) -> dict:
        """Get post information."""
        return {"id": post_id, "title": "", "like_count": 0}

    def search_posts(self, keyword: str, limit: int = 100) -> list:
        """Search posts by keyword."""
        return []

    def get_trending(self) -> list:
        """Get trending posts."""
        return []
