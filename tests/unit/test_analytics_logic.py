import json
from datetime import datetime, timedelta

from acas_pro.ui.logic.analytics_logic import (
    AnalyticsLogic, MetricType, TimeRange, MetricData, AnalyticsReport
)


class TestTimeRange:
    def test_today_range(self):
        logic = AnalyticsLogic()
        start, end = logic.get_time_range(TimeRange.TODAY)
        assert start.date() == datetime.now().date()
        assert end <= datetime.now()

    def test_yesterday_range(self):
        logic = AnalyticsLogic()
        start, end = logic.get_time_range(TimeRange.YESTERDAY)
        assert start.date() == (datetime.now() - timedelta(days=1)).date()

    def test_last_7_days(self):
        logic = AnalyticsLogic()
        start, end = logic.get_time_range(TimeRange.LAST_7_DAYS)
        assert (end - start).days == 7

    def test_last_30_days(self):
        logic = AnalyticsLogic()
        start, end = logic.get_time_range(TimeRange.LAST_30_DAYS)
        assert (end - start).days == 30

    def test_custom_range(self):
        logic = AnalyticsLogic()
        custom_start = datetime(2025, 1, 1)
        custom_end = datetime(2025, 1, 31)
        start, end = logic.get_time_range(
            TimeRange.CUSTOM, custom_start=custom_start, custom_end=custom_end
        )
        assert start == custom_start
        assert end == custom_end

    def test_default_range(self):
        logic = AnalyticsLogic()
        start, end = logic.get_time_range(TimeRange.THIS_MONTH)
        assert start.day == 1
        assert start.month == datetime.now().month
        assert start.hour == 0


class TestAggregateMetrics:
    def _make_data(self, platform='douyin', metric_type=MetricType.VIEWS):
        return [
            MetricData(
                timestamp=datetime(2025, 1, 1, 10, 0),
                value=100.0,
                platform=platform,
                metric_type=metric_type,
            ),
            MetricData(
                timestamp=datetime(2025, 1, 1, 11, 0),
                value=200.0,
                platform=platform,
                metric_type=metric_type,
            ),
            MetricData(
                timestamp=datetime(2025, 1, 2, 10, 0),
                value=300.0,
                platform=platform,
                metric_type=metric_type,
            ),
        ]

    def test_aggregate_by_day(self):
        logic = AnalyticsLogic()
        data = self._make_data()
        result = logic.aggregate_metrics(data, group_by='day')
        assert '2025-01-01' in result
        assert '2025-01-02' in result
        assert result['2025-01-01'][0].value == 300.0  # 100 + 200

    def test_aggregate_by_hour(self):
        logic = AnalyticsLogic()
        data = self._make_data()
        result = logic.aggregate_metrics(data, group_by='hour')
        assert '2025-01-01 10:00' in result
        assert '2025-01-01 11:00' in result

    def test_aggregate_empty(self):
        logic = AnalyticsLogic()
        result = logic.aggregate_metrics([], group_by='day')
        assert result == {}


class TestCalculateGrowthRate:
    def test_positive_growth(self):
        logic = AnalyticsLogic()
        rate = logic.calculate_growth_rate(120.0, 100.0)
        assert rate == 20.0

    def test_negative_growth(self):
        logic = AnalyticsLogic()
        rate = logic.calculate_growth_rate(80.0, 100.0)
        assert rate == -20.0

    def test_zero_previous(self):
        logic = AnalyticsLogic()
        rate = logic.calculate_growth_rate(50.0, 0.0)
        assert rate == 100.0

    def test_both_zero(self):
        logic = AnalyticsLogic()
        rate = logic.calculate_growth_rate(0.0, 0.0)
        assert rate == 0.0


class TestCalculateEngagementRate:
    def test_normal(self):
        logic = AnalyticsLogic()
        rate = logic.calculate_engagement_rate(150.0, 1000.0)
        assert rate == 15.0

    def test_zero_views(self):
        logic = AnalyticsLogic()
        rate = logic.calculate_engagement_rate(150.0, 0.0)
        assert rate == 0.0


class TestGenerateSummary:
    def test_non_empty(self):
        logic = AnalyticsLogic()
        data = [
            MetricData(datetime.now(), 10.0, 'douyin', MetricType.VIEWS),
            MetricData(datetime.now(), 20.0, 'douyin', MetricType.VIEWS),
            MetricData(datetime.now(), 30.0, 'douyin', MetricType.VIEWS),
        ]
        summary = logic.generate_summary(data)
        assert summary['total'] == 60.0
        assert summary['max'] == 30.0
        assert summary['min'] == 10.0

    def test_empty(self):
        logic = AnalyticsLogic()
        summary = logic.generate_summary([])
        assert summary['total'] == 0
        assert summary['average'] == 0
        assert summary['max'] == 0


class TestComparePeriods:
    def test_positive_growth(self):
        logic = AnalyticsLogic()
        current = [
            MetricData(datetime.now(), 200.0, 'douyin', MetricType.VIEWS),
        ]
        previous = [
            MetricData(datetime.now(), 100.0, 'douyin', MetricType.VIEWS),
        ]
        result = logic.compare_periods(current, previous)
        assert result['growth_rate'] == 100.0
        assert result['difference'] == 100.0


class TestExportReport:
    def test_export_json(self):
        logic = AnalyticsLogic()
        report = AnalyticsReport(
            period_start=datetime(2025, 1, 1),
            period_end=datetime(2025, 1, 31),
            metrics={},
            summary={'total': 1000.0},
            trends={'views': 10.5},
        )
        result = logic.export_report(report, format='json')
        data = json.loads(result)
        assert data['summary']['total'] == 1000.0
        assert data['trends']['views'] == 10.5


class TestDetectAnomalies:
    def test_detects_spike(self):
        logic = AnalyticsLogic()
        # Use larger spread so 50 is clearly > 2 std deviations
        data = [
            MetricData(datetime.now(), v, 'douyin', MetricType.VIEWS)
            for v in [10.0, 12.0, 11.0, 13.0, 10.0, 11.0, 50.0]
        ]
        anomalies = logic.detect_anomalies(data, threshold=2.0)
        values = [d.value for d in data]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5
        # Print diagnostics
        print(f'mean={mean}, std_dev={std_dev}, z_score(50)={abs(50 - mean)/std_dev}')
        assert len(anomalies) >= 1
        assert anomalies[0].value == 50.0

    def test_too_few_data_points(self):
        logic = AnalyticsLogic()
        data = [
            MetricData(datetime.now(), 10.0, 'douyin', MetricType.VIEWS),
            MetricData(datetime.now(), 20.0, 'douyin', MetricType.VIEWS),
        ]
        anomalies = logic.detect_anomalies(data)
        assert anomalies == []
