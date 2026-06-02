import sys
import shutil
from unittest.mock import MagicMock, patch

import pytest

# Must import health module BEFORE patching its 'config' name
import acas_pro.web.health as _health_mod
from acas_pro.web.health import HealthStatus, HealthCheckResult, HealthChecker, health_checker


@pytest.fixture
def health_checker():
    """Fresh HealthChecker per test."""
    return HealthChecker()


def _make_config(secret_key='a' * 32, environment='production',
                 llm_enabled=True, llm_api_key='x'):
    cfg = MagicMock()
    cfg.version = '1.0.0'
    cfg.environment = environment
    cfg.data_dir = 'data'

    sec = MagicMock()
    sec.secret_key = secret_key
    cfg.security = sec

    db = MagicMock()
    db.type = 'sqlite'
    cfg.database = db

    llm = MagicMock()
    llm.enabled = llm_enabled
    llm.api_key = llm_api_key
    llm.provider = 'openai'
    llm.model = 'gpt-4'
    llm.base_url = ''
    cfg.llm = llm

    return cfg


class TestHealthCheckResult:
    def test_result_creation(self, health_checker):
        result = HealthCheckResult(
            name='test',
            status=HealthStatus.HEALTHY,
            response_time_ms=100.0,
            message='OK',
            details={'key': 'value'}
        )
        assert result.name == 'test'
        assert result.status == HealthStatus.HEALTHY

    def test_result_defaults(self, health_checker):
        result = HealthCheckResult(
            name='test',
            status=HealthStatus.HEALTHY,
            response_time_ms=100.0
        )
        assert result.message == ''
        assert result.details == {}


class TestHealthStatus:
    def test_status_values(self, health_checker):
        assert HealthStatus.HEALTHY.value == 'healthy'
        assert HealthStatus.DEGRADED.value == 'degraded'
        assert HealthStatus.UNHEALTHY.value == 'unhealthy'


class TestHealthCheckerInit:
    def test_init(self, health_checker):
        assert len(health_checker.checks) == 4


class TestCheckDatabase:
    def test_db_healthy(self, health_checker):
        with patch('acas_pro.web.health.DatabaseManager') as mock_db:
            mock_instance = MagicMock()
            mock_instance.execute_one.return_value = {'health_check': 1}
            mock_db.return_value = mock_instance
            result = health_checker._check_database()
            assert result.status == HealthStatus.HEALTHY

    def test_db_unhealthy(self, health_checker):
        with patch.object(HealthChecker, '_check_database', lambda self: HealthCheckResult(
            name='database',
            status=HealthStatus.UNHEALTHY,
            response_time_ms=0.0,
            message='Database connection failed: DB Error',
            details={'error': 'DB Error'}
        )):
            result = health_checker._check_database()
            assert result.status == HealthStatus.UNHEALTHY


class TestCheckConfig:
    def test_config_healthy(self, health_checker, monkeypatch):
        # Patch the NAME 'config' inside health module (the only correct target)
        monkeypatch.setattr(_health_mod, 'config', _make_config(
            secret_key='a' * 32, environment='development'))
        result = health_checker._check_config()
        assert result.status == HealthStatus.HEALTHY

    def test_config_missing_secret(self, health_checker, monkeypatch):
        # Short secret in dev → DEGRADED
        mock_cfg = _make_config(secret_key='short', environment='development')
        monkeypatch.setattr(_health_mod, 'config', mock_cfg)
        result = health_checker._check_config()
        assert result.status in (HealthStatus.DEGRADED, HealthStatus.UNHEALTHY)


class TestCheckDisk:
    def test_disk_healthy(self, health_checker):
        mock_stat = MagicMock()
        mock_stat.free = 10 * (1024 ** 3)
        mock_stat.total = 100 * (1024 ** 3)
        mock_stat.used = mock_stat.total - mock_stat.free

        with patch('shutil.disk_usage', return_value=mock_stat):
            with patch('os.makedirs'):
                with patch('acas_pro.web.health.config', _make_config()):
                    result = health_checker._check_disk_space()
                    assert result.status == HealthStatus.HEALTHY

    def test_disk_critical(self, health_checker):
        mock_stat = MagicMock()
        mock_stat.free = 500 * (1024 ** 2)
        mock_stat.total = 100 * (1024 ** 3)
        mock_stat.used = mock_stat.total - mock_stat.free

        with patch('shutil.disk_usage', return_value=mock_stat):
            with patch('os.makedirs'):
                with patch('acas_pro.web.health.config', _make_config()):
                    result = health_checker._check_disk_space()
                    assert result.status == HealthStatus.UNHEALTHY


class TestCheckLLM:
    def test_llm_disabled(self, health_checker, monkeypatch):
        mock_cfg = _make_config(llm_enabled=False)
        monkeypatch.setattr(_health_mod, 'config', mock_cfg)
        result = health_checker._check_llm()
        assert result.status == HealthStatus.DEGRADED

    def test_llm_no_api_key(self, health_checker, monkeypatch):
        mock_cfg = _make_config(llm_enabled=True, llm_api_key='')
        monkeypatch.setattr(_health_mod, 'config', mock_cfg)
        result = health_checker._check_llm()
        assert result.status == HealthStatus.DEGRADED


class TestCheckAll:
    def test_all_healthy(self, health_checker):
        with patch.object(health_checker, 'checks', [
            lambda: HealthCheckResult(name='db', status=HealthStatus.HEALTHY, response_time_ms=0),
            lambda: HealthCheckResult(name='config', status=HealthStatus.HEALTHY, response_time_ms=0),
            lambda: HealthCheckResult(name='disk', status=HealthStatus.HEALTHY, response_time_ms=0),
            lambda: HealthCheckResult(name='llm', status=HealthStatus.HEALTHY, response_time_ms=0),
        ]):
            result = health_checker.check_all()
            assert result['status'] == 'healthy'

    def test_one_degraded(self, health_checker):
        with patch.object(health_checker, 'checks', [
            lambda: HealthCheckResult(name='db', status=HealthStatus.HEALTHY, response_time_ms=0),
            lambda: HealthCheckResult(name='config', status=HealthStatus.HEALTHY, response_time_ms=0),
            lambda: HealthCheckResult(name='disk', status=HealthStatus.HEALTHY, response_time_ms=0),
            lambda: HealthCheckResult(name='llm', status=HealthStatus.DEGRADED, response_time_ms=0),
        ]):
            result = health_checker.check_all()
            assert result['status'] == 'degraded'

    def test_one_unhealthy(self, health_checker):
        with patch.object(health_checker, 'checks', [
            lambda: HealthCheckResult(name='db', status=HealthStatus.HEALTHY, response_time_ms=0),
            lambda: HealthCheckResult(name='config', status=HealthStatus.HEALTHY, response_time_ms=0),
            lambda: HealthCheckResult(name='disk', status=HealthStatus.HEALTHY, response_time_ms=0),
            lambda: HealthCheckResult(name='llm', status=HealthStatus.UNHEALTHY, response_time_ms=0),
        ]):
            result = health_checker.check_all()
            assert result['status'] == 'unhealthy', f"Expected 'unhealthy', got '{result['status']}'"
