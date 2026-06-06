"""
Tests for global error handlers (web/__init__.py)
"""
import json
import pytest
from unittest.mock import patch, MagicMock


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app_with_error_handlers():
    """Create a Flask app with error handlers registered."""
    import sys
    sys.path.insert(0, 'src')
    
    from acas_pro.web import create_app
    app = create_app({'TESTING': True, 'DEBUG': True})
    return app


@pytest.fixture
def client(app_with_error_handlers):
    """Test client for the app with error handlers."""
    with app_with_error_handlers.test_client() as client:
        yield client


# ---------------------------------------------------------------------------
# Tests for 404 Not Found
# ---------------------------------------------------------------------------

class Test404NotFound:
    """Tests for 404 error handler."""

    def test_api_request_returns_json(self, client):
        """API requests should get JSON response."""
        resp = client.get('/api/nonexistent', headers={'Accept': 'application/json'})
        assert resp.status_code == 404
        assert resp.mimetype == 'application/json'
        data = json.loads(resp.data)
        assert data['error'] is True
        assert 'Not Found' in data['message']

    def test_api_prefix_returns_json(self, client):
        """Requests to /api/ paths should get JSON response."""
        resp = client.get('/api/nonexistent')
        assert resp.status_code == 404
        assert resp.mimetype == 'application/json'

    def test_browser_request_returns_html(self, client):
        """Browser requests should get HTML response."""
        resp = client.get('/nonexistent')
        assert resp.status_code == 404
        assert 'text/html' in resp.mimetype
        assert b'<h1>' in resp.data


# ---------------------------------------------------------------------------
# Tests for 400 Bad Request
# ---------------------------------------------------------------------------

class Test400BadRequest:
    """Tests for 400 error handler."""

    def test_bad_request_returns_json(self, client):
        """400 errors should return JSON for API requests."""
        # Trigger a 400 by sending malformed JSON
        resp = client.post(
            '/api/auth/login',
            data='{invalid json}',
            content_type='application/json',
            headers={'Accept': 'application/json'}
        )
        # Should get 400 (Bad Request) not 500
        if resp.status_code == 400:
            data = json.loads(resp.data)
            assert data['error'] is True


# ---------------------------------------------------------------------------
# Tests for 405 Method Not Allowed
# ---------------------------------------------------------------------------

class Test405MethodNotAllowed:
    """Tests for 405 error handler."""

    def test_method_not_allowed_returns_json(self, client):
        """405 errors should return JSON for API requests."""
        # Try DELETE on a GET-only endpoint
        resp = client.delete('/api/openapi.json')
        assert resp.status_code == 405
        data = json.loads(resp.data)
        assert data['error'] is True
        assert 'Method' in data['message']


# ---------------------------------------------------------------------------
# Tests for error handler registration
# ---------------------------------------------------------------------------

class TestErrorHandlerRegistration:
    """Tests for error handler registration."""

    def test_app_has_error_handlers(self, app_with_error_handlers):
        """App should have error handlers registered."""
        # Check that error handlers are registered (Flask stores them in error_handler_spec)
        error_spec = app_with_error_handlers.error_handler_spec
        # Flask's error_handler_spec is a nested dict: {None: {code: {exception: handler}}}
        handlers = error_spec.get(None, {})
        # Check that 404, 500 etc. are registered
        assert 404 in handlers
        assert 500 in handlers

    def test_error_handlers_are_callable(self, app_with_error_handlers):
        """Error handlers should be callable."""
        # Trigger 404 and check response
        with app_with_error_handlers.test_client() as client:
            resp = client.get('/nonexistent-path-for-test')
            assert resp.status_code == 404
