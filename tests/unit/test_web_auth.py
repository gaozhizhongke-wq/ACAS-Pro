# -*- coding: utf-8 -*-
"""Tests for ACAS Pro auth routes - fully isolated by re-importing per test"""
import sys
import json
import types
import pytest

sys.path.insert(0, r'C:\Users\HUAWEI\.qclaw\workspace-hermes\ACAS-Pro\src')

# We deliberately re-import auth per test to avoid cross-test pollution.
# The _make_isolated_app() helper builds a fresh Flask app with
# completely mocked module-level dependencies for acas_pro.core.security
# and acas_pro.services.user_service.

def _make_isolated_app(monkeypatch, *, register_ok=True, login_ok=True,
                       rate_limit_allowed=True):
    """
    Create a fresh Flask app with auth blueprint.
    All external deps are mocked via monkeypatch BEFORE importing auth,
    so auth.py's `import acas_pro.core.security as _sec` picks up the mocks.
    """
    # 1. Mock acas_pro.core.security module attributes
    import acas_pro.core.security as _sec_mod
    import acas_pro.core.config as _cfg_mod

    # rate_limiter
    mock_rl = type('MockRL', (), {
        'is_allowed': lambda self, *a, **kw: rate_limit_allowed,
        'record_attempt': lambda self, *a, **kw: None,
    })()
    monkeypatch.setattr(_sec_mod, 'rate_limiter', mock_rl, raising=False)

    # password_validator
    monkeypatch.setattr(_sec_mod, 'password_validator', type('PV', (), {
        'validate': staticmethod(lambda pw: (True, ''))
    })(), raising=False)

    # JWTManager
    _jwt_store = {}
    class MockJWTMgr:
        def generate_token(self, user_id, extra_claims=None):
            tok = f'jwt_{user_id}'
            _jwt_store[tok] = {'sub': user_id, **(extra_claims or {})}
            return tok
        def verify_token(self, token, expected_type=None):
            return _jwt_store.get(token)
    monkeypatch.setattr(_sec_mod, 'JWTManager', MockJWTMgr(), raising=False)

    # 2. Mock acas_pro.services.user_service.user_service
    import acas_pro.services.user_service as _us_mod
    mock_profile = type('P', (), {'id': 'u1', 'account': 'test', 'nickname': 'Test'})()
    class MockUS:
        def register(self, account, password, nickname=None):
            return (True, '', mock_profile) if register_ok else (False, 'Account already exists', None)
        def login(self, account, password):
            return (True, '', mock_profile) if login_ok else (False, 'Invalid credentials', None)
    monkeypatch.setattr(_us_mod, 'user_service', MockUS(), raising=False)

    # 3. Mock config
    monkeypatch.setattr(_cfg_mod, 'config', type('C', (), {
        'security': type('S', (), {'secret_key': 'x' * 32})()
    })(), raising=False)

    # 4. Build fresh Flask app and re-import auth blueprint
    #    to pick up the mocked module attributes
    from flask import Flask
    # Force reload of auth module so it picks up mocked _sec / _us_mod
    mod_name = 'acas_pro.web.routes.auth'
    if mod_name in sys.modules:
        # Remove cached module and its sub-attrs so reimport is clean
        del sys.modules[mod_name]
    from acas_pro.web.routes.auth import bp as auth_bp, generate_token, verify_token

    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret'
    app.register_blueprint(auth_bp)
    return app, generate_token, verify_token


# ---------------------------------------------------------------
# TestAuthRegister
# ---------------------------------------------------------------

class TestAuthRegister:
    def test_register_success(self, monkeypatch):
        app, _, _ = _make_isolated_app(monkeypatch, register_ok=True, rate_limit_allowed=True)
        client = app.test_client()
        resp = client.post('/api/auth/register', json={
            'account': 'test', 'password': 'Test123!', 'nickname': 'Test'
        })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True

    def test_register_missing_account(self, monkeypatch):
        app, _, _ = _make_isolated_app(monkeypatch)
        client = app.test_client()
        resp = client.post('/api/auth/register', json={'password': 'Test123!'})
        assert resp.status_code == 400

    def test_register_missing_password(self, monkeypatch):
        app, _, _ = _make_isolated_app(monkeypatch)
        client = app.test_client()
        resp = client.post('/api/auth/register', json={'account': 'test'})
        assert resp.status_code == 400

    def test_register_weak_password(self, monkeypatch):
        import acas_pro.core.security as _sec_mod
        monkeypatch.setattr(_sec_mod, 'password_validator', type('PV', (), {
            'validate': staticmethod(lambda pw: (False, 'too weak'))
        })(), raising=False)
        app, _, _ = _make_isolated_app(monkeypatch)
        client = app.test_client()
        resp = client.post('/api/auth/register', json={
            'account': 'test', 'password': 'weak'
        })
        assert resp.status_code == 400

    def test_register_rate_limited(self, monkeypatch):
        app, _, _ = _make_isolated_app(monkeypatch, rate_limit_allowed=False)
        client = app.test_client()
        resp = client.post('/api/auth/register', json={
            'account': 'test', 'password': 'Test123!'
        })
        assert resp.status_code == 429

    def test_register_duplicate(self, monkeypatch):
        app, _, _ = _make_isolated_app(monkeypatch, register_ok=False)
        client = app.test_client()
        resp = client.post('/api/auth/register', json={
            'account': 'test', 'password': 'Test123!'
        })
        assert resp.status_code == 409


