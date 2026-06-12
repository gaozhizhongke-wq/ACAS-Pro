#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Analytics Business Logic
Extracted from analytics pages for testability
"""

from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from enum import Enum


class MetricType(Enum):
    """Analytics metric types"""

    VIEWS = "views"
    LIKES = "likes"
    COMMENTS = "comments"
    SHARES = "shares"
    FOLLOWERS = "followers"
    REVENUE = "revenue"
    CONVERSION = "conversion"


class TimeRange(Enum):
    """Time range presets"""

    TODAY = "today"
    YESTERDAY = "yesterday"
    LAST_7_DAYS = "7d"
    LAST_30_DAYS = "30d"
    THIS_MONTH = "month"
    LAST_MONTH = "last_month"
    CUSTOM = "custom"


@dataclass
class MetricData:
    """Single metric data point"""

    timestamp: datetime
    value: float
    platform: str
    metric_type: MetricType


@dataclass
class AnalyticsReport:
    """Analytics report"""

    period_start: datetime
    period_end: datetime
    metrics: Dict[MetricType, List[MetricData]]
    summary: Dict[str, float]
    trends: Dict[str, float]  # percentage change


class AnalyticsLogic:
    """Analytics business logic"""

    def __init__(self) -> None:
        self._data_cache: Dict[str, List[MetricData]] = {}

    def get_time_range(
        self,
        range_type: TimeRange,
        custom_start: Optional[datetime] = None,
        custom_end: Optional[datetime] = None,
    ) -> Tuple[datetime, datetime]:
        """Get start and end dates for time range"""
        now = datetime.now()

        if range_type == TimeRange.TODAY:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif range_type == TimeRange.YESTERDAY:
            start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0)
            end = start + timedelta(days=1)
        elif range_type == TimeRange.LAST_7_DAYS:
            start = now - timedelta(days=7)
            end = now
        elif range_type == TimeRange.LAST_30_DAYS:
            start = now - timedelta(days=30)
            end = now
        elif range_type == TimeRange.THIS_MONTH:
            start = now.replace(day=1, hour=0, minute=0, second=0)
            end = now
        elif range_type == TimeRange.LAST_MONTH:
            last_month = now.replace(day=1) - timedelta(days=1)
            start = last_month.replace(day=1, hour=0, minute=0, second=0)
            end = last_month.replace(day=last_month.day, hour=23, minute=59, second=59)
        elif range_type == TimeRange.CUSTOM and custom_start and custom_end:
            start = custom_start
            end = custom_end
        else:
            start = now - timedelta(days=7)
            end = now

        return start, end

    def aggregate_metrics(
        self, data: List[MetricData], group_by: str = "day"
    ) -> Dict[str, List[MetricData]]:
        """Aggregate metrics by time period"""
        from collections import defaultdict

        grouped = defaultdict(list)

        for item in data:
            if group_by == "day":
                key = item.timestamp.strftime("%Y-%m-%d")
            elif group_by == "hour":
                key = item.timestamp.strftime("%Y-%m-%d %H:00")
            elif group_by == "week":
                key = item.timestamp.strftime("%Y-W%W")
            else:
                key = item.timestamp.strftime("%Y-%m-%d")

            grouped[key].append(item)

        # Sum values for each group
        result = {}
        for key, items in grouped.items():
            total = sum(i.value for i in items)
            result[key] = [
                MetricData(
                    timestamp=items[0].timestamp,
                    value=total,
                    platform="all",
                    metric_type=items[0].metric_type,
                )
            ]

        return result

    def calculate_growth_rate(self, current: float, previous: float) -> float:
        """Calculate growth rate percentage"""
        if previous == 0:
            return 100.0 if current > 0 else 0.0
        return ((current - previous) / previous) * 100

    def calculate_engagement_rate(self, interactions: float, views: float) -> float:
        """Calculate engagement rate"""
        if views == 0:
            return 0.0
        return (interactions / views) * 100

    def generate_summary(self, data: List[MetricData]) -> Dict[str, float]:
        """Generate summary statistics"""
        if not data:
            return {"total": 0, "average": 0, "max": 0, "min": 0}

        values = [d.value for d in data]
        return {
            "total": sum(values),
            "average": sum(values) / len(values),
            "max": max(values),
            "min": min(values),
        }

    def compare_periods(
        self, current_data: List[MetricData], previous_data: List[MetricData]
    ) -> Dict[str, float]:
        """Compare two periods and return trend analysis"""
        current_total = sum(d.value for d in current_data)
        previous_total = sum(d.value for d in previous_data)

        return {
            "growth_rate": self.calculate_growth_rate(current_total, previous_total),
            "current_total": current_total,
            "previous_total": previous_total,
            "difference": current_total - previous_total,
        }

    def export_report(self, report: AnalyticsReport, format: str = "json") -> str:
        """Export report to string format"""
        import json

        data = {
            "period": {
                "start": report.period_start.isoformat(),
                "end": report.period_end.isoformat(),
            },
            "summary": report.summary,
            "trends": report.trends,
        }

        return json.dumps(data, indent=2)

    def detect_anomalies(
        self, data: List[MetricData], threshold: float = 2.0
    ) -> List[MetricData]:
        """Detect anomalous data points using standard deviation"""
        if len(data) < 3:
            return []

        values = [d.value for d in data]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance**0.5

        anomalies = []
        for item in data:
            z_score = abs(item.value - mean) / std_dev if std_dev > 0 else 0
            if z_score > threshold:
                anomalies.append(item)

        return anomalies
