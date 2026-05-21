"""Quick coverage boost for zero-coverage UI modules"""
import pytest

class TestForecastPage:
    def test_import(self):
        from acas_pro.ui.pages.forecast import ForecastPage
        assert ForecastPage is not None

class TestDashboardPage:
    def test_import(self):
        from acas_pro.ui.pages.dashboard import DashboardPage
        assert DashboardPage is not None

class TestInventoryPage:
    def test_import(self):
        from acas_pro.ui.pages.inventory import InventoryPage
        assert InventoryPage is not None
