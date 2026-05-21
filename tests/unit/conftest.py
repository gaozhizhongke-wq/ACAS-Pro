# -*- coding: utf-8 -*-
"""
Local conftest for tests/unit/ directory.

Overrides the global _reset_lazy_singletons fixture because test_security.py
uses import-time patching of _cfg() that is broken when modules are deleted
and re-imported between tests.

Pytest allows conftest fixtures in subdirectories to override parent fixtures.
"""

import pytest
import sys


@pytest.fixture(autouse=True, scope="function")
def _reset_lazy_singletons():
    """Gentle reset for unit tests: clear jwt mocks and reset singletons
    WITHOUT deleting acas_pro modules from sys.modules.

    This preserves import-time patches in test_security.py while still
    cleaning up external mock pollution.
    """
    # Clean up jwt mock pollution
    if 'jwt' in sys.modules and hasattr(sys.modules['jwt'], 'mock_calls'):
        del sys.modules['jwt']

    # Reset lazy singletons without deleting modules
    try:
        from acas_pro.core.security import _reset_lazy_instances
        _reset_lazy_instances()
    except Exception:
        pass
    try:
        from acas_pro.core.config import _clear
        _clear()
    except Exception:
        pass

    yield
