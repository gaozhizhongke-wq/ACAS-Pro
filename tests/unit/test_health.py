# -*- coding: utf-8 -*-
"""Tests for health checker module."""
import pytest
from unittest.mock import MagicMock
from acas_pro.web.health import (
    HealthChecker, HealthStatus, HealthCheckResult,
    health_checker
)


@pytest.fixture
def checker():
    return HealthChecker()


class TestHealthChecker:
    """Test HealthChecker class."""

    @pytest.fixture
    def checker(self):
        return HealthChecker()

    def test_check_all_healthy(self, checker, monkeypatch):
        """Test all checks return healthy."""
        def mock_check():
            return HealthCheckResult(
                name='mock', status=HealthStatus.HEALTHY,
                response_time_ms=1.0, message='OK'
            )
        checker.checks = [mock_check, mock_check]
        
        result = checker.check_all()
        assert result['status'] == 'healthy'
        assert len(result['checks']) == 2
        assert result['checks'][0]['status'] == 'healthy'

    def test_check_all_degraded(self, checker):
        """Test one degraded check results in degraded overall."""
        def healthy():
            return HealthCheckResult('db', HealthStatus.HEALTHY, 1.0, 'OK')
        def degraded():
            return HealthCheckResult('llm', HealthStatus.DEGRADED, 1.0, 'Slow')
        checker.checks = [healthy, degraded]
        
        result = checker.check_all()
        assert result['status'] == 'degraded'

    def test_check_all_unhealthy(self, checker):
        """Test one unhealthy check results in unhealthy overall."""
        def healthy():
            return HealthCheckResult('db', HealthStatus.HEALTHY, 1.0, 'OK')
        def unhealthy():
            return HealthCheckResult('llm', HealthStatus.UNHEALTHY, 1.0, 'Down')
        checker.checks = [healthy, unhealthy]
        
        result = checker.check_all()
        assert result['status'] == 'unhealthy'

    def test_check_all_exception(self, checker):
        """Test check exception handling."""
        def bad_check():
            raise ValueError("boom")
        checker.checks = [bad_check]
        
        result = checker.check_all()
        assert result['status'] == 'unhealthy'
        assert len(result['checks']) == 1
        assert 'boom' in result['checks'][0]['message']


class TestCheckDatabase:
    """Test _check_database method."""

    def test_database_healthy(self, checker, monkeypatch):
        """Test database healthy path."""
        mock_db = MagicMock()
        mock_db.execute_one.return_value = {'health_check': 1}
        monkeypatch.setattr('acas_pro.web.health.DatabaseManager', lambda: mock_db)
        
        result = checker._check_database()
        assert result.status == HealthStatus.HEALTHY
        assert 'OK' in result.message

    def test_database_unexpected_result(self, checker, monkeypatch):
        """Test database returns unexpected result."""
        mock_db = MagicMock()
        mock_db.execute_one.return_value = {'health_check': 0}
        monkeypatch.setattr('acas_pro.web.health.DatabaseManager', lambda: mock_db)
        
        result = checker._check_database()
        assert result.status == HealthStatus.UNHEALTHY
        assert 'unexpected' in result.message

    def test_database_exception(self, checker, monkeypatch):
        """Test database exception path."""
        def bad_db():
            raise RuntimeError("DB down")
        monkeypatch.setattr('acas_pro.web.health.DatabaseManager', bad_db)
        
        result = checker._check_database()
        assert result.status == HealthStatus.UNHEALTHY
        assert 'DB down' in result.message


class TestCheckConfig:
    """Test _check_config method."""

    def test_config_healthy(self, checker, monkeypatch):
        """Test config healthy path."""
        mock_config = MagicMock()
        mock_config.security.secret_key = 'a' * 50
        mock_config.environment = 'development'
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)
        
        result = checker._check_config()
        assert result.status == HealthStatus.HEALTHY

    def test_config_short_key(self, checker, monkeypatch):
        """Test short secret key."""
        mock_config = MagicMock()
        mock_config.security.secret_key = 'short'
        mock_config.environment = 'development'
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)
        
        result = checker._check_config()
        assert result.status == HealthStatus.DEGRADED
        assert 'issues' in result.details
        assert any('SECRET_KEY' in issue for issue in result.details['issues'])

    def test_config_default_key_in_production(self, checker, monkeypatch):
        """Test default key in production."""
        mock_config = MagicMock()
        mock_config.security.secret_key = 'acas-pro-secret-key-change-me'
        mock_config.environment = 'production'
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)
        
        result = checker._check_config()
        assert result.status == HealthStatus.DEGRADED
        issues = result.details['issues']
        assert any('default' in issue or 'SECRET_KEY' in issue for issue in issues)


