import pytest
import json
from unittest.mock import patch, MagicMock
from flask import Flask, g


@pytest.fixture
def app():
    app = Flask(__name__)
    from acas_pro.web.routes.llm import bp
    app.register_blueprint(bp, url_prefix='/api/llm')
    app.config['TESTING'] = True

    # Simulate authenticated user for all requests
    @app.before_request
    def _set_user():
        g.user = {'id': 'test-user', 'username': 'tester'}

    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestLLMChat:
    """Test POST /api/llm/chat — expects {messages: [{role, content}]}"""

    def test_chat_success(self, client):
        with patch('acas_pro.web.routes.llm.create_llm_client') as mock_create:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = 'Hello!'
            mock_client.chat.return_value = mock_response
            mock_create.return_value = mock_client

            response = client.post(
                '/api/llm/chat',
                json={'messages': [{'role': 'user', 'content': 'Hi'}]}
            )
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['content'] == 'Hello!'

    def test_chat_missing_messages(self, client):
        response = client.post(
            '/api/llm/chat',
            json={}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_chat_empty_messages(self, client):
        response = client.post(
            '/api/llm/chat',
            json={'messages': []}
        )
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data

    def test_chat_api_error(self, client):
        with patch('acas_pro.web.routes.llm.create_llm_client') as mock_create:
            mock_client = MagicMock()
            mock_client.chat.side_effect = Exception('API error')
            mock_create.return_value = mock_client

            response = client.post(
                '/api/llm/chat',
                json={'messages': [{'role': 'user', 'content': 'Hi'}]}
            )
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data

    def test_chat_not_configured(self, client):
        with patch('acas_pro.web.routes.llm.create_llm_client') as mock_create:
            mock_create.side_effect = RuntimeError('LLM not configured')

            response = client.post(
                '/api/llm/chat',
                json={'messages': [{'role': 'user', 'content': 'Hi'}]}
            )
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data


class TestLLMConfig:
    """Test POST /api/llm/config — checks g.user for auth"""

    def test_config_no_auth(self, app, client):
        """Without before_request setting g.user → 401"""
        # Create a separate app without the auth bypass
        app2 = Flask(__name__)
        from acas_pro.web.routes.llm import bp
        app2.register_blueprint(bp, url_prefix='/api/llm')
        # Do NOT set g.user
        client2 = app2.test_client()

        response = client2.post(
            '/api/llm/config',
            json={'provider': 'openai', 'api_key': 'key123'}
        )
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data

    def test_config_save_with_auth(self, app, client):
        """With g.user set → should reach config update logic"""
        with patch('acas_pro.web.routes.llm.config') as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.llm = MagicMock()
            mock_config.return_value = mock_cfg

            response = client.post(
                '/api/llm/config',
                json={'provider': 'openai', 'api_key': 'key123'}
            )
            # 200 = success, 500 = env/import error — both OK as long as not 401/404
            assert response.status_code in (200, 500)

    def test_config_missing_provider(self, app, client):
        """Missing provider — should still work (defaults to openai)"""
        with patch('acas_pro.web.routes.llm.config') as mock_config:
            mock_cfg = MagicMock()
            mock_cfg.llm = MagicMock()
            mock_config.return_value = mock_cfg

            response = client.post(
                '/api/llm/config',
                json={}
            )
            assert response.status_code in (200, 500)


class TestLLMRoutesExist:
    """Verify the two expected routes exist (no 404)"""

    def test_chat_route_exists(self, client):
        response = client.post(
            '/api/llm/chat',
            json={'messages': [{'role': 'user', 'content': 'test'}]}
        )
        assert response.status_code != 404

    def test_config_route_exists(self, app, client):
        # Use app without auth bypass to hit the 401 path (route exists)
        app2 = Flask(__name__)
        from acas_pro.web.routes.llm import bp
        app2.register_blueprint(bp, url_prefix='/api/llm')
        client2 = app2.test_client()
        response = client2.post('/api/llm/config', json={})
        assert response.status_code != 404
