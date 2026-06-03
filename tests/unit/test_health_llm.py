# -*- coding: utf-8 -*-
"""Additional tests for health.py LLM check branches."""
import pytest
from unittest.mock import MagicMock, patch


class TestCheckLLMBranches:
    """Test _check_llm method branches."""

    @pytest.fixture
    def checker(self):
        from acas_pro.web.health import HealthChecker
        return HealthChecker()

    def test_llm_disabled(self, checker, monkeypatch):
        """Test LLM disabled branch."""
        mock_config = MagicMock()
        mock_config.llm.enabled = False
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)
        
        result = checker._check_llm()
        assert result.status.value == 'degraded'
        assert 'disabled' in result.message

    def test_llm_no_api_key(self, checker, monkeypatch):
        """Test LLM no API key branch."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = None
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)
        
        result = checker._check_llm()
        assert result.status.value == 'degraded'
        assert 'API key not configured' in result.message

    def test_llm_import_error(self, checker, monkeypatch):
        """Test LLM import error branch."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = 'test-key'
        mock_config.llm.provider = 'openai'
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)
        
        with patch('builtins.__import__', side_effect=ImportError("No module named 'llm'")):
            result = checker._check_llm()
            # ImportError is caught internally
            assert result.status.value in ['degraded', 'unhealthy']

    def test_llm_api_401_error(self, checker, monkeypatch):
        """Test LLM API 401 error branch."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = 'test-key'
        mock_config.llm.provider = 'openai'
        mock_config.llm.model = 'gpt-4'
        mock_config.llm.base_url = None
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)
        
        with patch('acas_pro.llm.llm_client.LLMClient') as MockClient:
            mock_client = MagicMock()
            mock_client.chat.side_effect = Exception("401 Unauthorized")
            MockClient.return_value = mock_client
            
            result = checker._check_llm()
            assert result.status.value == 'unhealthy'
            assert 'invalid or expired' in result.message

    def test_llm_api_429_error(self, checker, monkeypatch):
        """Test LLM API 429 error branch."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = 'test-key'
        mock_config.llm.provider = 'openai'
        mock_config.llm.model = 'gpt-4'
        mock_config.llm.base_url = None
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)
        
        with patch('acas_pro.llm.llm_client.LLMClient') as MockClient:
            mock_client = MagicMock()
            mock_client.chat.side_effect = Exception("429 Too Many Requests")
            MockClient.return_value = mock_client
            
            result = checker._check_llm()
            assert result.status.value == 'degraded'
            assert 'rate limited' in result.message

    def test_llm_api_generic_error(self, checker, monkeypatch):
        """Test LLM API generic error branch."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = 'test-key'
        mock_config.llm.provider = 'openai'
        mock_config.llm.model = 'gpt-4'
        mock_config.llm.base_url = None
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)
        
        with patch('acas_pro.llm.llm_client.LLMClient') as MockClient:
            mock_client = MagicMock()
            mock_client.chat.side_effect = Exception("Connection timeout")
            MockClient.return_value = mock_client
            
            result = checker._check_llm()
            assert result.status.value == 'degraded'
            assert 'connectivity issue' in result.message

    def test_llm_empty_response(self, checker, monkeypatch):
        """Test LLM empty response branch."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = 'test-key'
        mock_config.llm.provider = 'openai'
        mock_config.llm.model = 'gpt-4'
        mock_config.llm.base_url = None
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)
        
        with patch('acas_pro.llm.llm_client.LLMClient') as MockClient:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = None
            mock_client.chat.return_value = mock_response
            MockClient.return_value = mock_client
            
            result = checker._check_llm()
            assert result.status.value == 'degraded'
            assert 'empty response' in result.message

    def test_llm_success(self, checker, monkeypatch):
        """Test LLM success branch."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = 'test-key'
        mock_config.llm.provider = 'openai'
        mock_config.llm.model = 'gpt-4'
        mock_config.llm.base_url = None
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)
        
        with patch('acas_pro.llm.llm_client.LLMClient') as MockClient:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.content = 'Hello!'
            mock_client.chat.return_value = mock_response
            MockClient.return_value = mock_client
            
            result = checker._check_llm()
            assert result.status.value == 'healthy'
            assert 'connected' in result.message
