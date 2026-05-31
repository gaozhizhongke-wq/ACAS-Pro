# -*- coding: utf-8 -*-
"""Tests for ACAS Pro web health checks"""
import sys
import shutil
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

from acas_pro.web.health import HealthStatus, HealthCheckResult, HealthChecker, health_checker


# ---------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------

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


# ---------------------------------------------------------------
# HealthCheckResult
# ---------------------------------------------------------------

class TestHealthCheckResult:
    def test_result_creation(self):
        r = HealthCheckResult(name='db', status=HealthStatus.HEALTHY,
                             response_time_ms=1.0, message='OK')
        assert r.name == 'db'
        assert r.status == HealthStatus.HEALTHY

    def test_result_defaults(self):
        r = HealthCheckResult(name='x', status=HealthStatus.DEGRADED,
                             response_time_ms=0)
        assert r.message == ''
        assert r.details == {}


# ---------------------------------------------------------------
# HealthStatus
# ---------------------------------------------------------------

class TestHealthStatus:
    def test_status_values(self):
        assert HealthStatus.HEALTHY.value == 'healthy'
        assert HealthStatus.DEGRADED.value == 'degraded'
        assert HealthStatus.UNHEALTHY.value == 'unhealthy'


# ---------------------------------------------------------------
# _check_database
# ---------------------------------------------------------------

class TestCheckDatabase:
    def test_db_healthy(self, health_checker):
        mock_db = MagicMock()
        mock_db.execute_one.return_value = {'health_check': 1}

        with patch('acas_pro.web.health.DatabaseManager', return_value=mock_db):
            with patch('acas_pro.web.health.config') as mock_config:
                mock_config.return_value = _make_config()
                result = health_checker._check_database()
                assert result.status == HealthStatus.HEALTHY
                assert 'OK' in result.message

    def test_db_unhealthy(self, health_checker):
        with patch('acas_pro.web.health.DatabaseManager', side_effect=Exception('boom')):
            with patch('acas_pro.web.health.config') as mock_config:
                mock_config.return_value = _make_config()
                result = health_checker._check_database()
                assert result.status == HealthStatus.UNHEALTHY


# ---------------------------------------------------------------
# _check_config
# ---------------------------------------------------------------

class TestCheckConfig:
    def test_config_healthy(self, health_checker):
        with patch('acas_pro.web.health.config') as mock_config:
            mock_config.return_value = _make_config(secret_key='a' * 32,
                                                   environment='production')
            result = health_checker._check_config()
            assert result.status == HealthStatus.HEALTHY

    def test_config_missing_secret(self, health_checker):
        with patch('acas_pro.web.health.config') as mock_config:
            mock_config.return_value = _make_config(secret_key='short',
                                                   environment='production')
            result = health_checker._check_config()
            assert result.status == HealthStatus.DEGRADED


# ---------------------------------------------------------------
# _check_disk_space
# shutil is imported locally inside _check_disk_space, so patch the real module.
# ---------------------------------------------------------------

class TestCheckDisk:
    def test_disk_healthy(self, health_checker):
        mock_stat = MagicMock()
        mock_stat.free = 10 * (1024 ** 3)
        mock_stat.total = 100 * (1024 ** 3)
        mock_stat.used = mock_stat.total - mock_stat.free

        with patch('shutil.disk_usage', return_value=mock_stat):
            with patch('acas_pro.web.health.config') as mock_config:
                mock_config.return_value = _make_config()
                result = health_checker._check_disk_space()
                assert result.status == HealthStatus.HEALTHY

    def test_disk_critical(self, health_checker):
        mock_stat = MagicMock()
        mock_stat.free = 500 * (1024 ** 2)
        mock_stat.total = 100 * (1024 ** 3)
        mock_stat.used = mock_stat.total - mock_stat.free

        with patch('shutil.disk_usage', return_value=mock_stat):
            with patch('acas_pro.web.health.config') as mock_config:
                mock_config.return_value = _make_config()
                result = health_checker._check_disk_space()
                assert result.status == HealthStatus.UNHEALTHY


# ---------------------------------------------------------------
# _check_llm
# ---------------------------------------------------------------

class TestCheckLLM:
    def test_llm_disabled(self, health_checker):
        with patch('acas_pro.web.health.config') as mock_config:
            mock_config.return_value = _make_config(llm_enabled=False)
            result = health_checker._check_llm()
            assert result.status == HealthStatus.DEGRADED
            assert 'disabled' in result.message.lower()

    def test_llm_no_api_key(self, health_checker):
        with patch('acas_pro.web.health.config') as mock_config:
            mock_config.return_value = _make_config(llm_enabled=True, llm_api_key='')
            result = health_checker._check_llm()
            assert result.status == HealthStatus.DEGRADED
            assert 'key' in result.message.lower()


# ---------------------------------------------------------------
# check_all
# ---------------------------------------------------------------

class TestCheckAll:
    def _patch_all(self, health_checker, db=None, cfg=None, disk=None, llm=None):
        if db is None:
            db = HealthCheckResult('database', HealthStatus.HEALTHY, 1.0, 'OK')
        if cfg is None:
            cfg = HealthCheckResult('config', HealthStatus.HEALTHY, 1.0, 'OK')
        if disk is None:
            disk = HealthCheckResult('disk', HealthStatus.HEALTHY, 1.0, 'OK')
        if llm is None:
            llm = HealthCheckResult('llm', HealthStatus.HEALTHY, 1.0, 'OK')

        mock_config = _make_config()
        with patch.object(health_checker, '_check_database', return_value=db), \
             patch.object(health_checker, '_check_config', return_value=cfg), \
             patch.object(health_checker, '_check_disk_space', return_value=disk), \
             patch.object(health_checker, '_check_llm', return_value=llm), \
             patch('acas_pro.web.health.config', return_value=mock_config):
            return health_checker.check_all()

    def test_all_healthy(self, health_checker):
        result = self._patch_all(health_checker)
        assert result['status'] == 'healthy'

    def test_one_degraded(self, health_checker):
        degraded = HealthCheckResult('config', HealthStatus.DEGRADED, 1.0, 'issue')
        result = self._patch_all(health_checker, cfg=degraded)
        assert result['status'] == 'degraded'

    def test_one_unhealthy(self, health_checker):
        unhealthy = HealthCheckResult('database', HealthStatus.UNHEALTHY, 1.0, 'down')
        result = self._patch_all(health_checker, db=unhealthy)
        assert result['status'] == 'unhealthy'
