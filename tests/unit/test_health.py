#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for web/health.py module."""

import sys
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers: make a proper config mock (attributes, not .return_value)
# ---------------------------------------------------------------------------

def _make_config(environment="test", secret_key_length=32,
                 llm_enabled=False, llm_api_key=None, llm_provider="openai"):
    cfg = MagicMock()
    cfg.version = "1.0.0"
    cfg.environment = environment
    cfg.data_dir = "data"
    # security
    cfg.security = MagicMock()
    cfg.security.secret_key = "x" * secret_key_length
    # database
    cfg.database = MagicMock()
    cfg.database.type = "sqlite"
    # llm — provider MUST be a real string (health.py validates against enum)
    cfg.llm = MagicMock()
    cfg.llm.enabled = llm_enabled
    cfg.llm.api_key = llm_api_key
    cfg.llm.provider = llm_provider
    cfg.llm.model = "gpt-4"
    cfg.llm.base_url = ""
    return cfg


# ---------------------------------------------------------------------------
# TestHealthStatus
# ---------------------------------------------------------------------------

class TestHealthStatus:
    @pytest.fixture(autouse=True)
    def _mock_deps(self):
        # Save real modules before mocking
        _saved = {}
        for mod in ['acas_pro.core.config', 'acas_pro.core.logging',
                     'acas_pro.core.database', 'acas_pro.llm.llm_client']:
            existing = sys.modules.get(mod)
            if existing is not None and not hasattr(existing, 'mock_calls'):
                _saved[mod] = existing
        sys.modules['acas_pro.core.config'] = MagicMock()
        sys.modules['acas_pro.core.logging'] = MagicMock(
            get_logger=MagicMock(return_value=MagicMock())
        )
        sys.modules['acas_pro.core.database'] = MagicMock()
        sys.modules['acas_pro.llm.llm_client'] = MagicMock()
        yield
        for mod, real in _saved.items():
            sys.modules[mod] = real
        for mod in ['acas_pro.core.config', 'acas_pro.core.logging',
                     'acas_pro.core.database', 'acas_pro.llm.llm_client']:
            if mod not in _saved and mod in sys.modules:
                del sys.modules[mod]

    def test_healthy_value(self):
        from acas_pro.web.health import HealthStatus
        assert HealthStatus.HEALTHY.value == "healthy"

    def test_degraded_value(self):
        from acas_pro.web.health import HealthStatus
        assert HealthStatus.DEGRADED.value == "degraded"

    def test_unhealthy_value(self):
        from acas_pro.web.health import HealthStatus
        assert HealthStatus.UNHEALTHY.value == "unhealthy"


# ---------------------------------------------------------------------------
# TestHealthCheckResult
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# TestHealthChecker
# ---------------------------------------------------------------------------