class TestCheckDiskSpace:
    """Test _check_disk_space method."""

    def test_disk_space_healthy(self, checker, monkeypatch):
        """Test disk space healthy path."""
        import shutil
        mock_stat = MagicMock()
        mock_stat.free = 100 * (1024**3)  # 100GB
        mock_stat.total = 500 * (1024**3)
        mock_stat.used = 400 * (1024**3)
        
        monkeypatch.setattr(shutil, 'disk_usage', lambda x: mock_stat)
        monkeypatch.setattr('acas_pro.web.health.config.data_dir', '/tmp')
        
        result = checker._check_disk_space()
        assert result.status == HealthStatus.HEALTHY
        assert 'OK' in result.message

    def test_disk_space_degraded(self, checker, monkeypatch):
        """Test disk space degraded (5GB)."""
        import shutil
        mock_stat = MagicMock()
        mock_stat.free = 3 * (1024**3)  # 3GB
        mock_stat.total = 500 * (1024**3)
        mock_stat.used = 497 * (1024**3)
        
        monkeypatch.setattr(shutil, 'disk_usage', lambda x: mock_stat)
        monkeypatch.setattr('acas_pro.web.health.config.data_dir', '/tmp')
        
        result = checker._check_disk_space()
        assert result.status == HealthStatus.DEGRADED
        assert 'Warning' in result.message

    def test_disk_space_unhealthy(self, checker, monkeypatch):
        """Test disk space unhealthy (<1GB)."""
        import shutil
        mock_stat = MagicMock()
        mock_stat.free = 0.5 * (1024**3)  # 0.5GB
        mock_stat.total = 500 * (1024**3)
        mock_stat.used = 499.5 * (1024**3)
        
        monkeypatch.setattr(shutil, 'disk_usage', lambda x: mock_stat)
        monkeypatch.setattr('acas_pro.web.health.config.data_dir', '/tmp')
        
        result = checker._check_disk_space()
        assert result.status == HealthStatus.UNHEALTHY
        assert 'Critical' in result.message

    def test_disk_space_exception(self, checker, monkeypatch):
        """Test disk space exception."""
        import shutil
        monkeypatch.setattr(shutil, 'disk_usage', lambda x: (_ for _ in ()).throw(RuntimeError("Disk error")))
        
        result = checker._check_disk_space()
        assert result.status == HealthStatus.DEGRADED
        assert 'Disk check failed' in result.message


class TestCheckLLM:
    """Test _check_llm method."""

    def test_llm_disabled(self, checker, monkeypatch):
        """Test LLM disabled path."""
        mock_config = MagicMock()
        mock_config.llm.enabled = False
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)
        
        result = checker._check_llm()
        assert result.status == HealthStatus.DEGRADED
        assert 'disabled' in result.message

    def test_llm_no_api_key(self, checker, monkeypatch):
        """Test LLM no API key."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = None
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)
        
        result = checker._check_llm()
        assert result.status == HealthStatus.DEGRADED
        assert 'API key' in result.message

    def test_llm_import_error(self, checker, monkeypatch):
        """Test LLM import error."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = 'test-key'
        mock_config.llm.provider = 'openai'
        mock_config.llm.model = 'gpt-4'
        mock_config.llm.base_url = None
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)
        
        # Force ImportError by removing the module
        import sys
        monkeypatch.setitem(sys.modules, 'acas_pro.llm.llm_client', None)
        
        result = checker._check_llm()
        assert result.status == HealthStatus.DEGRADED
        assert 'import' in result.message.lower()

    def test_llm_exception(self, checker, monkeypatch):
        """Test LLM unexpected exception."""
        mock_config = MagicMock()
        mock_config.llm.enabled = True
        mock_config.llm.api_key = 'test'
        # Make config.llm raise exception
        type(mock_config).llm = property(lambda self: (_ for _ in ()).throw(RuntimeError("Config error")))
        monkeypatch.setattr('acas_pro.web.health.config', mock_config)
        
        result = checker._check_llm()
        assert result.status == HealthStatus.UNHEALTHY
        assert 'failed' in result.message.lower()


class TestSingleton:
    """Test singleton instance."""

    def test_health_checker_singleton(self):
        """Test health_checker is a HealthChecker instance."""
        assert isinstance(health_checker, HealthChecker)
        assert hasattr(health_checker, 'check_all')
        assert hasattr(health_checker, 'checks')
