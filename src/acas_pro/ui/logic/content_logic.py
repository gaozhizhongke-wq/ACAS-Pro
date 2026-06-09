#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ACAS Pro - Content Logic Module"""
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Optional, Any
from datetime import datetime


class Platform(Enum):
    DOUYIN = "douyin"
    KUAISHOU = "kuaishou"
    XIAOHONGSHU = "xiaohongshu"
    BILIBILI = "bilibili"
    WECHAT = "wechat"
    WEIBO = "weibo"


class ContentStyle(Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    EMOTIONAL = "emotional"
    HUMOROUS = "humorous"
    EDUCATIONAL = "educational"


@dataclass
class TrendItem:
    id: str
    title: str
    author: str
    platform: Platform
    views: int
    likes: int
    comments: int
    viral_score: float
    timestamp: datetime


@dataclass
class ContentTemplate:
    name: str
    platform: Platform
    duration: int
    style: ContentStyle = ContentStyle.CASUAL
    tags: List[str] = None


@dataclass
class GeneratedScript:
    title: str
    content: str
    platform: Platform
    style: ContentStyle
    word_count: int
    estimated_duration: int
    keywords: List[str]


class ContentCreationLogic:
    """Content creation business logic"""

    def __init__(self) -> None:
        self._trends: List[TrendItem] = []

    def fetch_trends(self, platform: Optional[Platform] = None, limit: int = 20) -> List[TrendItem]:
        """Fetch trending content"""
        trends = self._generate_mock_trends(platform, limit)
        if platform:
            trends = [t for t in trends if t.platform == platform]
        return trends[:limit]

    def analyze_trend(self, trend_id: str) -> Dict[str, Any]:
        """Analyze a specific trend"""
        trend = next((t for t in self._trends if t.id == trend_id), None)
        if not trend:
            return {}
        return {
            "viral_factors": self._analyze_viral_factors(trend),
            "target_audience": self._infer_audience(trend),
            "content_gaps": self._find_content_gaps(trend),
            "recommendations": self._generate_recommendations(trend),
        }

    def generate_script(
        self,
        topic: str,
        platform: Platform,
        style: ContentStyle,
        duration: int = 60,
        keywords: Optional[List[str]] = None,
    ) -> GeneratedScript:
        """Generate content script"""
        content = self._generate_script_content(topic, style, duration)
        return GeneratedScript(
            title=f"{topic} - {style.value}",
            content=content,
            platform=platform,
            style=style,
            word_count=len(content.split()),
            estimated_duration=duration,
            keywords=keywords or [topic],
        )

    def get_templates(self, platform: Optional[Platform] = None) -> List[ContentTemplate]:
        """Get content templates"""
        templates = [
            ContentTemplate(name="Product Demo", platform=Platform.DOUYIN, duration=60),
            ContentTemplate(name="Lifestyle Vlog", platform=Platform.XIAOHONGSHU, duration=180),
            ContentTemplate(name="Tutorial Series", platform=Platform.BILIBILI, duration=600),
        ]
        if platform:
            templates = [t for t in templates if t.platform == platform]
        return templates

    def optimize_script(self, script: GeneratedScript, target_platform: Platform) -> GeneratedScript:
        """Optimize script for target platform"""
        max_durations = {Platform.DOUYIN: 60, Platform.KUAISHOU: 120, Platform.XIAOHONGSHU: 120}
        max_duration = max_durations.get(target_platform, script.estimated_duration)
        duration = min(script.estimated_duration, max_duration)
        return GeneratedScript(
            title=script.title,
            content=f"[Optimized for {target_platform.value}]\n{script.content}",
            platform=target_platform,
            style=script.style,
            word_count=script.word_count,
            estimated_duration=duration,
            keywords=script.keywords,
        )

    def _generate_mock_trends(self, platform: Optional[Platform], limit: int) -> List[TrendItem]:
        """Generate mock trend data"""
        if len(self._trends) < limit:
            platforms = list(Platform)
            for i in range(len(self._trends), limit):
                p = platforms[i % len(platforms)]
                self._trends.append(
                    TrendItem(
                        id=f"trend-{i}",
                        title=f"趋势话题 #{i+1}",
                        author=f"user{i}",
                        platform=p,
                        views=100000 + i * 50000,
                        likes=5000 + i * 2000,
                        comments=500 + i * 100,
                        viral_score=80 + i * 2,
                        timestamp=datetime.now(),
                    )
                )
        return self._trends[:limit]

    def _analyze_viral_factors(self, trend: TrendItem) -> List[str]:
        """Analyze viral factors"""
        factors = []
        if trend.views > 1000000:
            factors.append("高播放量")
        if trend.likes / trend.views > 0.05:
            factors.append("高点赞率")
        if trend.comments > 1000:
            factors.append("高互动率")
        return factors

    def _infer_audience(self, trend: TrendItem) -> str:
        """Infer target audience"""
        return "18-35岁年轻用户"

    def _find_content_gaps(self, trend: TrendItem) -> List[str]:
        """Find content gaps"""
        return ["深度解析", "实操教程", "对比评测"]

    def _generate_recommendations(self, trend: TrendItem) -> List[str]:
        """Generate content recommendations"""
        return [
            f"基于{trend.author}的内容建议",
            "抓住热点话题",
            "突出差异化特点",
        ]

    def _generate_script_content(self, topic: str, style: ContentStyle, duration: int) -> str:
        """Generate script content"""
        return f"关于{topic}的{style.value}内容，时长{duration}秒"
