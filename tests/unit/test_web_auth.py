# -*- coding: utf-8 -*-
"""Tests for ACAS Pro auth routes - correct patch targets"""
import sys
import json
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, 'src')

from acas_pro.web.routes.auth import bp as auth, generate_token, verify_token


@pytest.fixture
def app():
    from flask import Flask
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'test-secret'
    app.register_blueprint(auth)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


# ---------------------------------------------------------------
# Helpers — patch auth.py's module-level refs (the ONLY correct target)
# ---------------------------------------------------------------

def _mock_register(monkeypatch, *, register_ok=True):
    """Patch auth.py's _sec / _us_mod refs for register route."""
    # auth.py: _sec = acas_pro.core.security  →  patch auth._sec.rate_limiter etc.
    import acas_pro.web.routes.auth as _auth_mod
    import acas_pro.core.security as _sec_mod

    # rate_limiter — must be on the module object that auth.py reads from
    mock_rl = MagicMock()
    mock_rl.is_allowed.return_value = True
    monkeypatch.setattr(_sec_mod, 'rate_limiter', mock_rl)

    # password_validator
    mock_pv = MagicMock()
    mock_pv.validate.return_value = (True, '')
    monkeypatch.setattr(_sec_mod, 'password_validator', mock_pv)

    # JWTManager
    mock_jwt = MagicMock()
    mock_jwt.generate_token.return_value = 'tok_abc'
    monkeypatch.setattr(_sec_mod, 'JWTManager', mock_jwt)

    # user_service — patch the module attr that auth.py reads
    mock_us = MagicMock()
    profile = type('P', (), {'id': 'u1', 'account': 'test', 'nickname': 'Test'})()
    if register_ok:
        mock_us.register.return_value = (True, '', profile)
    else:
        mock_us.register.return_value = (False, 'Account already exists', None)
    import acas_pro.services.user_service as _us_mod
    monkeypatch.setattr(_us_mod, 'user_service', mock_us)

    # config (for verify_token legacy fallback)
    cfg = MagicMock()
    cfg.security.secret_key = 'x' * 32
    import acas_pro.core.config as _cfg_mod
    monkeypatch.setattr(_cfg_mod, 'config', cfg)

    return mock_rl, mock_us, mock_jwt


def _mock_login(monkeypatch, *, login_ok=True):
    """Patch auth.py's _sec / _us_mod refs for login route."""
    import acas_pro.core.security as _sec_mod
    import acas_pro.services.user_service as _us_mod
    import acas_pro.core.config as _cfg_mod

    mock_rl = MagicMock()
    mock_rl.is_allowed.return_value = True
    monkeypatch.setattr(_sec_mod, 'rate_limiter', mock_rl)

    mock_jwt = MagicMock()
    mock_jwt.generate_token.return_value = 'tok_abc'
    monkeypatch.setattr(_sec_mod, 'JWTManager', mock_jwt)

    mock_us = MagicMock()
    profile = type('P', (), {'id': 'u1', 'account': 'test', 'nickname': 'Test'})()
    if login_ok:
        mock_us.login.return_value = (True, '', profile)
    else:
        mock_us.login.return_value = (False, 'Invalid credentials', None)
    monkeypatch.setattr(_us_mod, 'user_service', mock_us)

    cfg = MagicMock()
    cfg.security.secret_key = 'x' * 32
    monkeypatch.setattr(_cfg_mod, 'config', cfg)

    return mock_rl, mock_us, mock_jwt


# ---------------------------------------------------------------
# TestAuthRegister
# ---------------------------------------------------------------

