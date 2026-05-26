#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for web/routes/llm.py"""

import pytest
from unittest.mock import patch, MagicMock
from flask import Flask
from acas_pro.web.routes.llm import create_llm_client, save_llm_config, llm_chat


@pytest.fixture
def app_ctx():
    """Provide a minimal Flask app context for tests that call jsonify."""
    app = Flask(__name__)
    app.config['TESTING'] = True
    with app.app_context():
        yield app


class TestCreateLLMClient:
    def test_create_with_config(self, monkeypatch):
        import acas_pro.web.routes.llm as _llm_mod
        _mock_cfg = MagicMock()
        _mock_cfg().llm.enabled = True
        _mock_cfg().llm.api_key = 'test_key'
        _mock_cfg().llm.provider = 'openai'
        _mock_cfg().llm.model = 'gpt-4'
        _mock_cfg().llm.api_base = 'https://api.openai.com/v1'
        _mock_cfg().llm.temperature = 0.7
        _mock_cfg().llm.max_tokens = 2048
        monkeypatch.setattr(_llm_mod, 'config', _mock_cfg)
        _mock_client = MagicMock()
        _mock_instance = MagicMock()
        _mock_client.return_value = _mock_instance
        monkeypatch.setattr(_llm_mod, 'LLMClient', _mock_client)
        monkeypatch.setattr(_llm_mod, 'ClientLLMConfig', MagicMock())
        client = _llm_mod.create_llm_client()
        assert client is _mock_instance

    def test_not_configured_raises(self):
        with patch('acas_pro.web.routes.llm.config') as mock_cfg:
            mock_cfg().llm.enabled = False
            mock_cfg().llm.api_key = ''
            with pytest.raises(RuntimeError, match='LLM not configured'):
                create_llm_client()


class TestSaveLLMConfig:
    @pytest.fixture(autouse=True)
    def _request_ctx(self, app_ctx):
        """Auto-wrap each test in a request context."""
        with app_ctx.test_request_context(json={'provider': 'openai', 'api_key': 'test_key', 'model': 'gpt-4'}):
            yield

    def test_save_config(self):
        from flask import g as real_g
        with patch('acas_pro.web.routes.llm.request') as mock_req, \
             patch('acas_pro.web.routes.llm.config') as mock_cfg:
            real_g.user = MagicMock()
            real_g.user.id = "USER001"
            mock_req.json = {'provider': 'openai', 'api_key': 'test_key', 'model': 'gpt-4'}
            response = save_llm_config()
            assert response is not None
            assert response.status_code == 200

    def test_save_config_minimal(self):
        from flask import g as real_g
        with patch('acas_pro.web.routes.llm.request') as mock_req, \
             patch('acas_pro.web.routes.llm.config') as mock_cfg:
            real_g.user = MagicMock()
            real_g.user.id = "USER001"
            mock_req.json = {'provider': 'kimi'}
            response = save_llm_config()
            assert response is not None


class TestLLMChat:
    def test_chat_basic(self, app_ctx):
        with app_ctx.test_request_context(json={"messages": [{"role": "user", "content": "Hello"}], "provider": "openai"}):
            with patch('acas_pro.web.routes.llm.create_llm_client') as mock_create:
                mock_client = MagicMock()
                mock_client.chat.return_value = MagicMock(
                    content="Hello!",
                    model="gpt-4",
                    usage={"prompt_tokens": 5, "completion_tokens": 2}
                )
                mock_create.return_value = mock_client
                response = llm_chat()
                assert response is not None

    def test_chat_with_system(self, app_ctx):
        with app_ctx.test_request_context(json={"messages": [{"role": "system", "content": "You are helpful"}, {"role": "user", "content": "Hello"}], "provider": "openai"}):
            with patch('acas_pro.web.routes.llm.create_llm_client') as mock_create:
                mock_client = MagicMock()
                mock_client.chat.return_value = MagicMock(
                    content="Hi!",
                    model="gpt-4",
                    usage={"prompt_tokens": 10, "completion_tokens": 1}
                )
                mock_create.return_value = mock_client
                response = llm_chat()
                assert response is not None

    def test_chat_no_messages(self, app_ctx):
        with app_ctx.test_request_context(json={"provider": "openai"}):
            response = llm_chat()
            assert response is not None

    def test_chat_empty_messages(self, app_ctx):
        with app_ctx.test_request_context(json={"messages": [], "provider": "openai"}):
            response = llm_chat()
            assert response is not None
