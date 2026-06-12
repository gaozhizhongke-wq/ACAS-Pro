# -*- coding: utf-8 -*-
"""Tests for dashboard_stats routes to boost coverage."""
import pytest
from unittest.mock import MagicMock
from flask import Flask


@pytest.fixture
def app():
    app = Flask(__name__)
    from acas_pro.web.routes.dashboard_stats import bp
    app.register_blueprint(bp)
    app.config['TESTING'] = True
    app.config['PROPAGATE_EXCEPTIONS'] = False
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestDashboardStats:
    """Test /api/dashboard/stats route."""

    def test_dashboard_stats_success(self, client, monkeypatch):
        """Test dashboard stats with mocked DB returning data."""
        mock_db = MagicMock()
        mock_db.fetchone.side_effect = [
            {'total': 1234.56},      # revenue
            {'cnt': 42},              # active_orders
            {'cnt': 100},             # inventory
            {'cnt': 5},               # low_stock
            {'cnt': 2},               # risk_alerts
        ]
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.config.llm.enabled', True)
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.config.llm.provider', 'openai')

        response = client.get('/api/dashboard/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert data['revenue'] == 1234.56
        assert data['active_orders'] == 42
        assert data['inventory'] == 100
        assert data['low_stock'] == 5
        assert data['risk_alerts'] == 2
        assert data['llm_enabled'] is True
        assert data['llm_provider'] == 'openai'

    def test_dashboard_stats_fallback(self, client, monkeypatch):
        """Test dashboard stats when orders table missing (fallback path)."""
        mock_db = MagicMock()
        # First query succeeds, second fails, fallback succeeds
        mock_db.fetchone.side_effect = [
            {'total': 0},             # revenue
            Exception('no orders'),     # active_orders fails
            {'cnt': 10},               # fallback active_orders
            {'cnt': 50},               # inventory
            {'cnt': 3},               # low_stock
            {'cnt': 1},               # risk_alerts
        ]
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.config.llm.enabled', False)
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.config.llm.provider', 'disabled')

        response = client.get('/api/dashboard/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert data['active_orders'] == 10  # fallback value

    def test_dashboard_stats_degraded(self, client, monkeypatch):
        """Test dashboard stats when DB constructor fails (triggers outer except)."""
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: (_ for _ in ()).throw(Exception('DB constructor down')))
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.config.llm.enabled', True)
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.config.llm.provider', 'kimi')

        response = client.get('/api/dashboard/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert data.get('error') == 'Dashboard data unavailable' or data.get('status') == 'degraded'


class TestFestivals:
    """Test /api/festivals route."""

    def test_list_festivals(self, client, monkeypatch):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = [
            {'id': '1', 'name': '春节', 'festival_type': 'traditional', 'date': '2026-02-17'}
        ]
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)

        response = client.get('/api/festivals')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['festivals']) == 1

    def test_list_festivals_error(self, client, monkeypatch):
        mock_db = MagicMock()
        mock_db.fetchall.side_effect = Exception('table missing')
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)

        response = client.get('/api/festivals')
        assert response.status_code == 500
        data = response.get_json()
        assert data['success'] is False


class TestProducts:
    """Test /api/products routes."""

    def test_list_products(self, client, monkeypatch):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = [
            {'id': 'p1', 'name': 'Product 1', 'price': 99.9, 'stock_quantity': 10}
        ]
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)

        response = client.get('/api/products')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['products']) == 1

    def test_low_stock_products(self, client, monkeypatch):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = [
            {'id': 'p2', 'name': 'Low Stock', 'deficit': 5}
        ]
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)

        response = client.get('/api/products/low-stock')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True


class TestAccounts:
    """Test /api/accounts route."""

    def test_list_accounts(self, client, monkeypatch):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = [
            {'id': 'a1', 'platform': 'douyin', 'account_name': 'Test Account'}
        ]
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)

        response = client.get('/api/accounts')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['accounts']) == 1


class TestDashboardStatsErrors:
    """Test individual error handling paths in dashboard_stats."""

    def test_revenue_error(self, client, monkeypatch):
        mock_db = MagicMock()
        mock_db.fetchone.side_effect = [
            Exception('revenue fail'),  # revenue fails
            {'cnt': 1}, {'cnt': 2}, {'cnt': 3}, {'cnt': 4}  # rest succeed
        ]
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.config.llm.enabled', False)
        response = client.get('/api/dashboard/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert data['revenue'] == 0

    def test_inventory_error(self, client, monkeypatch):
        mock_db = MagicMock()
        mock_db.fetchone.side_effect = [
            {'total': 100}, {'cnt': 1},
            Exception('inventory fail'),  # inventory fails
            {'cnt': 3}, {'cnt': 4}
        ]
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.config.llm.enabled', False)
        response = client.get('/api/dashboard/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert data['inventory'] == 0

    def test_low_stock_error(self, client, monkeypatch):
        mock_db = MagicMock()
        mock_db.fetchone.side_effect = [
            {'total': 100}, {'cnt': 1}, {'cnt': 2},
            Exception('low_stock fail'),  # low_stock fails
            {'cnt': 4}
        ]
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.config.llm.enabled', False)
        response = client.get('/api/dashboard/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert data['low_stock'] == 0

    def test_risk_alerts_error(self, client, monkeypatch):
        mock_db = MagicMock()
        mock_db.fetchone.side_effect = [
            {'total': 100}, {'cnt': 1}, {'cnt': 2}, {'cnt': 3},
            Exception('risk_alerts fail')  # risk_alerts fails
        ]
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.config.llm.enabled', False)
        response = client.get('/api/dashboard/stats')
        assert response.status_code == 200
        data = response.get_json()
        assert data['risk_alerts'] == 0

    def test_festivals_error(self, client, monkeypatch):
        mock_db = MagicMock()
        mock_db.fetchall.side_effect = Exception('festivals fail')
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)
        response = client.get('/api/festivals')
        assert response.status_code == 500

    def test_products_error(self, client, monkeypatch):
        mock_db = MagicMock()
        mock_db.fetchall.side_effect = Exception('products fail')
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)
        response = client.get('/api/products')
        assert response.status_code == 500

    def test_low_stock_error_route(self, client, monkeypatch):
        mock_db = MagicMock()
        mock_db.fetchall.side_effect = Exception('low_stock fail')
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)
        response = client.get('/api/products/low-stock')
        assert response.status_code == 500

    def test_accounts_error(self, client, monkeypatch):
        mock_db = MagicMock()
        mock_db.fetchall.side_effect = Exception('accounts fail')
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)
        response = client.get('/api/accounts')
        assert response.status_code == 500

    def test_forecast_error(self, client, monkeypatch):
        mock_db = MagicMock()
        mock_db.fetchall.side_effect = Exception('forecast fail')
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)
        response = client.get('/api/forecast/daily')
        assert response.status_code == 500
    """Test /api/forecast/daily route."""

    def test_forecast_daily(self, client, monkeypatch):
        mock_db = MagicMock()
        mock_db.fetchall.return_value = [
            {'date': '2026-06-01', 'platform': 'douyin', 'revenue': 1000, 'orders': 50, 'views': 10000}
        ]
        monkeypatch.setattr('acas_pro.web.routes.dashboard_stats.DatabaseManager', lambda: mock_db)

        response = client.get('/api/forecast/daily')
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert len(data['data']) == 1