class TestAuthRegister:
    def test_register_success(self, client, monkeypatch):
        _mock_register(monkeypatch, register_ok=True)
        resp = client.post('/api/auth/register', json={
            'account': 'test', 'password': 'Test123!', 'nickname': 'Test'
        })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True

    def test_register_missing_account(self, client):
        resp = client.post('/api/auth/register', json={'password': 'Test123!'})
        assert resp.status_code == 400

    def test_register_missing_password(self, client):
        resp = client.post('/api/auth/register', json={'account': 'test'})
        assert resp.status_code == 400

    def test_register_weak_password(self, client, monkeypatch):
        import acas_pro.core.security as _sec_mod
        mock_pv = MagicMock()
        mock_pv.validate.return_value = (False, 'too weak')
        monkeypatch.setattr(_sec_mod, 'password_validator', mock_pv)
        resp = client.post('/api/auth/register', json={
            'account': 'test', 'password': 'weak'
        })
        assert resp.status_code == 400

    def test_register_rate_limited(self, client, monkeypatch):
        import acas_pro.core.security as _sec_mod
        mock_rl = MagicMock()
        mock_rl.is_allowed.return_value = False
        monkeypatch.setattr(_sec_mod, 'rate_limiter', mock_rl)
        resp = client.post('/api/auth/register', json={
            'account': 'test', 'password': 'Test123!'
        })
        assert resp.status_code == 429

    def test_register_duplicate(self, client, monkeypatch):
        _mock_register(monkeypatch, register_ok=False)
        resp = client.post('/api/auth/register', json={
            'account': 'test', 'password': 'Test123!'
        })
        assert resp.status_code == 409


# ---------------------------------------------------------------
# TestAuthLogin
# ---------------------------------------------------------------

class TestAuthLogin:
    def test_login_success(self, client, monkeypatch):
        _mock_login(monkeypatch, login_ok=True)
        resp = client.post('/api/auth/login', json={
            'account': 'test', 'password': 'Test123!'
        })
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True

    def test_login_invalid_credentials(self, client, monkeypatch):
        _mock_login(monkeypatch, login_ok=False)
        resp = client.post('/api/auth/login', json={
            'account': 'test', 'password': 'wrong'
        })
        assert resp.status_code == 401

    def test_login_missing_account(self, client):
        resp = client.post('/api/auth/login', json={'password': 'Test123!'})
        assert resp.status_code == 400

    def test_login_rate_limited(self, client, monkeypatch):
        import acas_pro.core.security as _sec_mod
        mock_rl = MagicMock()
        mock_rl.is_allowed.return_value = False
        monkeypatch.setattr(_sec_mod, 'rate_limiter', mock_rl)
        resp = client.post('/api/auth/login', json={
            'account': 'test', 'password': 'Test123!'
        })
        assert resp.status_code == 429


# ---------------------------------------------------------------
# TestAuthMe
# ---------------------------------------------------------------

class TestAuthMe:
    def test_me_authenticated(self, client):
        from flask import g
        from acas_pro.web.routes.auth import auth_me
        ctx = client.application.app_context()
        ctx.push()
        try:
            g.user = {'user_id': 'u1', 'account': 'test'}
            resp = auth_me()
            assert resp.status_code == 200
            data = json.loads(resp.get_data())
            assert data['user_id'] == 'u1'
        finally:
            ctx.pop()

    def test_me_unauthenticated(self, client):
        from flask import g
        from acas_pro.web.routes.auth import auth_me
        ctx = client.application.app_context()
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
    def test_generate_token(self):
        tok = generate_token('u1', 'test')
        assert isinstance(tok, str)
        assert len(tok) > 0

    def test_verify_token_success(self):
        tok = generate_token('u1', 'test')
        payload = verify_token(tok)
        assert payload is not None
        assert payload['sub'] == 'u1'

    def test_verify_token_legacy(self):
        """JWTManager returns None -> fallback to jwt.decode"""
        with patch('acas_pro.core.security.JWTManager.verify_token',
                   return_value=None):
            with patch('jwt.decode', return_value={'user_id': 'u1', 'account': 'test'}):
                payload = verify_token('tok')
        assert payload is not None
        assert payload['user_id'] == 'u1'

    def test_verify_token_invalid(self):
        """Both JWTManager and jwt.decode fail -> returns None"""
        with patch('acas_pro.core.security.JWTManager.verify_token',
                   return_value=None):
            with patch('jwt.decode', side_effect=Exception('bad token')):
                payload = verify_token('bad')
        assert payload is None
