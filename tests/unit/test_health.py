#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for web/health.py module."""

import sys
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock

# Mock dependencies before importing
sys.modules['acas_pro.core.config'] = MagicMock()
sys.modules['acas_pro.core.logging'] = MagicMock(get_logger=MagicMock(return_value=MagicMock()))
sys.modules['acas_pro.core.database'] = MagicMock()
sys.modules['acas_pro.llm.llm_client'] = MagicMock()


class TestHealthStatus:
    def test_healthy_value(self):
        from acas_pro.web.health import HealthStatus
        assert HealthStatus.HEALTHY.value == "healthy"

    def test_degraded_value(self):
        from acas_pro.web.health import HealthStatus
        assert HealthStatus.DEGRADED.value == "degraded"

    def test_unhealthy_value(self):
        from acas_pro.web.health import HealthStatus
        assert HealthStatus.UNHEALTHY.value == "unhealthy"


class TestHealthCheckResult:
    def test_create_result(self):
        from acas_pro.web.health import HealthCheckResult, HealthStatus
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.HEALTHY,
            response_time_ms=10.5,
            message="OK",
            details={"key": "value"}
        )
        assert result.name == "test"
        assert result.status == HealthStatus.HEALTHY
        assert result.response_time_ms == 10.5
        assert result.message == "OK"
        assert result.details == {"key": "value"}

    def test_create_result_minimal(self):
        from acas_pro.web.health import HealthCheckResult, HealthStatus
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.UNHEALTHY,
            response_time_ms=0.0
        )
        assert result.name == "test"
        assert result.message == ""
        assert result.details == {}


