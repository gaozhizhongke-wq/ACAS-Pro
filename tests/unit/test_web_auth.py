# -*- coding: utf-8 -*-
"""Tests for ACAS Pro auth routes"""
import sys
from unittest.mock import MagicMock, patch, PropertyMock
from contextlib import contextmanager

import pytest
import json

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
# Helpers: create a minimal mock user_service with register/login
# ---------------------------------------------------------------

@contextmanager
def _mock_user_service(mock_service=True, mock_rl=True, mock_pv=True):
    """Patch deps inside auth.py route handlers."""
    from types import SimpleNamespace
    patches = []
    try:
        if mock_service:
            p = patch('acas_pro.web.routes.auth.user_service')
            m = p.start()
            profile = SimpleNamespace(id='u1', account='test', nickname='Test')
            m.register.return_value = (True, 'registered', profile)
            m.login.return_value = (True, 'logged in', profile)
            patches.append(p)
        if mock_rl:
            p = patch('acas_pro.web.routes.auth.rate_limiter')
            m = p.start()
            m.is_allowed.return_value = True
            patches.append(p)
        if mock_pv:
            p = patch('acas_pro.web.routes.auth.pv')
            m = p.start()
            m.validate.return_value = (True, '')
            patches.append(p)
        p = patch('acas_pro.web.routes.auth.JWTManager.generate_token', return_value='tok_abc')
        p.start()
        patches.append(p)
        p = patch('acas_pro.web.routes.auth.config')
        m = p.start()
        m.return_value = MagicMock(security=MagicMock(secret_key='x'*32))
        patches.append(p)
        yield {}
    finally:
        for p in patches:
            p.stop()


# ---------------------------------------------------------------
# TestAuthRegister
# ---------------------------------------------------------------

class TestAuthRegister:
    def test_register_success(self, client):
        with _mock_user_service():
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

    def test_register_weak_password(self, client):
        with patch('acas_pro.web.routes.auth.pv') as m_pv:
            m_pv.validate.return_value = (False, 'too weak')
            resp = client.post('/api/auth/register', json={
                'account': 'test', 'password': 'weak'
            })
            assert resp.status_code == 400

    def test_register_rate_limited(self, client):
        with patch('acas_pro.web.routes.auth.rate_limiter') as m_rl:
            m_rl.is_allowed.return_value = False
            resp = client.post('/api/auth/register', json={
                'account': 'test', 'password': 'Test123!'
            })
            assert resp.status_code == 429

    def test_register_duplicate(self, client):
        with patch('acas_pro.web.routes.auth.user_service') as m:
            m.register.return_value = (False, 'Account already exists', None)
            resp = client.post('/api/auth/register', json={
                'account': 'test', 'password': 'Test123!'
            })
            assert resp.status_code == 409


# ---------------------------------------------------------------
# TestAuthLogin
# ---------------------------------------------------------------

class TestAuthLogin:
    def test_login_success(self, client):
        with patch('acas_pro.web.routes.auth.user_service') as m:
            m.login.return_value = (
                True, 'OK',
                type('P', (), {'id': 'u1', 'account': 'test', 'nickname': 'Test'})()
            )
            resp = client.post('/api/auth/login', json={
                'account': 'test', 'password': 'Test123!'
            })
            assert resp.status_code == 200
            data = json.loads(resp.data)
            assert data['success'] is True

    def test_login_invalid_credentials(self, client):
        with patch('acas_pro.web.routes.auth.user_service') as m:
            m.login.return_value = (False, 'Invalid credentials', None)
            resp = client.post('/api/auth/login', json={
                'account': 'test', 'password': 'wrong'
            })
            assert resp.status_code == 401

    def test_login_missing_account(self, client):
        resp = client.post('/api/auth/login', json={'password': 'Test123!'})
        assert resp.status_code == 400

    def test_login_rate_limited(self, client):
        with patch('acas_pro.web.routes.auth.rate_limiter') as m_rl:
            m_rl.is_allowed.return_value = False
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
            # authenticated: returns jsonify(...)  → Response, status 200
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
            # unauthenticated: returns (jsonify(...), 401) → tuple
            assert resp[1] == 401
        finally:
            ctx.pop()


# ---------------------------------------------------------------
# TestTokenFunctions
# ---------------------------------------------------------------

class TestTokenFunctions:
    def test_generate_token(self):
        # Just verify it doesn't crash and returns a string
        tok = generate_token('u1', 'test')
        assert isinstance(tok, str)
        assert len(tok) > 0

    def test_verify_token_success(self):
        # Ensure config has a valid secret key for token generation/verification
        with patch('acas_pro.core.security._cfg') as m_cfg:
            m_cfg.return_value.security.secret_key = 'test-secret-key-for-jwt-1234567890'
            m_cfg.return_value.security.jwt_algorithm = 'HS256'
            # Generate a real token, then verify it
            tok = generate_token('u1', 'test')
            payload = verify_token(tok)
            assert payload is not None
            assert payload['sub'] == 'u1'
            assert payload['account'] == 'test'

    def test_verify_token_legacy(self):
        """JWTManager returns None → fallback to jwt.decode (local import)."""
        with patch('acas_pro.web.routes.auth.JWTManager.verify_token',
                    return_value=None):
            with patch('acas_pro.web.routes.auth.config') as m_cfg:
                m_cfg.return_value.security.secret_key = 'secret'
                # jwt is imported locally inside verify_token();
                # patch the real jwt module's decode
                with patch('jwt.decode', return_value={'user_id': 'u1'}):
                    payload = verify_token('legacy_tok')
                    assert payload is not None
                    assert payload['user_id'] == 'u1'

    def test_verify_token_invalid(self):
        with patch('acas_pro.web.routes.auth.JWTManager.verify_token',
                    return_value=None):
            with patch('acas_pro.web.routes.auth.config') as m_cfg:
                m_cfg.return_value.security.secret_key = 'secret'
                with patch('jwt.decode', side_effect=__import__('jwt').InvalidTokenError('bad')):
                    payload = verify_token('bad_tok')
                    assert payload is None
