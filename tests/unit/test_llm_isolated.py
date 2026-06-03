# -*- coding: utf-8 -*-
"""Tests for LLM routes - isolated unit tests."""
import pytest
from unittest.mock import MagicMock, patch


class TestProviderMapping:
    """Test provider mapping."""

    def test_provider_mapping(self):
        """Test provider mapping in create_llm_client."""
        from acas_pro.web.routes.llm import _PROVIDER_MAP, LLMProvider
        
        assert _PROVIDER_MAP['openai'] == LLMProvider.OPENAI
        assert _PROVIDER_MAP['anthropic'] == LLMProvider.ANTHROPIC
        assert _PROVIDER_MAP['deepseek'] == LLMProvider.DEEPSEEK
        assert _PROVIDER_MAP['kimi'] == LLMProvider.KIMI
        assert _PROVIDER_MAP['qwen'] == LLMProvider.QWEN
        assert _PROVIDER_MAP['lmstudio'] == LLMProvider.LMSTUDIO
        assert _PROVIDER_MAP['ollama'] == LLMProvider.OLLAMA

    def test_unknown_provider_defaults_to_openai(self, monkeypatch):
        """Test unknown provider defaults to OPENAI."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = 'test-key'
        mock_config.llm.provider = 'unknown_provider'
        mock_config.llm.model = 'gpt-4'
        mock_config.llm.temperature = 0.7
        mock_config.llm.max_tokens = 2000
        mock_config.llm.base_url = None
        monkeypatch.setattr('acas_pro.web.routes.llm.config', mock_config)
        
        from acas_pro.web.routes.llm import create_llm_client, LLMProvider
        with patch('acas_pro.web.routes.llm.LLMClient') as MockClient:
            create_llm_client()
            call_args = MockClient.call_args
            assert call_args[0][0].provider == LLMProvider.OPENAI


class TestCreateLLMClient:
    """Test create_llm_client function."""

    def test_llm_not_enabled(self, monkeypatch):
        """Test when LLM is not enabled."""
        mock_config = MagicMock()
        mock_config.llm.enabled = False
        mock_config.llm.api_key = None
        monkeypatch.setattr('acas_pro.web.routes.llm.config', mock_config)
        
        from acas_pro.web.routes.llm import create_llm_client
        with pytest.raises(RuntimeError, match='LLM not configured'):
            create_llm_client()

    def test_llm_no_api_key(self, monkeypatch):
        """Test when API key is missing."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = None
        monkeypatch.setattr('acas_pro.web.routes.llm.config', mock_config)
        
        from acas_pro.web.routes.llm import create_llm_client
        with pytest.raises(RuntimeError, match='LLM not configured'):
            create_llm_client()

    def test_llm_success(self, monkeypatch):
        """Test successful client creation."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = 'test-key'
        mock_config.llm.provider = 'openai'
        mock_config.llm.model = 'gpt-4'
        mock_config.llm.temperature = 0.7
        mock_config.llm.max_tokens = 2000
        mock_config.llm.base_url = None
        monkeypatch.setattr('acas_pro.web.routes.llm.config', mock_config)
        
        from acas_pro.web.routes.llm import create_llm_client, LLMProvider
        with patch('acas_pro.web.routes.llm.LLMClient') as MockClient:
            create_llm_client()
            call_args = MockClient.call_args[0][0]
            assert call_args.provider == LLMProvider.OPENAI
            assert call_args.api_key == 'test-key'
            assert call_args.model == 'gpt-4'

    def test_llm_with_base_url(self, monkeypatch):
        """Test client creation with base_url."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = 'test-key'
        mock_config.llm.provider = 'openai'
        mock_config.llm.model = 'gpt-4'
        mock_config.llm.temperature = 0.7
        mock_config.llm.max_tokens = 2000
        mock_config.llm.base_url = 'https://custom.api.com'
        mock_config.llm.api_base = None  # Ensure api_base is None
        monkeypatch.setattr('acas_pro.web.routes.llm.config', mock_config)
        
        from acas_pro.web.routes.llm import create_llm_client
        with patch('acas_pro.web.routes.llm.LLMClient') as MockClient:
            create_llm_client()
            call_args = MockClient.call_args[0][0]
            assert call_args.api_base == 'https://custom.api.com'

    def test_llm_with_legacy_api_base(self, monkeypatch):
        """Test client creation with legacy api_base attribute."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = 'test-key'
        mock_config.llm.provider = 'openai'
        mock_config.llm.model = 'gpt-4'
        mock_config.llm.temperature = 0.7
        mock_config.llm.max_tokens = 2000
        # Only has api_base, not base_url
        mock_config.llm.api_base = 'https://legacy.api.com'
        mock_config.llm.base_url = None
        monkeypatch.setattr('acas_pro.web.routes.llm.config', mock_config)
        
        from acas_pro.web.routes.llm import create_llm_client
        with patch('acas_pro.web.routes.llm.LLMClient') as MockClient:
            create_llm_client()
            call_args = MockClient.call_args[0][0]
            assert call_args.api_base == 'https://legacy.api.com'
