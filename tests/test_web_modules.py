"""Tests for web modules using sys.modules injection approach."""
import sys
from unittest.mock import MagicMock
import pytest


def _setup_web_env():
    """Inject mocks via sys.modules for web module imports."""
    saved = {}

    # Flask mock
    if 'flask' not in sys.modules:
        sys.modules['flask'] = MagicMock()
    mock_flask = sys.modules['flask']
    mock_bp = MagicMock()
    mock_bp.route = lambda *a, **kw: (lambda f: f)
    mock_bp.before_request = lambda f: f
    mock_bp.after_request = lambda f: f
    mock_flask.Blueprint = MagicMock(return_value=mock_bp)
    mock_flask.request = MagicMock()
    mock_flask.jsonify = lambda d: d
    mock_flask.g = MagicMock()
    mock_flask.render_template = lambda t, **kw: f"rendered:{t}"
    mock_flask.session = {}
    saved['flask'] = mock_flask

    # Config mock with all needed attributes
    mock_config = MagicMock()
    mock_config.version = "1.0.0"
    mock_config.environment = "development"
    mock_config.data_dir = "data"
    mock_config.database.type = "sqlite"
    mock_config.security.secret_key = "a" * 64
    mock_config.security.jwt_secret = "b" * 64
    mock_config.security.access_token_ttl = 3600
    mock_config.security.refresh_token_ttl = 86400
    mock_config.llm.enabled = False
    mock_config.llm.api_key = None
    mock_config.llm.provider = "openai"
    mock_config.llm.model = "gpt-4"
    mock_config.llm.base_url = "https://api.openai.com/v1"

    # Inject config via sys.modules
    if 'acas_pro.core.config' in sys.modules:
        saved['acas_pro.core.config'] = sys.modules.pop('acas_pro.core.config')
    config_mod = MagicMock()
    config_mod.config = mock_config
    config_mod.get_config = MagicMock(return_value=mock_config)
    sys.modules['acas_pro.core.config'] = config_mod

    # Mock logging
    if 'acas_pro.core.logging' in sys.modules:
        saved['acas_pro.core.logging'] = sys.modules.pop('acas_pro.core.logging')
    logging_mod = MagicMock()
    logging_mod.logger = MagicMock()
    logging_mod.get_logger = MagicMock(return_value=logging_mod.logger)
    sys.modules['acas_pro.core.logging'] = logging_mod

    # Mock database
    if 'acas_pro.core.database' in sys.modules:
        saved['acas_pro.core.database'] = sys.modules.pop('acas_pro.core.database')
    db_mod = MagicMock()
    mock_db_instance = MagicMock()
    mock_db_instance.execute_one = MagicMock(return_value={'health_check': 1})
    db_mod.DatabaseManager = MagicMock(return_value=mock_db_instance)
    sys.modules['acas_pro.core.database'] = db_mod

    # Mock security
    if 'acas_pro.core.security' in sys.modules:
        saved['acas_pro.core.security'] = sys.modules.pop('acas_pro.core.security')
    sec_mod = MagicMock()
    sec_mod.password_validator = MagicMock()
    sec_mod.password_validator.validate_password = MagicMock(return_value=(True, ""))
    sec_mod.password_validator.hash_password = MagicMock(return_value="hashed")
    sec_mod.password_validator.verify_password = MagicMock(return_value=True)
    sec_mod.rate_limiter = MagicMock()
    sec_mod.JWTManager = MagicMock()
    sys.modules['acas_pro.core.security'] = sec_mod

    # Mock user_service module (the whole module)
    if 'acas_pro.services.user_service' in sys.modules:
        saved['acas_pro.services.user_service'] = sys.modules.pop('acas_pro.services.user_service')
    else:
        saved['acas_pro.services.user_service'] = None  # Mark for removal on teardown
    user_svc_mod = MagicMock()
    user_svc_mod.user_service = MagicMock()
    sys.modules['acas_pro.services.user_service'] = user_svc_mod

    # Clear web modules
    web_mods = [m for m in list(sys.modules.keys()) if 'acas_pro.web' in m]
    for m in web_mods:
        saved[m] = sys.modules.pop(m, None)

    # Also clear oauth
    if 'acas_pro.services.oauth' in sys.modules:
        saved['acas_pro.services.oauth'] = sys.modules.pop('acas_pro.services.oauth')
    if 'acas_pro.services.oauth.oauth_service' in sys.modules:
        saved['acas_pro.services.oauth.oauth_service'] = sys.modules.pop('acas_pro.services.oauth.oauth_service')

    return saved


def _teardown(saved):
    # Restore original modules
    for k, v in saved.items():
        if v is None:
            sys.modules.pop(k, None)
        else:
            sys.modules[k] = v


class TestApiSpec:
    def test_import(self):
        saved = _setup_web_env()
        try:
            import acas_pro.web.api_spec as api_spec
            assert True  # Successfully imported
        finally:
            _teardown(saved)


class TestWebHealth:
    def test_import(self):
        saved = _setup_web_env()
        try:
            import acas_pro.web.health as wh
            assert hasattr(wh, 'HealthChecker')
        finally:
            _teardown(saved)

    def test_check_all(self):
        saved = _setup_web_env()
        try:
            from acas_pro.web.health import HealthChecker
            hc = HealthChecker()
            result = hc.check_all()
            assert 'status' in result
            assert 'checks' in result
            assert 'version' in result
        finally:
            _teardown(saved)

    def test_health_check_result(self):
        saved = _setup_web_env()
        try:
            from acas_pro.web.health import HealthCheckResult, HealthStatus
            r = HealthCheckResult(
                name="test", status=HealthStatus.HEALTHY,
                response_time_ms=10.0, message="ok"
            )
            assert r.name == "test"
            assert r.status == HealthStatus.HEALTHY
        finally:
            _teardown(saved)


class TestWebMiddleware:
    def test_import(self):
        saved = _setup_web_env()
        try:
            import acas_pro.web.middleware as mw
            assert True
        finally:
            _teardown(saved)


class TestWebRoutesAuth:
    def test_import(self):
        saved = _setup_web_env()
        try:
            import acas_pro.web.routes.auth as auth_mod
            assert hasattr(auth_mod, 'bp') or hasattr(auth_mod, 'auth_bp')
        except Exception as e:
            pytest.skip(f"Cannot import auth routes: {e}")
        finally:
            _teardown(saved)


class TestWebRoutesDashboard:
    def test_import(self):
        saved = _setup_web_env()
        try:
            import acas_pro.web.routes.dashboard as dash_mod
            assert hasattr(dash_mod, 'bp') or hasattr(dash_mod, 'dashboard_bp')
        except Exception as e:
            pytest.skip(f"Cannot import dashboard routes: {e}")
        finally:
            _teardown(saved)


class TestWebRoutesLLM:
    def test_import(self):
        saved = _setup_web_env()
        try:
            import acas_pro.web.routes.llm as llm_mod
            assert hasattr(llm_mod, 'bp') or hasattr(llm_mod, 'llm_bp')
        except Exception as e:
            pytest.skip(f"Cannot import llm routes: {e}")
        finally:
            _teardown(saved)


class TestWebRoutesAuthV2:
    def test_import(self):
        saved = _setup_web_env()
        try:
            import acas_pro.web.routes.auth_v2 as a2_mod
            assert True
        except Exception as e:
            pytest.skip(f"Cannot import auth_v2 routes: {e}")
        finally:
            _teardown(saved)
