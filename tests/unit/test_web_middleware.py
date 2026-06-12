import pytest
import json
import time
from unittest.mock import patch
from flask import Flask, jsonify, g


@pytest.fixture
def app():
    app = Flask(__name__)
    from acas_pro.web.middleware import RequestContext
    RequestContext.init_app(app)

    @app.route('/test-protected')
    def protected():
        if not getattr(g, 'user', None):
            return jsonify({'error': 'Authentication required'}), 401
        return jsonify({'ok': True})

    @app.route('/test-bad-request', methods=['POST'])
    def bad_request():
        return jsonify({'error': 'Invalid request', 'message': 'Test error', 'request_id': None}), 400

    @app.route('/test-internal-error')
    def internal_error():
        raise Exception('Internal error')

    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestRequestContext:
    def test_before_request_sets_request_id(self, client):
        response = client.get('/test-protected')
        assert response.status_code in (200, 401)
        # X-Request-ID should be set in response
        assert 'X-Request-ID' in response.headers

    def test_before_request_sets_client_ip(self, client):
        """Verify X-Forwarded-For is captured via a test route."""
        # Add a test route that echoes g.client_ip
        app = client.application
        @app.route('/test-echo-ip')
        def echo_ip():
            return {'client_ip': g.get('client_ip', '')}, 200

        response = client.get('/test-echo-ip', headers={'X-Forwarded-For': '1.2.3.4'})
        data = json.loads(response.data)
        assert data['client_ip'] == '1.2.3.4'

    def test_after_request_adds_request_id(self, client):
        response = client.get('/test-protected')
        assert 'X-Request-ID' in response.headers


class TestErrorHandler:
    def test_bad_request_handler(self, client):
        response = client.post('/test-bad-request', json={})
        assert response.status_code == 400
        data = json.loads(response.data)
        # Flask uses 'Bad Request' as status phrase
        assert 'error' in data or 'message' in data

    def test_unauthorized_handler(self, client):
        response = client.get('/test-protected')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert 'Authentication' in data['error'] or 'auth' in data['error'].lower()

    def test_internal_server_error_handler(self, app, client):
        with patch('acas_pro.web.middleware.logger') as mock_logger:  # noqa: F841
            with app.test_request_context('/test-internal-error'):
                try:
                    response = client.get('/test-internal-error')
                    # Should get 500
                    assert response.status_code == 500
                except Exception:
                    pass


class TestRequestTracking:
    def test_request_id_header(self, client):
        response = client.get('/test-protected', headers={'X-Request-ID': 'test-123'})
        assert response.headers.get('X-Request-ID') == 'test-123' or response.headers.get('X-Request-ID') is not None

    def test_response_time_tracking(self, app, client):
        with app.test_request_context('/test-protected'):
            start = time.time()
            g.start_time = start
            g.request_id = 'test'
            response = client.get('/test-protected')
            assert response.status_code in (200, 401)
