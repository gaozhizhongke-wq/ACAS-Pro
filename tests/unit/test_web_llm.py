#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for web/routes/llm.py"""

import pytest
from unittest.mock import patch, MagicMock
from acas_pro.web.routes.llm import create_llm_client, save_llm_config, llm_chat


class TestCreateLLMClient:
    def test_create_with_config(self):
        with patch('acas_pro.web.routes.llm.LLMClient') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            client = create_llm_client(
                provider="openai",
                api_key="test_key",
                model="gpt-4"
            )
            assert client is not None

    def test_create_default(self):
        with patch('acas_pro.web.routes.llm.LLMClient') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            client = create_llm_client()
            assert client is not None


class TestSaveLLMConfig:
    def test_save_config(self):
        with patch('acas_pro.web.routes.llm.g') as mock_g:
            mock_g.user = MagicMock()
            mock_g.user.id = "USER001"
            with patch('acas_pro.web.routes.llm.db') as mock_db:
                result = save_llm_config(
                    provider="openai",
                    api_key="test_key",
                    model="gpt-4"
                )
                assert result is True

    def test_save_config_minimal(self):
        with patch('acas_pro.web.routes.llm.g') as mock_g:
            mock_g.user = MagicMock()
            mock_g.user.id = "USER001"
            with patch('acas_pro.web.routes.llm.db') as mock_db:
                result = save_llm_config(provider="kimi")
                assert result is True


class TestLLMChat:
    def test_chat_basic(self):
        with patch('acas_pro.web.routes.llm.request') as mock_request:
            mock_request.get_json.return_value = {
                "messages": [{"role": "user", "content": "Hello"}],
                "provider": "openai"
            }
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

    def test_chat_with_system(self):
        with patch('acas_pro.web.routes.llm.request') as mock_request:
            mock_request.get_json.return_value = {
                "messages": [{"role": "system", "content": "You are helpful"}, {"role": "user", "content": "Hello"}],
                "provider": "openai"
            }
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

    def test_chat_no_messages(self):
        with patch('acas_pro.web.routes.llm.request') as mock_request:
            mock_request.get_json.return_value = {
                "provider": "openai"
            }
            response = llm_chat()
            assert response is not None

    def test_chat_empty_messages(self):
        with patch('acas_pro.web.routes.llm.request') as mock_request:
            mock_request.get_json.return_value = {
                "messages": [],
                "provider": "openai"
            }
            response = llm_chat()
            assert response is not None