class TestHealthChecker:
    """Test HealthChecker class."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup mocks before each test."""
        # Clear cached modules
        for m in list(sys.modules.keys()):
            if m.startswith('acas_pro'):
                del sys.modules[m]

        # Mock config
        mock_config = MagicMock()
        mock_config.return_value.version = "1.0.0"
        mock_config.return_value.environment = "test"
        mock_config.return_value.database.type = "sqlite"
        mock_config.return_value.security.secret_key = "x" * 32
        mock_config.return_value.llm.enabled = False
        mock_config.return_value.llm.api_key = None

        mock_config_pkg = MagicMock()
        mock_config_pkg.config = mock_config
        sys.modules['acas_pro.core.config'] = mock_config_pkg

        # Mock logging
        mock_logger = MagicMock()
        mock_get_logger = MagicMock(return_value=mock_logger)
        mock_logging_pkg = MagicMock()
        mock_logging_pkg.get_logger = mock_get_logger
        sys.modules['acas_pro.core.logging'] = mock_logging_pkg

        # Mock database
        mock_db = MagicMock()
        mock_db.execute_one.return_value = {"health_check": 1}
        mock_dm = MagicMock()
        mock_dm.return_value = mock_db
        mock_db_pkg = MagicMock()
        mock_db_pkg.DatabaseManager = mock_dm
        sys.modules['acas_pro.core.database'] = mock_db_pkg

        yield

        # Cleanup
        for m in list(sys.modules.keys()):
            if m.startswith('acas_pro'):
                del sys.modules[m]

    def test_init(self):
        from acas_pro.web.health import HealthChecker
        checker = HealthChecker()
        assert len(checker.checks) == 4
        assert callable(checker.checks[0])

    def test_check_all_healthy(self):
        from acas_pro.web.health import HealthChecker
        checker = HealthChecker()
        result = checker.check_all()
        assert 'status' in result
        assert 'checks' in result
        assert 'timestamp' in result
        assert 'version' in result
        assert 'environment' in result
        assert 'response_time_ms' in result

    def test_check_all_exception_handling(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()

        # Make one check raise an exception
        def bad_check():
            raise Exception("test error")

        checker.checks = [bad_check]
        result = checker.check_all()
        assert result['status'] == HealthStatus.UNHEALTHY.value

    def test_check_database_healthy(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()
        result = checker._check_database()
        assert result.status == HealthStatus.HEALTHY
        assert result.name == 'database'

    def test_check_database_unhealthy(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()

        # Mock db.execute_one to return unexpected result
        mock_db_pkg = sys.modules['acas_pro.core.database']
        mock_db = mock_db_pkg.DatabaseManager.return_value
        mock_db.execute_one.return_value = None

        result = checker._check_database()
        assert result.status == HealthStatus.UNHEALTHY

    def test_check_database_exception(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()

        # Mock db.execute_one to raise exception
        mock_db_pkg = sys.modules['acas_pro.core.database']
        mock_db = mock_db_pkg.DatabaseManager.return_value
        mock_db.execute_one.side_effect = Exception("db error")

        result = checker._check_database()
        assert result.status == HealthStatus.UNHEALTHY

    def test_check_config_healthy(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()
        result = checker._check_config()
        assert result.status == HealthStatus.HEALTHY
        assert result.name == 'configuration'

    def test_check_config_short_secret_key(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()

        # Mock config with short secret key
        mock_config_pkg = sys.modules['acas_pro.core.config']
        mock_config = mock_config_pkg.config
        mock_config.return_value.security.secret_key = "short"
        mock_config.return_value.environment = "production"

        result = checker._check_config()
        assert result.status == HealthStatus.DEGRADED
        assert "issues" in result.details

    def test_check_config_default_secret_in_production(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()

        # Mock config with default secret key in production
        mock_config_pkg = sys.modules['acas_pro.core.config']
        mock_config = mock_config_pkg.config
        mock_config.return_value.security.secret_key = "acas-pro-secret-key-change-me"
        mock_config.return_value.environment = "production"

        result = checker._check_config()
        assert result.status == HealthStatus.DEGRADED

    def test_check_disk_space_healthy(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        
        # Patch shutil and os BEFORE calling the method
        with patch('shutil.disk_usage', return_value=MagicMock(free=10*(1024**3), total=100*(1024**3), used=90*(1024**3))), \
             patch('os.makedirs'):
            checker = HealthChecker()
            result = checker._check_disk_space()
            assert result.status == HealthStatus.HEALTHY

    def test_check_disk_space_critical(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        
        with patch('shutil.disk_usage', return_value=MagicMock(free=0.5*(1024**3), total=100*(1024**3), used=99.5*(1024**3))), \
             patch('os.makedirs'):
            checker = HealthChecker()
            result = checker._check_disk_space()
            assert result.status == HealthStatus.UNHEALTHY

    def test_check_disk_space_warning(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        
        with patch('shutil.disk_usage', return_value=MagicMock(free=3*(1024**3), total=100*(1024**3), used=97*(1024**3))), \
             patch('os.makedirs'):
            checker = HealthChecker()
            result = checker._check_disk_space()
            assert result.status == HealthStatus.DEGRADED

    def test_check_disk_space_exception(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        
        with patch('shutil.disk_usage', side_effect=Exception("disk error")), \
             patch('os.makedirs'):
            checker = HealthChecker()
            result = checker._check_disk_space()
            assert result.status == HealthStatus.DEGRADED

    def test_check_llm_disabled(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()

        mock_config_pkg = sys.modules['acas_pro.core.config']
        mock_config = mock_config_pkg.config
        mock_config.return_value.llm.enabled = False

        result = checker._check_llm()
        assert result.status == HealthStatus.DEGRADED
        assert "disabled" in result.message.lower() or "disabled" in str(result.details).lower()

    def test_check_llm_no_api_key(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()

        mock_config_pkg = sys.modules['acas_pro.core.config']
        mock_config = mock_config_pkg.config
        mock_config.return_value.llm.enabled = True
        mock_config.return_value.llm.api_key = None

        result = checker._check_llm()
        assert result.status == HealthStatus.DEGRADED

    def test_check_llm_configured(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()

        mock_config_pkg = sys.modules['acas_pro.core.config']
        mock_config = mock_config_pkg.config
        mock_config.return_value.llm.enabled = True
        mock_config.return_value.llm.api_key = "test-key"
        mock_config.return_value.llm.provider = "openai"
        mock_config.return_value.llm.model = "gpt-4"

        # Mock LLM client import
        mock_llm_client = MagicMock()
        mock_llm_client.LLMClient = MagicMock()
        mock_llm_client.LLMProvider = MagicMock()
        mock_llm_client.LLMConfig = MagicMock()
        sys.modules['acas_pro.llm.llm_client'] = mock_llm_client

        result = checker._check_llm()
        assert result.status == HealthStatus.HEALTHY