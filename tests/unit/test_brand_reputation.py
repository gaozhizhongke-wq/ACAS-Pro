#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for metrics/brand_reputation.py"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from acas_pro.metrics.brand_reputation import (
    MetricPeriod, SentimentArticle, ReputationScore, ReputationTrend,
    BrandReputationCalculator
)


class TestSentimentArticle:
    def test_create(self):
        article = SentimentArticle(
            id="a1", title="Test", content="Content",
            source="weibo", published_at=datetime.now(timezone.utc),
            sentiment_score=0.8, sentiment_level="positive",
            platform="weibo", category="product"
        )
        assert article.id == "a1"
        assert article.sentiment_score == 0.8


class TestReputationScore:
    def test_post_init(self):
        score = ReputationScore(
            score=75.5, grade="B", total_articles=10,
            positive_count=5, negative_count=2, neutral_count=3,
            positive_ratio=0.5, negative_ratio=0.2,
            sentiment_avg=0.3, trend="stable"
        )
        assert score.calculated_at is not None

    def test_to_dict(self):
        score = ReputationScore(
            score=75.5, grade="B", total_articles=10,
            positive_count=5, negative_count=2, neutral_count=3,
            positive_ratio=0.5, negative_ratio=0.2,
            sentiment_avg=0.3, trend="stable",
            platform_breakdown={"weibo": 80.0},
            category_breakdown={"product": 75.0}
        )
        d = score.to_dict()
        assert d["score"] == 75.5
        assert d["grade"] == "B"
        assert d["trend"] == "stable"
        assert "calculated_at" in d


class TestBrandReputationCalculator:
    def setup_method(self):
        self.calc = BrandReputationCalculator()

    def test_init(self):
        assert self.calc is not None
        assert len(self.calc._history) == 0

    def test_calculate_empty(self):
        result = self.calc.calculate([])
        assert result.score == 50
        assert result.grade == "C"
        assert result.total_articles == 0

    def test_calculate_positive(self):
        articles = [
            SentimentArticle("a1", "Good", "Nice", "weibo", datetime.now(timezone.utc), 0.8, "positive", "weibo", "product"),
            SentimentArticle("a2", "Great", "Awesome", "douyin", datetime.now(timezone.utc), 0.9, "very_positive", "douyin", "service"),
            SentimentArticle("a3", "OK", "Fine", "weibo", datetime.now(timezone.utc), 0.1, "neutral", "weibo", "product")
        ]
        result = self.calc.calculate(articles)
        assert result.score > 50
        assert result.total_articles == 3
        assert result.positive_count == 2
        assert result.neutral_count == 1
        assert result.negative_count == 0

    def test_calculate_negative(self):
        articles = [
            SentimentArticle("a1", "Bad", "Terrible", "weibo", datetime.now(timezone.utc), -0.8, "negative", "weibo", "product"),
            SentimentArticle("a2", "Awful", "Worst", "douyin", datetime.now(timezone.utc), -0.9, "very_negative", "douyin", "service")
        ]
        result = self.calc.calculate(articles)
        assert result.score < 50
        assert result.negative_count == 2

    def test_calculate_mixed(self):
        articles = [
            SentimentArticle("a1", "Good", "Nice", "weibo", datetime.now(timezone.utc), 0.8, "positive", "weibo", "product"),
            SentimentArticle("a2", "Bad", "Terrible", "weibo", datetime.now(timezone.utc), -0.8, "negative", "weibo", "product"),
            SentimentArticle("a3", "OK", "Fine", "xiaohongshu", datetime.now(timezone.utc), 0.0, "neutral", "xiaohongshu", "service")
        ]
        result = self.calc.calculate(articles)
        assert 0 <= result.score <= 100
        assert result.total_articles == 3
        assert result.positive_count == 1
        assert result.negative_count == 1
        assert result.neutral_count == 1

    def test_calculate_with_previous_score(self):
        articles = [
            SentimentArticle("a1", "Good", "Nice", "weibo", datetime.now(timezone.utc), 0.8, "positive", "weibo", "product")
        ]
        result1 = self.calc.calculate(articles)
        result2 = self.calc.calculate(articles, previous_score=result1.score - 5)
        assert result2.trend == "improving"

    def test_calculate_declining(self):
        articles = [
            SentimentArticle("a1", "Bad", "Terrible", "weibo", datetime.now(timezone.utc), -0.8, "negative", "weibo", "product")
        ]
        result = self.calc.calculate(articles, previous_score=80)
        assert result.trend == "declining"

    def test_platform_breakdown(self):
        articles = [
            SentimentArticle("a1", "Good", "Nice", "weibo", datetime.now(timezone.utc), 0.8, "positive", "weibo", "product"),
            SentimentArticle("a2", "Bad", "Terrible", "douyin", datetime.now(timezone.utc), -0.8, "negative", "douyin", "product")
        ]
        result = self.calc.calculate(articles)
        assert "weibo" in result.platform_breakdown
        assert "douyin" in result.platform_breakdown

    def test_category_breakdown(self):
        articles = [
            SentimentArticle("a1", "Good", "Nice", "weibo", datetime.now(timezone.utc), 0.8, "positive", "weibo", "product"),
            SentimentArticle("a2", "Bad", "Terrible", "weibo", datetime.now(timezone.utc), -0.8, "negative", "weibo", "service")
        ]
        result = self.calc.calculate(articles)
        assert "product" in result.category_breakdown
        assert "service" in result.category_breakdown

    def test_grade_a(self):
        articles = [
            SentimentArticle(f"a{i}", "Great", "Awesome", "weibo", datetime.now(timezone.utc), 0.95, "very_positive", "weibo", "product")
            for i in range(10)
        ]
        result = self.calc.calculate(articles)
        assert result.grade == "A"
        assert result.score >= 90

    def test_grade_f(self):
        articles = [
            SentimentArticle(f"a{i}", "Bad", "Terrible", "weibo", datetime.now(timezone.utc), -0.95, "very_negative", "weibo", "product")
            for i in range(10)
        ]
        result = self.calc.calculate(articles)
        assert result.grade == "F"
        assert result.score < 60

    def test_calculate_trend_empty(self):
        trend = self.calc.calculate_trend(MetricPeriod.DAY, days=7)
        assert trend.direction == "stable"
        assert trend.change_rate == 0

    def test_calculate_trend_with_history(self):
        # Generate some history
        for i in range(5):
            articles = [
                SentimentArticle(f"a{i}_{j}", "Test", "Content", "weibo", datetime.now(timezone.utc), 0.5, "positive", "weibo", "product")
                for j in range(10)
            ]
            self.calc.calculate(articles)

        trend = self.calc.calculate_trend(MetricPeriod.DAY, days=7)
        assert isinstance(trend.data_points, list)
        assert len(trend.data_points) > 0

    def test_history_limit(self):
        # Add more than max_history entries
        for i in range(150):
            articles = [
                SentimentArticle(f"a{i}", "Test", "Content", "weibo", datetime.now(timezone.utc), 0.5, "positive", "weibo", "product")
            ]
            self.calc.calculate(articles)
        assert len(self.calc._history) <= 100

    def test_reputation_trend_to_dict(self):
        trend = ReputationTrend(
            period=MetricPeriod.DAY,
            data_points=[{"date": "2024-01-01", "score": 80, "count": 10}],
            change_rate=5.5,
            direction="up"
        )
        d = trend.to_dict()
        assert d["period"] == "day"
        assert d["direction"] == "up"
        assert d["change_rate"] == 5.5
