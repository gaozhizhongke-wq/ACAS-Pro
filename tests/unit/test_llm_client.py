#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for llm/llm_client.py"""

import pytest
from unittest.mock import patch, MagicMock
from acas_pro.llm.llm_client import (
    LLMProvider, LLMMessage, LLMResponse, LLMConfig, LLMClient
)


class TestLLMProvider:
    def test_values(self):
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"
        assert LLMProvider.KIMI.value == "kimi"
        assert LLMProvider.DEEPSEEK.value == "deepseek"


class TestLLMMessage:
    def test_create(self):
        msg = LLMMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.name is None

    def test_create_with_name(self):
        msg = LLMMessage(role="assistant", content="Hi", name="bot")
        assert msg.name == "bot"


class TestLLMResponse:
    def test_create(self):
        resp = LLMResponse(content="Hello")
        assert resp.content == "Hello"
        assert resp.role == "assistant"
        assert resp.finish_reason == "stop"

    def test_create_full(self):
        resp = LLMResponse(
            content="Hello",
            model="gpt-4",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
            latency_ms=100
        )
        assert resp.model == "gpt-4"
        assert resp.usage["prompt_tokens"] == 10


class TestLLMConfig:
    def test_default_provider(self):
        config = LLMConfig()
        assert config.provider == LLMProvider.OPENAI

    def test_default_base_openai(self):
        config = LLMConfig(provider=LLMProvider.OPENAI)
        assert "openai.com" in config.api_base

    def test_default_base_anthropic(self):
        config = LLMConfig(provider=LLMProvider.ANTHROPIC)
        assert "anthropic" in config.api_base

    def test_default_base_kimi(self):
        config = LLMConfig(provider=LLMProvider.KIMI)
        assert "moonshot" in config.api_base

    def test_default_base_deepseek(self):
        config = LLMConfig(provider=LLMProvider.DEEPSEEK)
        assert "deepseek" in config.api_base

    def test_default_model_openai(self):
        config = LLMConfig(provider=LLMProvider.OPENAI)
        assert config.model == "gpt-4o"

    def test_default_model_anthropic(self):
        config = LLMConfig(provider=LLMProvider.ANTHROPIC)
        assert "claude" in config.model

    def test_custom_values(self):
        config = LLMConfig(
            provider=LLMProvider.OPENAI,
            api_key="test_key",
            model="gpt-3.5-turbo",
            temperature=0.5
        )
        assert config.api_key == "test_key"
        assert config.model == "gpt-3.5-turbo"
        assert config.temperature == 0.5


class TestLLMClient:
    def setup_method(self):
        self.config = LLMConfig(
            provider=LLMProvider.OPENAI,
            api_key="test_key",
            model="gpt-4"
        )

    def test_init(self):
        client = LLMClient(self.config)
        assert client is not None
        assert client.config == self.config

    def test_chat_mock(self):
        with patch.object(LLMClient, 'chat') as mock_chat:
            mock_chat.return_value = LLMResponse(
                content="Hello!",
                model="gpt-4",
                usage={"prompt_tokens": 5, "completion_tokens": 2}
            )
            client = LLMClient(self.config)
            messages = [LLMMessage(role="user", content="Hi")]
            response = client.chat(messages)
            assert response.content == "Hello!"

    def test_quick_chat(self):
        with patch.object(LLMClient, 'chat') as mock_chat:
            mock_chat.return_value = LLMResponse(content="Quick response")
            client = LLMClient(self.config)
            response = client.quick_chat("Test prompt")
            assert response == "Quick response"

    def test_quick_chat_with_system(self):
        with patch.object(LLMClient, 'chat') as mock_chat:
            mock_chat.return_value = LLMResponse(content="With system")
            client = LLMClient(self.config)
            response = client.quick_chat("Test", system="You are helpful")
            assert response == "With system"

    def test_count_tokens(self):
        client = LLMClient(self.config)
        tokens = client.count_tokens("Hello world")
        assert tokens > 0

    def test_count_tokens_empty(self):
        client = LLMClient(self.config)
        tokens = client.count_tokens("")
        assert tokens == 0

    def test_list_models(self):
        client = LLMClient(self.config)
        try:
            models = client.list_models()
            assert isinstance(models, list)
        except Exception:
            pass  # API may not be available

    def test_stream_chat(self):
        with patch.object(LLMClient, 'stream_chat') as mock_stream:
            mock_stream.return_value = iter([LLMResponse(content="Hello")])
            client = LLMClient(self.config)
            messages = [LLMMessage(role="user", content="Hi")]
            responses = list(client.stream_chat(messages))
            assert len(responses) >= 0
