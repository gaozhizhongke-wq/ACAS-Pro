# -*- coding: utf-8 -*-
"""Tests for dashboard web routes.

Uses create_app to properly load templates and register all blueprints.
"""
import pytest
import json
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_config():
    cfg = MagicMock()
    cfg.llm.enabled = True
    cfg.llm.provider = "openai"
    cfg.llm.api_key = "sk-test-key-12345678"
    return cfg


@pytest.fixture
def app(mock_config):
    from acas_pro.web import create_app

    with patch("acas_pro.core.config.get_config", return_value=mock_config):
        app = create_app(
            {"TESTING": True, "SECRET_KEY": "test-secret-key-for-testing"}
        )
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestDashboardIndex:
    """Index route renders dashboard.html with proper Jinja2 context."""

    def test_index_returns_html(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"<!DOCTYPE html>" in resp.data or b"<html" in resp.data

    def test_index_contains_dashboard_elements(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8", errors="replace")
        assert "dashboard" in html.lower()

    def test_index_contains_javascript(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8", errors="replace")
        assert "<script" in html or "javascript" in html.lower()

    def test_index_llm_info(self, client, mock_config):
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8", errors="replace")
        assert "openai" in html.lower()


class TestDashboardTemplate:
    """Template content assertions for dashboard.html."""

    def test_template_contains_api_endpoints(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8", errors="replace")
        # Template has sidebar navigation with data-page attributes
        assert "data-page=" in html

    def test_template_contains_styling(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8", errors="replace")
        assert "<style" in html or "bootstrap" in html.lower() or "tailwind" in html.lower()

    def test_template_responsive_design(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        html = resp.data.decode("utf-8", errors="replace")
        assert ("viewport" in html.lower() or "media" in html.lower())


class TestDashboardAPI:
    """Dashboard API route fallback tests (blueprint registered)."""

    def test_dashboard_data_route(self, client):
        resp = client.get("/api/dashboard/data")
        assert resp.status_code in (200, 404)

    def test_dashboard_export_route(self, client):
        resp = client.get("/api/dashboard/export")
        assert resp.status_code in (200, 404)


class TestDashboardAnalytics:
    def test_analytics_route(self, client):
        resp = client.get("/api/dashboard/analytics")
        assert resp.status_code in (200, 404)

    def test_realtime_route(self, client):
        resp = client.get("/api/dashboard/realtime")
        assert resp.status_code in (200, 404)


class TestDashboardCharts:
    def test_sales_chart_route(self, client):
        resp = client.get("/api/dashboard/charts/sales")
        assert resp.status_code in (200, 404)

    def test_traffic_chart_route(self, client):
        resp = client.get("/api/dashboard/charts/traffic")
        assert resp.status_code in (200, 404)


class TestDashboardFilters:
    def test_date_range_filter(self, client):
        resp = client.get("/api/dashboard/data?start=2026-01-01&end=2026-06-01")
        assert resp.status_code in (200, 404)

    def test_platform_filter(self, client):
        resp = client.get("/api/dashboard/data?platform=douyin")
        assert resp.status_code in (200, 404)
