#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Brand Reputation Metrics Calculator
Calculate brand reputation scores from sentiment analysis results
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Optional
from collections import defaultdict
from enum import Enum

from ..core.logging import get_logger

logger = get_logger(__name__)


class MetricPeriod(Enum):
    """Metric calculation period"""

    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass
class SentimentArticle:
    """Article with sentiment for metric calculation"""

    id: str
    title: str
    content: str
    source: str
    published_at: datetime
    sentiment_score: float  # -1 to 1
    sentiment_level: str  # very_negative, negative, neutral, positive, very_positive
    platform: str = "unknown"
    category: str = "general"


@dataclass
class ReputationScore:
    """Brand reputation score result"""

    score: float  # 0-100
    grade: str  # A, B, C, D, F
    total_articles: int
    positive_count: int
    negative_count: int
    neutral_count: int
    positive_ratio: float
    negative_ratio: float
    sentiment_avg: float
    trend: str  # improving, stable, declining
    platform_breakdown: Dict[str, float] = field(default_factory=dict)
    category_breakdown: Dict[str, float] = field(default_factory=dict)
    calculated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.calculated_at is None:
            self.calculated_at = datetime.now(timezone.utc)

    def to_dict(self) -> Dict:
        return {
            "score": round(self.score, 1),
            "grade": self.grade,
            "total_articles": self.total_articles,
            "positive_count": self.positive_count,
            "negative_count": self.negative_count,
            "neutral_count": self.neutral_count,
            "positive_ratio": round(self.positive_ratio, 3),
            "negative_ratio": round(self.negative_ratio, 3),
            "sentiment_avg": round(self.sentiment_avg, 3),
            "trend": self.trend,
            "platform_breakdown": {
                k: round(v, 1) for k, v in self.platform_breakdown.items()
            },
            "category_breakdown": {
                k: round(v, 1) for k, v in self.category_breakdown.items()
            },
            "calculated_at": self.calculated_at.isoformat(),
        }


@dataclass
class ReputationTrend:
    """Reputation trend over time"""

    period: MetricPeriod
    data_points: List[Dict]  # [{date, score, count}]
    change_rate: float  # percentage change
    direction: str  # up, down, stable

    def to_dict(self) -> Dict:
        return {
            "period": self.period.value,
            "data_points": self.data_points,
            "change_rate": round(self.change_rate, 2),
            "direction": self.direction,
        }


