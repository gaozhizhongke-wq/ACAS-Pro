# -*- coding: utf-8 -*-
"""
Local conftest for tests/unit/ directory.

Minimal cleanup only:
- NEVER delete acas_pro.* from sys.modules (breaks monkeypatch.setattr)
- NEVER call _reset_lazy_instances() (recreates real singletons, undoing mocks)
- ONLY clean up jwt if it was fully replaced by a MagicMock
"""
import sys
import pytest


@pytest.fixture(autouse=True, scope="function")
def _isolation_cleanup():
    """
    Lightweight cleanup that runs after each test.
    Does NOT delete modules or reset singletons — that's the test's job via monkeypatch.
    """
    yield
    # Only clean up jwt if it's a MagicMock (left behind by a bad test)
    if 'jwt' in sys.modules and hasattr(sys.modules['jwt'], 'mock_calls'):
        del sys.modules['jwt']