# ---------------------------------------------------------------
# TestAuthLogin
# ---------------------------------------------------------------

class TestAuthLogin:
    def test_login_success(self, monkeypatch):
        app, _, _ = _make_isolated_app(monkeypatch, login_ok=True, rate_limit_allowed=True)
        client = app.test_client()
        resp = client.post('/api/auth/login', json={
            'account': 'test', 'password': 'Test123!'
        })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True

    def test_login_invalid_credentials(self, monkeypatch):
        app, _, _ = _make_isolated_app(monkeypatch, login_ok=False)
        client = app.test_client()
        resp = client.post('/api/auth/login', json={
            'account': 'test', 'password': 'wrong'
        })
        assert resp.status_code == 401

    def test_login_missing_account(self, monkeypatch):
        app, _, _ = _make_isolated_app(monkeypatch)
        client = app.test_client()
        resp = client.post('/api/auth/login', json={'password': 'Test123!'})
        assert resp.status_code == 400

    def test_login_rate_limited(self, monkeypatch):
        app, _, _ = _make_isolated_app(monkeypatch, rate_limit_allowed=False)
        client = app.test_client()
        resp = client.post('/api/auth/login', json={
            'account': 'test', 'password': 'Test123!'
        })
        assert resp.status_code == 429


# ---------------------------------------------------------------
# TestAuthMe
# ---------------------------------------------------------------

class TestAuthMe:
    def test_me_authenticated(self, monkeypatch):
        from flask import g
        from acas_pro.web.routes.auth import auth_me
        app, _, _ = _make_isolated_app(monkeypatch)
        ctx = app.app_context()
        ctx.push()
        try:
            g.user = {'user_id': 'u1', 'account': 'test'}
            resp = auth_me()
            assert resp.status_code == 200
            data = json.loads(resp.get_data())
            assert data['user_id'] == 'u1'
        finally:
            ctx.pop()

    def test_me_unauthenticated(self, monkeypatch):
        from flask import g
        from acas_pro.web.routes.auth import auth_me
        app, _, _ = _make_isolated_app(monkeypatch)
        ctx = app.app_context()
        ctx.push()
        try:
            g.user = None
            resp = auth_me()
            assert resp[1] == 401
        finally:
            ctx.pop()


# ---------------------------------------------------------------
# TestTokenFunctions
# ---------------------------------------------------------------

class TestTokenFunctions:
    def test_generate_token(self, monkeypatch):
        app, generate_token, _ = _make_isolated_app(monkeypatch)
        tok = generate_token('u1', 'test')
        assert isinstance(tok, str)
        assert len(tok) > 0

    def test_verify_token_success(self, monkeypatch):
        app, generate_token, verify_token = _make_isolated_app(monkeypatch)
        tok = generate_token('u1', 'test')
        payload = verify_token(tok)
        assert payload is not None
        assert payload['sub'] == 'u1'

    def test_verify_token_legacy(self, monkeypatch):
        """JWTManager returns None -> fallback to jwt.decode"""
        import acas_pro.core.security as _sec_mod
        import jwt as _jwt
        monkeypatch.setattr(_sec_mod.JWTManager, 'verify_token',
                           staticmethod(lambda tok, expected_type=None: None),
                           raising=False)
        monkeypatch.setattr(_jwt, 'decode',
                           staticmethod(lambda *a, **kw: {'user_id': 'u1', 'account': 'test'}),
                           raising=False)
        app, _, verify_token = _make_isolated_app(monkeypatch)
        payload = verify_token('tok')
        assert payload is not None
        assert payload['user_id'] == 'u1'

    def test_verify_token_invalid(self, monkeypatch):
        """Both JWTManager and jwt.decode fail -> returns None"""
        import acas_pro.core.security as _sec_mod
        import jwt as _jwt
        monkeypatch.setattr(_sec_mod.JWTManager, 'verify_token',
                           staticmethod(lambda tok, expected_type=None: None),
                           raising=False)
        def _bad_decode(*a, **kw):
            raise Exception('bad token')
        monkeypatch.setattr(_jwt, 'decode', _bad_decode, raising=False)
        app, _, verify_token = _make_isolated_app(monkeypatch)
        payload = verify_token('bad')
        assert payload is None
