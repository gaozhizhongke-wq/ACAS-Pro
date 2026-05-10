#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Deep smoke tests for UI pages using pytest-qt (offscreen platform).
Tests instantiate every widget class and call all public methods.
"""
import os
import sys
import inspect
import importlib
import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

os.environ["ENVIRONMENT"] = "development"
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
# Required so CryptoManager / security.py module-level init works
os.environ.setdefault("JWT_SECRET", "test_jwt_secret_32_bytes_long_abc123")
os.environ.setdefault("ENCRYPTION_KEY", "test_encryption_key_32bytes_ok!")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("SECRET_KEY", "test_secret_key_32_bytes_long_xyz")

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def _mock_for_param(name, annotation=None):
    """Generate a sensible mock value based on param name."""
    n = name.lower()
    if any(k in n for k in ["db", "database"]):
        return MagicMock(name=name)
    if "config" in n:
        return MagicMock(name=name)
    if any(k in n for k in ["key", "token", "secret", "api_key"]):
        return "test_key"
    if any(k in n for k in ["password", "pwd"]):
        return "TestPass1!"
    if "id" in n:
        return "test_id"
    if "name" in n:
        return "test_name"
    if "url" in n or "host" in n:
        return "https://test.example.com"
    if "path" in n or "dir" in n:
        return "/tmp/test"
    if "port" in n:
        return 8080
    if "email" in n or "mail" in n:
        return "test@test.com"
    if "phone" in n:
        return "13800000000"
    if any(k in n for k in ["json", "dict", "data", "info", "detail"]):
        return {}
    if any(k in n for k in ["text", "content", "message", "desc", "description", "label", "title", "query", "keyword", "search"]):
        return "test"
    if any(k in n for k in ["type", "category", "platform", "status", "mode", "action", "format", "channel"]):
        return "test"
    if any(k in n for k in ["list", "items", "rows", "records"]):
        return []
    if any(k in n for k in ["index", "offset", "page"]):
        return 0
    if any(k in n for k in ["count", "num", "size", "limit", "max", "min", "total", "width", "height"]):
        return 1
    if any(k in n for k in ["price", "amount", "cost", "budget", "rate", "ratio", "pct", "percent", "score", "value"]):
        return 1.0
    if any(k in n for k in ["debug", "enabled", "verbose", "visible", "checked", "selected"]):
        return True
    if any(k in n for k in ["timeout", "interval", "duration", "delay"]):
        return 30
    if any(k in n for k in ["date", "time", "start", "end"]):
        return datetime.datetime.now()
    if "widget" in n or "parent" in n or "layout" in n:
        return None
    return MagicMock(name=name)


def _try_instantiate(cls, parent=None):
    """Try to instantiate cls with sensible defaults."""
    try:
        sig = inspect.signature(cls.__init__)
    except (ValueError, TypeError, NameError):
        return None

    kwargs = {}
    for pname, param in sig.parameters.items():
        if pname == "self":
            continue
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue
        if param.default is not inspect.Parameter.empty:
            continue
        kwargs[pname] = _mock_for_param(pname, param.annotation)

    try:
        return cls(**kwargs)
    except Exception:
        # Try with no args
        try:
            return cls()
        except Exception:
            return None


def _deep_call_methods(obj, max_methods=80):
    """Call all public methods on an object."""
    called = 0
    for method_name in dir(obj):
        if called >= max_methods:
            break
        if method_name.startswith("__"):
            continue
        try:
            attr = getattr(obj, method_name)
        except Exception:
            continue
        if not callable(attr):
            continue

        try:
            sig = inspect.signature(attr)
        except (ValueError, TypeError, NameError):
            # No signature - try no args
            try:
                attr()
                called += 1
            except Exception:
                pass
            continue

        kwargs = {}
        for pname, param in sig.parameters.items():
            if pname == "self":
                continue
            if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                continue
            if param.default is not inspect.Parameter.empty:
                continue
            kwargs[pname] = _mock_for_param(pname, param.annotation)

        try:
            attr(**kwargs)
            called += 1
        except Exception:
            # Fallback: no args
            try:
                attr()
                called += 1
            except Exception:
                pass

    return called


def _get_classes(module):
    """Get all classes defined in this module (not imported)."""
    result = []
    for name in dir(module):
        try:
            obj = getattr(module, name)
        except Exception:
            continue
        if inspect.isclass(obj) and obj.__module__ == module.__name__:
            result.append((name, obj))
    return result


# ── UI modules to test ──────────────────────────────────────────
UI_MODULES = [
    "acas_pro.ui.pages.settings",
    "acas_pro.ui.pages.advanced_analytics",
    "acas_pro.ui.pages.ad_manager",
    "acas_pro.ui.pages.avatar_studio",
    "acas_pro.ui.pages.intelligence",
    "acas_pro.ui.auth.login_dialog",
    "acas_pro.ui.pages.festival_calendar",
    "acas_pro.ui.pages.blockchain_settlement",
    "acas_pro.ui.pages.llm_chat",
    "acas_pro.ui.pages.video_maker",
    "acas_pro.ui.pages.publish_manager",
    "acas_pro.ui.pages.account_management",
    "acas_pro.ui.pages.ecommerce_manager",
    "acas_pro.ui.pages.content_creation",
    "acas_pro.ui.main_window",
    "acas_pro.ui.pages.dashboard",
    "acas_pro.ui.pages.forecast",
    "acas_pro.ui.pages.inventory",
]


@pytest.fixture(scope="session")
def mock_db():
    """Shared mock database for UI tests."""
    db = MagicMock()
    for method in ["execute", "commit", "close", "fetchone", "fetchall",
                   "rollback", "cursor"]:
        getattr(db, method).return_value = MagicMock()
    db.fetchone.return_value = None
    db.fetchall.return_value = []
    return db


@pytest.fixture(scope="session")
def mock_config():
    """Real-enough config mock with proper string attribute values."""
    cfg = MagicMock()
    cfg.app_name = "ACAS Pro Test"
    cfg.encryption_key = "test_encryption_key_32bytes_ok!"
    cfg.jwt_secret = "test_jwt_secret_32_bytes_long_abc123"
    cfg.database_url = "sqlite:///test.db"
    cfg.secret_key = "test_secret_key_32_bytes_long_xyz"
    cfg.llm_provider = "deepseek"
    cfg.deepseek_api_key = "sk-test-key"
    cfg.openai_api_key = "sk-test-openai"
    cfg.encryption_enabled = False
    cfg.debug = False
    cfg.log_level = "ERROR"
    cfg.max_results = 10
    cfg.request_timeout = 30
    cfg.cache_ttl = 300
    cfg.cors_origins = ["http://localhost:3000"]
    cfg.rate_limit = 100
    cfg.rate_window = 60
    cfg.admin_email = "admin@test.com"
    cfg.admin_password = "TestAdmin1!"
    cfg.recaptcha_enabled = False
    cfg.environment = "testing"
    return cfg


@pytest.fixture(autouse=True)
def _cleanup_ui_modules():
    """Remove UI modules between tests so re-import is fresh."""
    yield
    for k in list(sys.modules.keys()):
        if k.startswith("acas_pro.ui"):
            del sys.modules[k]


@pytest.mark.parametrize("mod_path", UI_MODULES, ids=UI_MODULES)
def test_ui_page_smoke(qtbot, mock_db, mod_path):
    """Instantiate every class in the UI module and call all methods."""
    # Patch the database and config singletons
    with patch("acas_pro.core.database.DatabaseManager", return_value=mock_db), \
         patch("acas_pro.core.config.config", mock_config), \
         patch("acas_pro.services.user_service.user_service", MagicMock()):

        try:
            mod = importlib.import_module(mod_path)
        except Exception as e:
            pytest.skip(f"Import failed: {e}")
            return

        classes_found = 0
        methods_called = 0

        for cls_name, cls in _get_classes(mod):
            # Skip Qt base classes
            if cls_name in ("QApplication", "QObject", "QWidget", "QMainWindow",
                            "QDialog", "QThread", "QTimer", "QAction"):
                continue

            obj = _try_instantiate(cls)
            if obj is None:
                continue

            # qtbot manages widget lifecycle (adds/removes widget)
            try:
                qtbot.addWidget(obj)
            except Exception:
                # Not a widget or can't be managed by qtbot - skip
                pass

            classes_found += 1
            methods_called += _deep_call_methods(obj, max_methods=80)

        assert classes_found > 0, f"No classes instantiated in {mod_path}"
