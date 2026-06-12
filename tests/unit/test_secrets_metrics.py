#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Unit tests for core/secrets_manager.py and monitoring/metrics.py."""

import os
from unittest.mock import MagicMock
import sys
import pytest

if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()


class TestSecretsManager:
    def test_get_from_env(self):
        from acas_pro.core.secrets_manager import SecretsManager
        os.environ['TEST_SECRET_KEY'] = 'env_value'
        try:
            mgr = SecretsManager()
            result = mgr.get('TEST_SECRET_KEY')
            assert result == 'env_value'
        finally:
            del os.environ['TEST_SECRET_KEY']

    def test_get_fallback(self):
        from acas_pro.core.secrets_manager import SecretsManager
        mgr = SecretsManager()
        result = mgr.get('nonexistent_key_xyz', fallback='default')
        assert result == 'default'

    def test_get_not_found(self):
        from acas_pro.core.secrets_manager import SecretsManager
        mgr = SecretsManager()
        result = mgr.get('nonexistent_key_xyz')
        assert result is None

    def test_env_map_resolution(self):
        from acas_pro.core.secrets_manager import SecretsManager
        os.environ['DEEPSEEK_API_KEY'] = 'sk-test'
        try:
            mgr = SecretsManager()
            result = mgr.get('deepseek_api_key')
            assert result == 'sk-test'
        finally:
            del os.environ['DEEPSEEK_API_KEY']

    def test_production_warning(self):
        from acas_pro.core.secrets_manager import SecretsManager
        mgr = SecretsManager(is_production=True)
        # Using fallback for prod-only secret should warn but not crash
        result = mgr.get('SECRET_KEY', fallback='insecure')
        assert result == 'insecure'

    def test_require_raises(self):
        from acas_pro.core.secrets_manager import SecretsManager
        mgr = SecretsManager()
        with pytest.raises(ValueError, match="not found"):
            mgr.require('nonexistent_xyz_123')

    def test_mask(self):
        from acas_pro.core.secrets_manager import SecretsManager
        mgr = SecretsManager()
        assert mgr.mask('sk-abcdef1234567890') == 'sk-a...7890'
        assert mgr.mask('ab') == '***'

    def test_is_set(self):
        from acas_pro.core.secrets_manager import SecretsManager
        mgr = SecretsManager()
        assert mgr.is_set('nonexistent_xyz_123') == False  # noqa: E712

    def test_validate_production(self):
        from acas_pro.core.secrets_manager import SecretsManager
        mgr = SecretsManager()
        missing = mgr.validate_production()
        assert isinstance(missing, list)


class TestMetricsModule:
    def test_metrics_importable(self):
        from acas_pro.monitoring import metrics
        assert hasattr(metrics, 'REQUEST_COUNT')
        assert hasattr(metrics, 'REQUEST_DURATION')
        assert hasattr(metrics, 'ACTIVE_USERS')

    def test_counter_inc(self):
        from acas_pro.monitoring.metrics import Counter
        c = Counter('test_counter', 'A test counter')
        c.inc()  # Should not raise

    def test_histogram_observe(self):
        from acas_pro.monitoring.metrics import Histogram
        h = Histogram('test_hist', 'A test histogram')
        h.observe(0.5)

    def test_gauge_set(self):
        from acas_pro.monitoring.metrics import Gauge
        g = Gauge('test_gauge', 'A test gauge')
        g.set(42)

    def test_info(self):
        from acas_pro.monitoring.metrics import Info
        i = Info('test_info', 'Test info')
        i.info({'version': '1.0'})

    def test_generate_latest(self):
        from acas_pro.monitoring.metrics import generate_latest
        data = generate_latest()
        assert isinstance(data, bytes)
