"""
Pytest configuration and shared fixtures for ACAS Pro tests
"""
import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Mock PySide6 for UI tests
sys.modules['PySide6'] = MagicMock()
sys.modules['PySide6.QtWidgets'] = MagicMock()
sys.modules['PySide6.QtCore'] = MagicMock()
sys.modules['PySide6.QtGui'] = MagicMock()
sys.modules['PySide6.QtCharts'] = MagicMock()

# Mock Flask for web tests
sys.modules['flask'] = MagicMock()
sys.modules['flask_cors'] = MagicMock()
sys.modules['flask_limiter'] = MagicMock()


@pytest.fixture
def temp_dir():
    """Provide a temporary directory for tests"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_home(tmp_path):
    """Mock Path.home() to return a temporary directory"""
    with patch.object(Path, 'home', return_value=tmp_path):
        yield tmp_path


@pytest.fixture
def clean_env():
    """Clean environment variables for tests"""
    original_env = os.environ.copy()
    # Clear sensitive env vars
    for key in list(os.environ.keys()):
        if any(x in key.upper() for x in ['SECRET', 'KEY', 'TOKEN', 'PASSWORD']):
            del os.environ[key]
    yield
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_config_data():
    """Sample configuration data for tests"""
    return {
        "name": "Test Config",
        "version": "1.0.0",
        "environment": "development",
        "debug": True,
        "database": {
            "type": "sqlite",
            "name": "test.db"
        },
        "security": {
            "secret_key": "test_secret_key_32_chars_long!!",
            "password_min_length": 8
        },
        "llm": {
            "enabled": False
        }
    }
