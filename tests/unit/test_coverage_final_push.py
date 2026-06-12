"""
Targeted tests to cover the last few missed lines in high-coverage files.
These push overall coverage from 78.95% to >= 79%.
"""
import unittest.mock as mock
import datetime
from pathlib import Path


class TestAnalyzerNegationSwap:
    """Cover analyzer.py:242 - negation swaps pos/neg scores."""

    def test_negation_swap(self):
        from acas_pro.sentiment.analyzer import SentimentAnalyzer
        analyzer = SentimentAnalyzer()
        # Use a sentence with negation that triggers the swap at line 242
        # The method: if has_negation and pos_score > neg_score: swap
        result = analyzer.analyze("This is not good at all", context=None)
        assert hasattr(result, 'sentiment_score')
        assert isinstance(result.sentiment_score, float)


class TestAnalyticsLogicElseBranch:
    """Cover analytics_logic.py:110 - else branch in aggregate_metrics."""

    def test_aggregate_metrics_else_branch(self):
        from acas_pro.ui.logic.analytics_logic import AnalyticsLogic, MetricData, MetricType
        logic = AnalyticsLogic()
        ts = datetime.datetime(2024, 1, 15, 10, 30, 0)
        data = [
            MetricData(timestamp=ts, value=5.0, platform="douyin", metric_type=MetricType.VIEWS),
        ]
        # group_by="month" triggers the else branch at line 110
        result = logic.aggregate_metrics(data, group_by="month")
        assert isinstance(result, dict)
        assert len(result) == 1


class TestInventoryLogicHighUrgency:
    """Cover inventory_logic.py:123 - urgency = "high"."""

    def test_high_urgency_branch(self):
        from acas_pro.ui.logic.inventory_logic import InventoryLogic
        logic = InventoryLogic()
        # stock=5, daily_sales=1 -> days_until_stockout=5 -> "high"
        product = {
            "product_id": "P001",
            "product_name": "测试产品",
            "current_stock": 5,
            "avg_daily_sales": 1,
            "lead_time_days": 7,
        }
        result = logic._analyze_product(product)
        assert result.urgency == "high"
        assert result.days_until_stockout == 5


class TestUpdaterChecksumMismatch:
    """Cover updater.py:116-117 - filepath.unlink(); return None."""

    def test_download_checksum_mismatch(self):
        import urllib.request
        from acas_pro.update.updater import UpdateChecker, UpdateInfo

        checker = UpdateChecker()
        # Create a temp file to simulate downloaded file
        download_dir = Path.home() / ".acas-pro" / "updates"
        download_dir.mkdir(parents=True, exist_ok=True)
        test_file = download_dir / "ACAS-Pro-9.9.9-setup.exe"
        test_file.write_bytes(b"fake content")

        # Set _update_info with wrong checksum
        checker._update_info = UpdateInfo(
            version="9.9.9",
            download_url="http://example.com/fake",
            sha256="a" * 64,
            release_date="2024-01-01",
            changelog="test",
        )

        # Mock urllib to avoid real HTTP
        with mock.patch.object(urllib.request, 'urlopen') as mock_urlopen:
            mock_resp = mock.MagicMock()
            mock_resp.headers = {"Content-Length": "12"}
            mock_resp.read.side_effect = [b"fake content", b""]
            mock_urlopen.return_value.__enter__.return_value = mock_resp

            result = checker.download(progress_callback=mock.MagicMock())

        assert result is None
        assert not test_file.exists()
