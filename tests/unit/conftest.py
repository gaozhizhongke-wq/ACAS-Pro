# -*- coding: utf-8 -*-
"""
Local conftest for tests/unit/ directory.
"""

from pathlib import Path

import pytest
import sys
import importlib


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Detect which test corrupts acas_pro modules."""
    if call.when != 'call':
        return
    # Check if jsonify in llm module is still a function
    llm_mod = sys.modules.get('acas_pro.web.routes.llm')
    if llm_mod is not None and not hasattr(llm_mod, 'mock_calls'):
        j = getattr(llm_mod, 'jsonify', None)
        if j is not None and hasattr(j, 'mock_calls'):
            import os
            os.makedirs('logs', exist_ok=True)
            with open('logs/mock_diag.txt', 'a') as f:
                f.write(f'jsonify corrupted after {item.nodeid}\n')
    # Check security
    sec = sys.modules.get('acas_pro.core.security')
    if sec is not None and hasattr(sec, 'mock_calls'):
        import os
        os.makedirs('logs', exist_ok=True)
        with open('logs/mock_diag.txt', 'a') as f:
            f.write(f'security MagicMock after {item.nodeid}\n')


@pytest.fixture(autouse=True, scope="function")
def _reset_lazy_singletons():
    """Gentle reset for unit tests: clear jwt mocks and reset singletons
    WITHOUT deleting acas_pro modules from sys.modules.
    """
    # Clean up jwt mock pollution
    if 'jwt' in sys.modules and hasattr(sys.modules['jwt'], 'mock_calls'):
        del sys.modules['jwt']

    # Remove only mock stubs (MagicMock objects) left by other test files.
    mock_modules = [m for m in list(sys.modules.keys())
                    if m.startswith('acas_pro') and hasattr(sys.modules[m], 'mock_calls')]
    for m in mock_modules:
        del sys.modules[m]

    # Re-import config/logging if they were removed
    for mod_name in ['acas_pro.core.config', 'acas_pro.core.logging']:
        if mod_name not in sys.modules:
            try:
                importlib.import_module(mod_name)
            except Exception:
                pass

    # Reset lazy singletons
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
    try:
        from acas_pro.services.account_manager import _reset_lazy
        _reset_lazy()
    except Exception:
        pass
    try:
        from acas_pro.core.database import reset_db
        reset_db()
    except Exception:
        pass

    yield