class TestHealthChecker:
    """Test HealthChecker class.

    Strategy:
      - autouse fixture patches acas_pro.web.health's module-level names
        (config, DatabaseManager, logger) via monkeypatch.
      - NEVER delete or pop acas_pro.* from sys.modules (breaks cross-test mocks).
      - Tests that need to tweak config values do so via self.mock_config.xxx
        (the same object that health.py reads).
    """

    @pytest.fixture(autouse=True)
    def setup(self, monkeypatch):
        """Patch health.py's module-level refs.  Runs before every test."""
        import acas_pro.web.health as _health_mod

        # --- config ---
        self.mock_config = _make_config()
        monkeypatch.setattr(_health_mod, 'config', self.mock_config, raising=False)

        # --- DatabaseManager ---
        self.mock_db = MagicMock()
        self.mock_db.execute_one.return_value = {"health_check": 1}
        self.mock_dm = MagicMock()
        self.mock_dm.return_value = self.mock_db
        monkeypatch.setattr(_health_mod, 'DatabaseManager', self.mock_dm, raising=False)

        # --- logger ---
        self.mock_logger = MagicMock()
        monkeypatch.setattr(_health_mod, 'logger', self.mock_logger, raising=False)

        yield

    # ------------------------------------------------------------------
    # init / check_all
    # ------------------------------------------------------------------

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

        def bad_check():
            raise Exception("test error")

        checker.checks = [bad_check]
        result = checker.check_all()
        assert result['status'] == HealthStatus.UNHEALTHY.value

    # ------------------------------------------------------------------
    # _check_database
    # ------------------------------------------------------------------

    def test_check_database_healthy(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()
        result = checker._check_database()
        assert result.status == HealthStatus.HEALTHY
        assert result.name == 'database'

    def test_check_database_unhealthy(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()
        self.mock_db.execute_one.return_value = None
        result = checker._check_database()
        assert result.status == HealthStatus.UNHEALTHY

    def test_check_database_exception(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()
        self.mock_db.execute_one.side_effect = Exception("db error")
        result = checker._check_database()
        assert result.status == HealthStatus.UNHEALTHY

    # ------------------------------------------------------------------
    # _check_config
    # ------------------------------------------------------------------

    def test_check_config_healthy(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()
        result = checker._check_config()
        assert result.status == HealthStatus.HEALTHY
        assert result.name == 'configuration'

    def test_check_config_short_secret_key(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()
        self.mock_config.security.secret_key = "short"
        self.mock_config.environment = "production"
        result = checker._check_config()
        assert result.status == HealthStatus.DEGRADED
        assert "issues" in result.details

    def test_check_config_default_secret_in_production(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()
        self.mock_config.security.secret_key = "acas-pro-secret-key-change-me"
        self.mock_config.environment = "production"
        result = checker._check_config()
        assert result.status == HealthStatus.DEGRADED

    # ------------------------------------------------------------------
    # _check_disk_space  (uses shutil.disk_usage → patch at shutil level)
    # ------------------------------------------------------------------

    def test_check_disk_space_healthy(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        with patch('shutil.disk_usage',
                   return_value=MagicMock(free=10*(1024**3),
                                          total=100*(1024**3),
                                          used=90*(1024**3))), \
             patch('os.makedirs'):
            checker = HealthChecker()
            result = checker._check_disk_space()
            assert result.status == HealthStatus.HEALTHY

    def test_check_disk_space_critical(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        with patch('shutil.disk_usage',
                   return_value=MagicMock(free=0.5*(1024**3),
                                          total=100*(1024**3),
                                          used=99.5*(1024**3))), \
             patch('os.makedirs'):
            checker = HealthChecker()
            result = checker._check_disk_space()
            assert result.status == HealthStatus.UNHEALTHY

    def test_check_disk_space_warning(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        with patch('shutil.disk_usage',
                   return_value=MagicMock(free=3*(1024**3),
                                          total=100*(1024**3),
                                          used=97*(1024**3))), \
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

    # ------------------------------------------------------------------
    # _check_llm
    # ------------------------------------------------------------------

    def test_check_llm_disabled(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()
        self.mock_config.llm.enabled = False
        result = checker._check_llm()
        assert result.status == HealthStatus.DEGRADED
        assert "disabled" in result.message.lower() or \
               "disabled" in str(result.details).lower()

    def test_check_llm_no_api_key(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()
        self.mock_config.llm.enabled = True
        self.mock_config.llm.api_key = None
        result = checker._check_llm()
        assert result.status == HealthStatus.DEGRADED

    def test_check_llm_configured(self):
        from acas_pro.web.health import HealthChecker, HealthStatus
        checker = HealthChecker()

        self.mock_config.llm.enabled = True
        self.mock_config.llm.api_key = "test-key"
        self.mock_config.llm.provider = "openai"
        self.mock_config.llm.model = "gpt-4"
        self.mock_config.llm.base_url = ""

        # Mock LLM client module so the import inside _check_llm succeeds
        mock_llm_client = MagicMock()
        mock_llm_client.LLMClient = MagicMock()
        mock_llm_client.LLMConfig = MagicMock()
        # LLMProvider("openai") must succeed → make constructor return a truthy obj
        mock_provider_enum = MagicMock()
        mock_provider_enum.__str__ = lambda self: "LLMProvider.OPENAI"
        mock_llm_client.LLMProvider = type(
            "FakeLLMProvider", (),
            {"__init__": lambda self, v: None,
             "__repr__": lambda self: "OPENAI",
             "value": "openai"}
        )
        sys.modules['acas_pro.llm.llm_client'] = mock_llm_client

        result = checker._check_llm()
        assert result.status == HealthStatus.HEALTHY
