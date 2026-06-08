#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Content Creation Business Logic
Extracted from ContentCreationPage for testability
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Callable, Any
from enum import Enum
from datetime import datetime


class ContentStyle(Enum):
    """Content style types"""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    HUMOROUS = "humorous"
    EMOTIONAL = "emotional"
    EDUCATIONAL = "educational"


class Platform(Enum):
    """Content platforms"""
    DOUYIN = "douyin"
    KUAISHOU = "kuaishou"
    XIAOHONGSHU = "xiaohongshu"
    BILIBILI = "bilibili"
    WEIBO = "weibo"


@dataclass
class TrendItem:
    """Trending content item"""
    id: str
    title: str
    author: str
    platform: Platform
    views: int
    likes: int
    comments: int
    viral_score: float
    timestamp: datetime
    url: str = ""


@dataclass
class ScriptTemplate:
    """Script template"""
    id: str
    name: str
    platform: Platform
    style: ContentStyle
    template: str
    estimated_duration: int  # seconds


@dataclass
class GeneratedScript:
    """Generated script result"""
    title: str
    content: str
    platform: Platform
    style: ContentStyle
    word_count: int
    estimated_duration: int
    keywords: List[str]


class ContentCreationLogic:
    """Content creation business logic"""
    
    def __init__(self, trend_service=None, script_service=None) -> Any:
        self.trend_service = trend_service
        self.script_service = script_service
        self._trends: List[TrendItem] = []
        self._templates: List[ScriptTemplate] = []
    
    def fetch_trends(self, platform: Optional[Platform] = None, limit: int = 20) -> List[TrendItem]:
        """Fetch trending content"""
        # Mock data for testing
        self._trends = self._generate_mock_trends(platform, limit)
        return self._trends
    
    def analyze_trend(self, trend_id: str) -> Dict:
        """Analyze a trend item"""
        trend = next((t for t in self._trends if t.id == trend_id), None)
        if not trend:
            return {}
        
        return {
            "viral_factors": self._analyze_viral_factors(trend),
            "target_audience": self._infer_audience(trend),
            "content_gaps": self._find_content_gaps(trend),
            "recommendations": self._generate_recommendations(trend),
        }
    
    def generate_script(self, 
                       topic: str,
                       platform: Platform,
                       style: ContentStyle,
                       duration: int = 60,
                       keywords: Optional[List[str]] = None) -> GeneratedScript:
        """Generate content script"""
        # Mock generation
        content = self._generate_mock_script(topic, platform, style, duration)
        
        return GeneratedScript(
            title=f"{topic} - {style.value}",
            content=content,
            platform=platform,
            style=style,
            word_count=len(content.split()),
            estimated_duration=duration,
            keywords=keywords or [topic],
        )
    
    def get_templates(self, platform: Optional[Platform] = None) -> List[ScriptTemplate]:
        """Get available script templates"""
        templates = self._load_templates()
        if platform:
            templates = [t for t in templates if t.platform == platform]
        return templates
    
    def optimize_script(self, script: GeneratedScript, target_platform: Platform) -> GeneratedScript:
        """Optimize script for specific platform"""
        # Platform-specific optimizations
        optimizations = {
            Platform.DOUYIN: {"max_duration": 60, "hook_style": "fast"},
            Platform.KUAISHOU: {"max_duration": 120, "hook_style": "emotional"},
            Platform.XIAOHONGSHU: {"max_duration": 300, "hook_style": "lifestyle"},
        }
        
        opt = optimizations.get(target_platform, {})
        
        return GeneratedScript(
            title=script.title,
            content=f"[Optimized for {target_platform.value}]\n{script.content}",
            platform=target_platform,
            style=script.style,
            word_count=script.word_count,
            estimated_duration=min(script.estimated_duration, opt.get("max_duration", 60)),
            keywords=script.keywords,
        )
    
    def _generate_mock_trends(self, platform: Optional[Platform], limit: int) -> List[TrendItem]:
        """Generate mock trend data"""
        platforms = [platform] if platform else list(Platform)
        trends = []
        
        for i in range(min(limit, 20)):
            p = platforms[i % len(platforms)]
            trends.append(TrendItem(
                id=f"trend-{i}",
                title=f"热门话题 #{i+1}",
                author=f"user{i}",
                platform=p,
                views=100000 + i * 50000,
                likes=5000 + i * 2000,
                comments=500 + i * 100,
                viral_score=80 + i * 2,
                timestamp=datetime.now(),
            ))
        
        return trends
    
    def _analyze_viral_factors(self, trend: TrendItem) -> List[str]:
        """Analyze why content went viral"""
        factors = []
        if trend.views > 1000000:
            factors.append("高曝光量")
        if trend.likes / trend.views > 0.05:
            factors.append("高互动率")
        if trend.comments > 1000:
            factors.append("话题性强")
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
            f"参考 {trend.author} 的内容结构",
            "添加个人观点或经验",
            "使用更具吸引力的标题",
        ]
    
    def _generate_mock_script(self, topic: str, platform: Platform, style: ContentStyle, duration: int) -> str:
        """Generate mock script content"""
        return f"""
【{topic}】

开头 (0-5秒):
大家好！今天给大家分享{topic}...

正文 (5-{duration-5}秒):
1. 第一点内容
2. 第二点内容  
3. 第三点内容

结尾 ({duration-5}-{duration}秒):
喜欢的话记得点赞关注！
"""
    
    def _load_templates(self) -> List[ScriptTemplate]:
        """Load script templates"""
        return [
            ScriptTemplate(
                id="tpl-1",
                name="产品种草",
                platform=Platform.XIAOHONGSHU,
                style=ContentStyle.CASUAL,
                template="开头+产品+体验+总结",
                estimated_duration=60,
            ),
            ScriptTemplate(
                id="tpl-2",
                name="知识分享",
                platform=Platform.DOUYIN,
                style=ContentStyle.EDUCATIONAL,
                template="问题+解答+案例+总结",
                estimated_duration=45,
            ),
        ]
