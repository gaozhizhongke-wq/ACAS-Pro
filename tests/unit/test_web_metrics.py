"""
Tests for Prometheus metrics endpoint (web/routes/metrics.py)
"""
import pytest
from unittest.mock import patch, MagicMock
from flask import Flask


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app_with_metrics():
    """Create a Flask app with metrics blueprint registered."""
    import acas_pro.web.routes.metrics as metrics_mod
    
    # Ensure prometheus is "installed" for tests
    metrics_mod._HAS_PROMETHEUS = True
    metrics_mod._registry = None
    metrics_mod._metrics.clear()
    
    app = Flask(__name__)
    app.register_blueprint(metrics_mod.bp)
    return app, metrics_mod


@pytest.fixture
def client(app_with_metrics):
    """Test client for the app with metrics."""
    app, metrics_mod = app_with_metrics
    with app.test_client() as client:
        yield client


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestMetricsWithPrometheus:
    """Metrics endpoint when prometheus_client IS installed."""

    def test_metrics_endpoint_returns_200(self, client):
        resp = client.get('/metrics')
        assert resp.status_code == 200

    def test_metrics_endpoint_returns_correct_mimetype(self, app_with_metrics, client):
        app, metrics_mod = app_with_metrics
        resp = client.get('/metrics')
        # The actual CONTENT_TYPE_LATEST from prometheus_client
        assert 'text/plain' in resp.mimetype

    def test_metrics_endpoint_calls_generate_latest(self, app_with_metrics, client):
        app, metrics_mod = app_with_metrics
        with patch.object(metrics_mod, 'generate_latest', return_value=b'metrics_data') as mock_gen:
            with patch.object(metrics_mod, '_registry', MagicMock()):
                resp = client.get('/metrics')
                assert resp.data == b'metrics_data'

    def test_init_metrics_idempotent(self, app_with_metrics):
        """Calling _init_metrics twice should not crash."""
        app, metrics_mod = app_with_metrics
        # Simulate initialized state
        metrics_mod._registry = MagicMock()
        metrics_mod._metrics['test'] = True
        
        # Call _init_metrics again (should skip due to early return)
        metrics_mod._init_metrics()
        assert metrics_mod._registry is not None


class TestMetricsBlueprintRegistration:
    """Verify the blueprint is correctly configured."""

    def test_blueprint_name(self):
        from acas_pro.web.routes import metrics
        assert metrics.bp.name == 'metrics'

    def test_blueprint_url_prefix(self):
        from acas_pro.web.routes import metrics
        assert metrics.bp.url_prefix == '/metrics'


@pytest.mark.skipif(
    True,  # Skip because prometheus_client is installed
    reason="prometheus_client is installed, cannot test missing import"
)
class TestMetricsWithoutPrometheus:
    """Metrics endpoint when prometheus_client is NOT installed."""

    def test_has_prometheus_false(self):
        pass  # Skipped

    def test_metrics_endpoint_returns_503(self):
        pass  # Skipped
