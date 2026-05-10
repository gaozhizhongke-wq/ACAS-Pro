#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Test Configuration
Pytest configuration and fixtures
"""
# noqa: B105 (测试文件中的硬编码值用于测试环境，非生产密钥)
import os
import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ── pytest-qt: use offscreen platform (no display required) ──
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')


def pytest_configure(config):
    """Configure pytest-qt for offscreen testing."""
    config.option.qt_flags = ['offscreen']


# ── pytest-qt hooks ──
@pytest.hookimpl(tryfirst=True)
def qtbot_wait_callback(timeout):
    """Reduce wait time for CI speed."""
    pass


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests"""
    dir_path = Path(tempfile.mkdtemp())
    yield dir_path
    shutil.rmtree(dir_path, ignore_errors=True)


@pytest.fixture
def temp_config(temp_dir):
    """Create temporary config for tests"""
    from acas_pro.core.config import AppConfig, DatabaseConfig, SecurityConfig
    # noqa: B105
    test_secret = os.environ.get('TEST_SECRET_KEY', 'test_secret_key_for_testing_only_32chars')
    config = AppConfig(
        data_dir=str(temp_dir / "data"),
        log_dir=str(temp_dir / "logs"),
        backup_dir=str(temp_dir / "backups"),
        database=DatabaseConfig(path=str(temp_dir / "data" / "test.db")),
        security=SecurityConfig(secret_key=test_secret)
    )
    
    # Ensure directories exist
    Path(config.data_dir).mkdir(parents=True, exist_ok=True)
    Path(config.log_dir).mkdir(parents=True, exist_ok=True)
    
    return config


@pytest.fixture
def temp_db(temp_config):
    """Create temporary database for tests"""
    from acas_pro.core.database import DatabaseManager
    
    # Reset singleton so each test gets a fresh DB instance
    DatabaseManager._instance = None
    with patch('acas_pro.core.database.config', temp_config):
        db = DatabaseManager()
    
    yield db
    
    # Cleanup happens in autouse cleanup fixture below


@pytest.fixture
def _temp_db_cleanup(temp_config):
    """Cleanup temp DB files after test"""
    yield
    
    # Force close any lingering connections
    import gc
    gc.collect()
    
    # Cleanup DB + WAL/SHM files
    db_path = Path(temp_config.database.path)
    for suffix in ['', '-wal', '-shm']:
        p = Path(str(db_path) + suffix)
        for attempt in range(3):
            try:
                if p.exists():
                    p.unlink(missing_ok=True)
                break
            except PermissionError:
                import time
                time.sleep(0.1)
    
    # Reset singleton
    from acas_pro.core.database import DatabaseManager
    DatabaseManager._instance = None


@pytest.fixture
def sample_user_data():
    """Sample user data for testing"""
    return {
        "account": "test@example.com",
        "password": "Test@123456",
        "nickname": "Test User",
        "email": "test@example.com",
        "phone": "13800138000",
        "region": "cn_northwest"
    }


@pytest.fixture
def sample_sales_data():
    """Sample sales data for forecasting tests"""
    import numpy as np
    from datetime import datetime, timedelta
    
    base = datetime(2024, 1, 1)
    dates = [base + timedelta(days=i) for i in range(90)]
    
    # Trend + seasonality + noise
    values = []
    for i in range(90):
        trend = 100 + i * 0.5
        seasonal = 20 * np.sin(2 * np.pi * i / 7)
        noise = np.random.normal(0, 5)
        values.append(max(0, trend + seasonal + noise))
    
    return list(zip(dates, values))