class BrandReputationCalculator:
    """
    Brand reputation metrics calculator
    - Overall reputation score
    - Platform breakdown
    - Category breakdown
    - Trend analysis
    - Alert thresholds
    """

    # Sentiment level weights
    SENTIMENT_WEIGHTS = {
        "very_positive": 1.0,
        "positive": 0.6,
        "neutral": 0.0,
        "negative": -0.6,
        "very_negative": -1.0,
    }

    # Grade thresholds
    GRADE_THRESHOLDS = [
        (90, "A", "优秀"),
        (80, "B", "良好"),
        (70, "C", "一般"),
        (60, "D", "较差"),
        (0, "F", "危险"),
    ]

    # Platform weights (importance)
    PLATFORM_WEIGHTS = {
        "weibo": 1.2,
        "douyin": 1.1,
        "xiaohongshu": 1.0,
        "bilibili": 0.9,
        "wechat": 1.0,
        "news": 0.8,
        "other": 0.7,
    }

    def __init__(self):
        self._history: List[ReputationScore] = []
        self._max_history = 100

    def calculate(
        self, articles: List[SentimentArticle], previous_score: Optional[float] = None
    ) -> ReputationScore:
        """
        Calculate brand reputation score

        Args:
            articles: List of articles with sentiment
            previous_score: Previous period score for trend

        Returns:
            ReputationScore object
        """
        if not articles:
            return self._empty_score()

        # Count by sentiment level
        sentiment_counts = defaultdict(int)
        for article in articles:
            sentiment_counts[article.sentiment_level] += 1

        positive_count = (
            sentiment_counts["very_positive"] + sentiment_counts["positive"]
        )
        negative_count = (
            sentiment_counts["very_negative"] + sentiment_counts["negative"]
        )
        neutral_count = sentiment_counts["neutral"]
        total = len(articles)

        # Calculate weighted sentiment score
        weighted_sum = 0
        weight_total = 0

        for article in articles:
            # Base sentiment weight
            sentiment_weight = self.SENTIMENT_WEIGHTS.get(article.sentiment_level, 0)

            # Platform weight
            platform_weight = self.PLATFORM_WEIGHTS.get(article.platform.lower(), 0.7)

            # Combined weight
            combined_weight = sentiment_weight * platform_weight
            weighted_sum += combined_weight
            weight_total += platform_weight

        # Normalize to 0-100 scale
        if weight_total > 0:
            normalized = weighted_sum / weight_total  # -1 to 1
            score = 50 + (normalized * 50)  # 0 to 100
        else:
            score = 50

        # Clamp score
        score = max(0, min(100, score))

        # Determine grade
        grade = "F"
        for threshold, g, _ in self.GRADE_THRESHOLDS:
            if score >= threshold:
                grade = g
                break

        # Calculate ratios
        positive_ratio = positive_count / total if total > 0 else 0
        negative_ratio = negative_count / total if total > 0 else 0

        # Average sentiment score
        sentiment_avg = (
            sum(a.sentiment_score for a in articles) / total if total > 0 else 0
        )

        # Determine trend
        if previous_score is not None:
            diff = score - previous_score
            if diff > 2:
                trend = "improving"
            elif diff < -2:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Platform breakdown
        platform_breakdown = self._calculate_platform_breakdown(articles)

        # Category breakdown
        category_breakdown = self._calculate_category_breakdown(articles)

        result = ReputationScore(
            score=score,
            grade=grade,
            total_articles=total,
            positive_count=positive_count,
            negative_count=negative_count,
            neutral_count=neutral_count,
            positive_ratio=positive_ratio,
            negative_ratio=negative_ratio,
            sentiment_avg=sentiment_avg,
            trend=trend,
            platform_breakdown=platform_breakdown,
            category_breakdown=category_breakdown,
        )

        # Store in history
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        logger.info(f"Reputation score: {score:.1f} ({grade}), trend: {trend}")
        return result

    def _calculate_platform_breakdown(
        self, articles: List[SentimentArticle]
    ) -> Dict[str, float]:
        """Calculate reputation score by platform"""
        platform_articles = defaultdict(list)

        for article in articles:
            platform_articles[article.platform.lower()].append(article)

        breakdown = {}
        for platform, platform_list in platform_articles.items():
            if platform_list:
                avg_sentiment = sum(a.sentiment_score for a in platform_list) / len(
                    platform_list
                )
                breakdown[platform] = 50 + (avg_sentiment * 50)

        return breakdown

    def _calculate_category_breakdown(
        self, articles: List[SentimentArticle]
    ) -> Dict[str, float]:
        """Calculate reputation score by category"""
        category_articles = defaultdict(list)

        for article in articles:
            category_articles[article.category].append(article)

        breakdown = {}
        for category, category_list in category_articles.items():
            if category_list:
                avg_sentiment = sum(a.sentiment_score for a in category_list) / len(
                    category_list
                )
                breakdown[category] = 50 + (avg_sentiment * 50)

        return breakdown

    def _empty_score(self) -> ReputationScore:
        """Return empty reputation score"""
        return ReputationScore(
            score=50,
            grade="C",
            total_articles=0,
            positive_count=0,
            negative_count=0,
            neutral_count=0,
            positive_ratio=0,
            negative_ratio=0,
            sentiment_avg=0,
            trend="stable",
        )

    def calculate_trend(
        self, period: MetricPeriod = MetricPeriod.DAY, days: int = 7
    ) -> ReputationTrend:
        """
        Calculate reputation trend over time

        Args:
            period: Aggregation period
            days: Number of days to analyze

        Returns:
            ReputationTrend object
        """
        if len(self._history) < 2:
            return ReputationTrend(
                period=period, data_points=[], change_rate=0, direction="stable"
            )

        # Get relevant history
        recent = self._history[-days:] if len(self._history) >= days else self._history

        data_points = [
            {
                "date": score.calculated_at.isoformat(),
                "score": round(score.score, 1),
                "count": score.total_articles,
            }
            for score in recent
        ]

        # Calculate change rate
        if len(recent) >= 2:
            first_score = recent[0].score
            last_score = recent[-1].score
            if first_score > 0:
                change_rate = ((last_score - first_score) / first_score) * 100
            else:
                change_rate = 0
        else:
            change_rate = 0

        # Determine direction
        if change_rate > 5:
            direction = "up"
        elif change_rate < -5:
            direction = "down"
        else:
            direction = "stable"

        return ReputationTrend(
            period=period,
            data_points=data_points,
            change_rate=change_rate,
            direction=direction,
        )

    def get_alert_status(self, score: ReputationScore) -> Dict:
        """
        Get alert status based on reputation score

        Args:
            score: Current reputation score

        Returns:
            Alert status dict
        """
        alerts = []

        # Score threshold alerts
        if score.score < 60:
            alerts.append(
                {
                    "level": "critical",
                    "message": f"品牌口碑分数过低 ({score.score:.1f})，需要立即关注",
                    "recommendation": "分析负面舆情来源，制定应对策略",
                }
            )
        elif score.score < 70:
            alerts.append(
                {
                    "level": "warning",
                    "message": f"品牌口碑分数偏低 ({score.score:.1f})",
                    "recommendation": "关注负面舆情动态，优化内容策略",
                }
            )

        # Negative ratio alert
        if score.negative_ratio > 0.3:
            alerts.append(
                {
                    "level": "warning",
                    "message": f"负面舆情占比过高 ({score.negative_ratio:.1%})",
                    "recommendation": "分析负面舆情类型，针对性处理",
                }
            )

        # Trend alert
        if score.trend == "declining":
            alerts.append(
                {
                    "level": "warning",
                    "message": "品牌口碑呈下降趋势",
                    "recommendation": "对比历史数据，找出下降原因",
                }
            )

        return {
            "has_alerts": len(alerts) > 0,
            "alerts": alerts,
            "overall_status": "critical"
            if score.score < 60
            else "warning"
            if score.score < 70
            else "normal",
        }

    def get_summary(self, score: ReputationScore) -> str:
        """Get human-readable summary"""
        grade_desc = dict(self.GRADE_THRESHOLDS).get(score.grade, "未知")

        summary = f"""
品牌口碑报告
============
综合评分: {score.score:.1f} 分 ({grade_desc})
舆情总量: {score.total_articles} 条
正面舆情: {score.positive_count} 条 ({score.positive_ratio:.1%})
负面舆情: {score.negative_count} 条 ({score.negative_ratio:.1%})
中性舆情: {score.neutral_count} 条
趋势判断: {score.trend}

平台分布:
"""
        for platform, platform_score in score.platform_breakdown.items():
            summary += f"  - {platform}: {platform_score:.1f} 分\n"

        return summary


# Global instance
reputation_calculator = BrandReputationCalculator()


if __name__ == "__main__":
    # Test with sample data
    from datetime import datetime

    sample_articles = [
        SentimentArticle(
            id="1",
            title="产品体验很好",
            content="...",
            source="weibo",
            published_at=datetime.now(timezone.utc),
            sentiment_score=0.8,
            sentiment_level="positive",
            platform="weibo",
            category="product",
        ),
        SentimentArticle(
            id="2",
            title="物流太慢了",
            content="...",
            source="douyin",
            published_at=datetime.now(timezone.utc),
            sentiment_score=-0.6,
            sentiment_level="negative",
            platform="douyin",
            category="service",
        ),
        SentimentArticle(
            id="3",
            title="质量不错",
            content="...",
            source="xiaohongshu",
            published_at=datetime.now(timezone.utc),
            sentiment_score=0.5,
            sentiment_level="positive",
            platform="xiaohongshu",
            category="product",
        ),
    ]

    score = reputation_calculator.calculate(sample_articles)
    logger.info(f"[BrandReputation] {reputation_calculator.get_summary(score)}")
