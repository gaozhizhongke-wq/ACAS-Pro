#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase A: LLM 模块简化测试
"""

import pytest
from unittest.mock import Mock, patch

from acas_pro.llm.llm_client import LLMClient, LLMConfig, LLMProvider, LLMMessage


class TestLLMSimple:
    """简化 LLM 测试"""
    
    def test_llm_config_defaults(self):
        """测试 LLM 配置默认值"""
        config = LLMConfig(provider=LLMProvider.DEEPSEEK, api_key="test-key")
        assert config.provider == LLMProvider.DEEPSEEK
        assert config.api_key == "test-key"
        assert config.model == "deepseek-chat"  # 默认值
        assert config.api_base == "https://api.deepseek.com/v1"
    
    def test_llm_config_openai(self):
        """测试 OpenAI 配置"""
        config = LLMConfig(provider=LLMProvider.OPENAI, api_key="test-key")
        assert config.model == "gpt-4o"
        assert config.api_base == "https://api.openai.com/v1"
    
    def test_llm_message_creation(self):
        """测试消息创建"""
        msg = LLMMessage(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"
    
    def test_llm_client_creation(self):
        """测试客户端创建"""
        config = LLMConfig(provider=LLMProvider.DEEPSEEK, api_key="test-key")
        client = LLMClient(config=config)
        assert client is not None
        assert client.config == config
    
    def test_llm_token_count(self):
        """测试 Token 计数"""
        config = LLMConfig(provider=LLMProvider.DEEPSEEK, api_key="test-key")
        client = LLMClient(config=config)
        
        tokens = client.count_tokens("Hello world")
        assert tokens > 0
    
    def test_llm_list_models(self):
        """测试列出模型"""
        models = LLMClient.list_models(LLMProvider.DEEPSEEK)
        assert "deepseek-chat" in models
        assert "deepseek-coder" in models
    
    @patch('acas_pro.llm.llm_client.urllib.request.urlopen')
    def test_llm_quick_chat_mock(self, mock_urlopen):
        """测试快速聊天 (mock)"""
        mock_response = Mock()
        mock_response.read.return_value = b'{"choices": [{"message": {"content": "Hello!", "role": "assistant"}, "finish_reason": "stop"}], "model": "deepseek-chat", "usage": {"total_tokens": 10}}'
        mock_urlopen.return_value.__enter__ = Mock(return_value=mock_response)
        mock_urlopen.return_value.__exit__ = Mock(return_value=False)
        
        config = LLMConfig(provider=LLMProvider.DEEPSEEK, api_key="test-key")
        client = LLMClient(config=config)
        
        response = client.quick_chat("Hi", system="You are helpful")
        assert "Hello" in response or response != ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
