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
        assert 'API key' in result.message

    def test_llm_import_error(self, checker, monkeypatch):
        """Test LLM import error branch."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = 'test-key'
        mock_config.llm.provider = 'openai'
        mock_config.llm.model = 'gpt-4'
        mock_config.llm.base_url = None
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)

        with patch('builtins.__import__', side_effect=ImportError("No module named 'llm'")):
            result = checker._check_llm()
            # ImportError is caught internally → UNHEALTHY
            assert result.status.value in ['degraded', 'unhealthy']

    def test_llm_client_init_error(self, checker, monkeypatch):
        """Test LLM client init error branch (non-ImportError exception)."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = 'test-key'
        mock_config.llm.provider = 'openai'
        mock_config.llm.model = 'gpt-4'
        mock_config.llm.base_url = None
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)

        # Force a non-ImportError exception during client instantiation
        def fake_import(name, *args, **kwargs):
            if name == 'acas_pro.llm.llm_client':
                raise Exception("Init failed")
            return __builtins__.__import__(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=fake_import):
            result = checker._check_llm()
            # Generic exception during client init → DEGRADED
            assert result.status.value in ['degraded', 'unhealthy']

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
            MockClient.return_value = mock_client

            result = checker._check_llm()
            assert result.status.value == 'healthy'
            assert 'openai' in result.message or 'gpt-4' in result.message