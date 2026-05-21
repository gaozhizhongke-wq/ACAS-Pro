#!/usr/bin/env python3
"""Pre-mock dependencies for hard-to-import modules."""

import sys
from unittest.mock import MagicMock

# Pre-populate common missing dependencies
if 'numpy' not in sys.modules:
    sys.modules['numpy'] = MagicMock()
if 'torch' not in sys.modules:
    sys.modules['torch'] = MagicMock()
if 'cv2' not in sys.modules:
    sys.modules['cv2'] = MagicMock()
if 'PIL' not in sys.modules:
    sys.modules['PIL'] = MagicMock()
if 'PIL.Image' not in sys.modules:
    sys.modules['PIL.Image'] = MagicMock()
if 'feedparser' not in sys.modules:
    sys.modules['feedparser'] = MagicMock()
if 'apscheduler' not in sys.modules:
    sys.modules['apscheduler'] = MagicMock()
if 'jose' not in sys.modules:
    sys.modules['jose'] = MagicMock()

# Pre-create config object for modules that need it
class MockConfig:
    database_url = "sqlite:///test.db"
    secret_key = "test-secret"
    jwt_secret = "jwt-test-secret"
    weibo_app_key = "test_app_key"
    weibo_app_secret = "test_secret"
    
mock_cfg = MockConfig()
sys.modules['acas_pro.core.config'] = MagicMock()
sys.modules['acas_pro.core.config'].config = mock_cfg