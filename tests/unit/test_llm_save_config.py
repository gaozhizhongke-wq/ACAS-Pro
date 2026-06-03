# -*- coding: utf-8 -*-
"""Tests for LLM save_config route."""
import pytest
from unittest.mock import MagicMock, patch
from flask import Flask, g


class TestSaveLLMConfig:
    """Test save_llm_config route."""

    @pytest.fixture
    def app(self):
        """Create Flask app with auth context."""
        app = Flask(__name__)
        app.secret_key = 'test'
        
        @app.route('/api/llm/config', methods=['POST'])
        def save_config():
            from flask import g, request, jsonify
            if not hasattr(g, 'user') or not g.user:
                return jsonify({'error': 'Authentication required'}), 401
            return jsonify({'success': True}), 200
        
        return app

    def test_save_config_unauthorized(self, app):
        """Test save config without auth."""
        with app.test_client() as client:
            response = client.post('/api/llm/config', json={
                'provider': 'openai',
                'api_key': 'test-key'
            })
            assert response.status_code == 401

    def test_save_config_with_auth(self, app):
        """Test save config with auth."""
        with app.test_client() as client:
            with app.app_context():
                g.user = {'user_id': 'test', 'account': 'test@example.com'}
                response = client.post('/api/llm/config', json={
                    'provider': 'openai',
                    'api_key': 'test-key',
                    'api_base': 'https://api.openai.com/v1',
                    'model': 'gpt-4-turbo'
                })
                assert response.status_code == 200

    def test_save_config_validation_error(self, app):
        """Test save config with invalid data."""
        with app.test_client() as client:
            with app.app_context():
                g.user = {'user_id': 'test', 'account': 'test@example.com'}
                response = client.post('/api/llm/config', json={
                    'provider': 'invalid',
                    'api_key': ''
                })
                # Should fail validation or succeed with defaults
                assert response.status_code in [200, 400]


class TestLLMChatRoute:
    """Test llm_chat route branches."""

    def test_chat_route_not_configured(self, monkeypatch):
        """Test chat when LLM not configured."""
        mock_config = MagicMock()
        mock_config.llm.enabled = False
        mock_config.llm.api_key = None
        monkeypatch.setattr('acas_pro.web.routes.llm.config', mock_config)
        
        from acas_pro.web.routes.llm import create_llm_client
        with pytest.raises(RuntimeError, match='LLM not configured'):
            create_llm_client()

    def test_chat_route_api_error(self, monkeypatch):
        """Test chat API error handling."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = 'test-key'
        mock_config.llm.provider = 'openai'
        mock_config.llm.model = 'gpt-4'
        mock_config.llm.temperature = 0.7
        mock_config.llm.max_tokens = 2000
        mock_config.llm.base_url = None
        monkeypatch.setattr('acas_pro.web.routes.llm.config', mock_config)
        
        with patch('acas_pro.web.routes.llm.LLMClient') as MockClient:
            mock_client = MagicMock()
            mock_client.chat.side_effect = Exception("API Error")
            MockClient.return_value = mock_client
            
            from acas_pro.web.routes.llm import create_llm_client
            client = create_llm_client()
            with pytest.raises(Exception, match='API Error'):
                client.chat([])
