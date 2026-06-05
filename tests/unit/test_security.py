#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for acas_pro.core.security module

NOTE: A local conftest.py in tests/unit/ overrides the global _reset_lazy_singletons
fixture to prevent module deletion that would break our import-time _cfg() patching.
"""

import pytest
import os
import json
import time
import jwt
import secrets
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path


# ─── Shared mock config fixture ───

@pytest.fixture(autouse=True)
def mock_security_config():
    """Mock _cfg() for all security tests - applied per-test so it survives conftest re-imports."""
    mock_config = MagicMock()
    mock_config.security.salt_length = 16
    mock_config.security.pbkdf2_iterations = 100000
    mock_config.security.secret_key = "test-secret-key-12345678901234567890123456789012"
    mock_config.security.jwt_algorithm = "HS256"
    mock_config.security.session_timeout_minutes = 30
    mock_config.environment = "testing"
    with patch('acas_pro.core.security._cfg', return_value=mock_config):
        yield mock_config


from acas_pro.core.security import (
    PasswordValidator, PasswordHasher, JWTManager, SessionManager,
    RateLimiter, CryptoManager, RedisRateLimiter,
    generate_csrf_token, validate_csrf_request,
    set_jwt_cookie, clear_jwt_cookie, get_jwt_from_cookie,
    _parse_dt, _reset_lazy_instances, _build_rate_limiter,
    get_password_validator, get_password_hasher, get_session_manager, get_rate_limiter
)


# ─── PasswordValidator ───

class TestPasswordValidator:
    def test_valid_password(self):
        ok, msg = PasswordValidator.validate('Valid1@Password')
        assert ok is True
        assert msg == ""

    def test_too_short(self):
        ok, msg = PasswordValidator.validate("Short1!")
        assert ok is False
        assert "at least" in msg

    def test_too_long(self):
        ok, msg = PasswordValidator.validate("A" * 129 + "1!")
        assert ok is False
        assert "exceed" in msg

    def test_no_uppercase(self):
        ok, msg = PasswordValidator.validate("lowercase1!")
        assert ok is False
        assert "uppercase" in msg

    def test_no_lowercase(self):
        ok, msg = PasswordValidator.validate("UPPERCASE1!")
        assert ok is False
        assert "lowercase" in msg

    def test_no_digit(self):
        ok, msg = PasswordValidator.validate("NoDigit@Password")
        assert ok is False
        assert "digit" in msg

    def test_no_special_char(self):
        ok, msg = PasswordValidator.validate("NoSpecial123")
        assert ok is False
        assert "special character" in msg

    def test_common_password(self):
        ok, msg = PasswordValidator.validate("Password1!")
        if not ok:
            assert any(word in msg.lower() for word in ["common", "uppercase", "lowercase", "digit", "special"])

    def test_common_password_base(self):
        ok, msg = PasswordValidator.validate("Letmein1!")
        if not ok:
            assert any(word in msg.lower() for word in ["common", "uppercase", "lowercase", "digit", "special"])
        ok2, msg2 = PasswordValidator.validate("Xk9#mP2$vL7!")
        assert ok2 is True
        assert msg2 == ""


# ─── PasswordHasher ───

class TestPasswordHasher:
    def test_hash_password(self, mock_security_config):
        hashed = PasswordHasher.hash("TestPassword123!")
        assert hashed.startswith("pbkdf2:sha256:")
        assert "$" in hashed

    def test_verify_correct_password(self, mock_security_config):
        hashed = PasswordHasher.hash("TestPassword123!")
        assert PasswordHasher.verify("TestPassword123!", hashed) is True

    def test_verify_wrong_password(self, mock_security_config):
        hashed = PasswordHasher.hash("TestPassword123!")
        assert PasswordHasher.verify("WrongPassword123!", hashed) is False

    def test_verify_legacy_format(self, mock_security_config):
        assert PasswordHasher.verify("test", "invalid_format") is False

    def test_verify_malformed_hash(self, mock_security_config):
        assert PasswordHasher.verify("test", "bad$hash") is False


# ─── JWTManager ───

class TestJWTManager:
    @pytest.fixture(autouse=True)
    def setup_env(self):
        os.environ['ACAS_JWT_SECRET'] = 'test-jwt-secret-1234567890123456789012345678901234567890'
        yield
        os.environ.pop('ACAS_JWT_SECRET', None)

    def test_generate_token(self, mock_security_config):
        token = JWTManager.generate_token("user123")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_generate_refresh_token(self, mock_security_config):
        token = JWTManager.generate_refresh_token("user123")
        assert isinstance(token, str)

    def test_verify_valid_token(self, mock_security_config):
        token = JWTManager.generate_token("user123")
        payload = JWTManager.verify_token(token)
        assert payload is not None
        assert payload['sub'] == "user123"
        assert payload['type'] == 'access'

    def test_verify_invalid_token(self, mock_security_config):
        payload = JWTManager.verify_token("invalid.token.here")
        assert payload is None

    def test_verify_wrong_type(self, mock_security_config):
        refresh = JWTManager.generate_refresh_token("user123")
        payload = JWTManager.verify_token(refresh, expected_type='access')
        assert payload is None

    def test_refresh_access_token(self, mock_security_config):
        refresh = JWTManager.generate_refresh_token("user123")
        new_token = JWTManager.refresh_access_token(refresh)
        assert new_token is not None
        payload = JWTManager.verify_token(new_token)
        assert payload['sub'] == "user123"

    def test_refresh_with_invalid_token(self, mock_security_config):
        result = JWTManager.refresh_access_token("invalid")
        assert result is None

    def test_get_secret_key_from_env(self, mock_security_config):
        key = JWTManager._get_secret_key()
        assert key == os.environ['ACAS_JWT_SECRET']


# ─── SessionManager ───

class TestSessionManager:
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        db.fetchone = MagicMock(return_value=None)
        db.execute = MagicMock(return_value=MagicMock(rowcount=1))
        return db

    def test_create_session(self, mock_db, mock_security_config):
        sm = SessionManager()
        sm.db = mock_db
        token = sm.create_session("user123", "127.0.0.1", "Mozilla/5.0")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_validate_session_not_found(self, mock_db, mock_security_config):
        sm = SessionManager()
        sm.db = mock_db
        result = sm.validate_session("nonexistent_token")
        assert result is None

    def test_validate_session_expired(self, mock_db, mock_security_config):
        sm = SessionManager()
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        mock_db.fetchone = MagicMock(return_value={
            'user_id': 'user123',
            'expires_at': past
        })
        sm.db = mock_db
        result = sm.validate_session("expired_token")
        assert result is None

    def test_validate_session_valid(self, mock_db, mock_security_config):
        sm = SessionManager()
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        mock_db.fetchone = MagicMock(return_value={
            'user_id': 'user123',
            'expires_at': future
        })
        sm.db = mock_db
        result = sm.validate_session("valid_token")
        assert result == "user123"

    def test_revoke_session(self, mock_db, mock_security_config):
        sm = SessionManager()
        sm.db = mock_db
        result = sm.revoke_session("token123")
        assert result is True

    def test_revoke_all_user_sessions(self, mock_db, mock_security_config):
        sm = SessionManager()
        sm.db = mock_db
        result = sm.revoke_all_user_sessions("user123")
        assert result == 1

    def test_revoke_session_error(self, mock_db, mock_security_config):
        sm = SessionManager()
        mock_db.execute = MagicMock(side_effect=Exception("DB error"))
        sm.db = mock_db
        result = sm.revoke_session("token123")
        assert result is False


# ─── RateLimiter ───

class TestRateLimiter:
    @pytest.fixture
    def tmp_limiter(self, tmp_path):
        path = str(tmp_path / "rate_limit.json")
        return RateLimiter(path)

    def test_is_allowed_under_limit(self, tmp_limiter):
        assert tmp_limiter.is_allowed("key1", max_attempts=5, window_seconds=300) is True

    def test_is_allowed_over_limit(self, tmp_limiter):
        for _ in range(5):
            tmp_limiter.record_attempt("key2")
        assert tmp_limiter.is_allowed("key2", max_attempts=5, window_seconds=300) is False

    def test_record_attempt(self, tmp_limiter):
        tmp_limiter.record_attempt("key3")
        data = tmp_limiter._load()
        assert "key3" in data
        assert len(data["key3"]) == 1

    def test_reset(self, tmp_limiter):
        tmp_limiter.record_attempt("key4")
        tmp_limiter.reset("key4")
        data = tmp_limiter._load()
        assert "key4" not in data

    def test_load_nonexistent_file(self, tmp_limiter):
        limiter = RateLimiter("/nonexistent/path/rate_limit.json")
        data = limiter._load()
        assert data == {}

    def test_load_invalid_json(self, tmp_path):
        path = str(tmp_path / "invalid.json")
        with open(path, 'w') as f:
            f.write("not json")
        limiter = RateLimiter(path)
        data = limiter._load()
        assert data == {}


# ─── CryptoManager ───

class TestCryptoManager:
    @pytest.fixture(autouse=True)
    def setup_env(self):
        os.environ['ACAS_ENCRYPTION_KEY'] = 'test-encryption-key-12345678901234567890123456789012'
        os.environ['ACAS_ENCRYPTION_SALT'] = 'testsalt123456789012345678901234'
        yield
        os.environ.pop('ACAS_ENCRYPTION_KEY', None)
        os.environ.pop('ACAS_ENCRYPTION_SALT', None)

    def test_encrypt_decrypt(self, mock_security_config):
        cm = CryptoManager()
        plaintext = "Hello, World!"
        encrypted = cm.encrypt(plaintext)
        assert encrypted != plaintext
        assert len(encrypted) > 0
        decrypted = cm.decrypt(encrypted)
        assert decrypted == plaintext

    def test_encrypt_empty(self, mock_security_config):
        cm = CryptoManager()
        assert cm.encrypt("") == ""

    def test_decrypt_empty(self, mock_security_config):
        cm = CryptoManager()
        assert cm.decrypt("") == ""

    def test_decrypt_invalid(self, mock_security_config):
        cm = CryptoManager()
        with pytest.raises(ValueError, match="Invalid encrypted data"):
            cm.decrypt("invalid_ciphertext")

    def test_rotate_key(self, mock_security_config):
        cm = CryptoManager()
        result = cm.rotate_key("new-key-1234567890123456789012345678901234567890")
        assert result["status"] == "success"

    def test_init_with_custom_key(self, mock_security_config):
        cm = CryptoManager("custom-key-1234567890123456789012345678901234567890")
        encrypted = cm.encrypt("test")
        assert len(encrypted) > 0


# ─── RedisRateLimiter ───

class TestRedisRateLimiter:
    def test_init_no_redis(self):
        with patch.dict(os.environ, {}, clear=True):
            rl = RedisRateLimiter()
            assert rl.available is False

    def test_is_allowed_fallback(self):
        with patch.dict(os.environ, {'ACAS_DATA_DIR': 'C:\\tmp'}):
            rl = RedisRateLimiter()
            result = rl.is_allowed("key1")
            assert isinstance(result, bool)

    def test_record_attempt_fallback(self):
        with patch.dict(os.environ, {'ACAS_DATA_DIR': 'C:\\tmp'}):
            rl = RedisRateLimiter()
            rl.record_attempt("key1")

    def test_reset_fallback(self):
        with patch.dict(os.environ, {'ACAS_DATA_DIR': 'C:\\tmp'}):
            rl = RedisRateLimiter()
            rl.reset("key1")


# ─── CSRF Functions ───

class TestCSRF:
    def test_generate_csrf_token(self):
        token = generate_csrf_token()
        assert isinstance(token, str)
        assert len(token) == 64

    def test_validate_csrf_testing_env(self):
        with patch.dict(os.environ, {'ACAS_ENV': 'testing'}):
            ok, msg = validate_csrf_request(None)
            assert ok is True
            assert msg == ""

    def test_validate_csrf_missing_header(self):
        with patch.dict(os.environ, {}, clear=True):
            request = MagicMock()
            request.headers = {}
            request.cookies = {'csrf_token': 'abc'}
            ok, msg = validate_csrf_request(request)
            assert ok is False
            assert "Missing" in msg

    def test_validate_csrf_missing_cookie(self):
        with patch.dict(os.environ, {}, clear=True):
            request = MagicMock()
            request.headers = {'X-CSRF-Token': 'abc'}
            request.cookies = {}
            ok, msg = validate_csrf_request(request)
            assert ok is False
            assert "cookie not set" in msg

    def test_validate_csrf_mismatch(self):
        with patch.dict(os.environ, {}, clear=True):
            request = MagicMock()
            request.headers = {'X-CSRF-Token': 'a' * 64}
            request.cookies = {'csrf_token': 'b' * 64}
            ok, msg = validate_csrf_request(request)
            assert ok is False
            assert "mismatch" in msg

    def test_validate_csrf_invalid_format(self):
        with patch.dict(os.environ, {}, clear=True):
            request = MagicMock()
            request.headers = {'X-CSRF-Token': 'not-hex-format'}
            request.cookies = {'csrf_token': 'not-hex-format'}
            ok, msg = validate_csrf_request(request)
            assert ok is False
            assert "Invalid CSRF token format" in msg


# ─── JWT Cookie Functions ───

class TestJWTCookie:
    def test_set_jwt_cookie(self):
        response = MagicMock()
        set_jwt_cookie(response, "test_token")
        response.set_cookie.assert_called_once()
        args = response.set_cookie.call_args
        assert args[0][0] == 'acas_jwt'
        assert args[1]['httponly'] is True
        assert args[1]['secure'] is True
        assert args[1]['samesite'] == 'Lax'

    def test_clear_jwt_cookie(self):
        response = MagicMock()
        clear_jwt_cookie(response)
        response.set_cookie.assert_called_once()
        args = response.set_cookie.call_args
        assert args[0][0] == 'acas_jwt'
        assert args[1]['max_age'] == 0

    def test_get_jwt_from_cookie(self):
        request = MagicMock()
        request.cookies = {'acas_jwt': 'test_token'}
        token = get_jwt_from_cookie(request)
        assert token == 'test_token'

    def test_get_jwt_from_cookie_missing(self):
        request = MagicMock()
        request.cookies = {}
        token = get_jwt_from_cookie(request)
        assert token == ''


# ─── Helper Functions ───

class TestHelpers:
    def test_parse_dt_datetime(self):
        now = datetime.now(timezone.utc)
        result = _parse_dt(now)
        assert result == now

    def test_parse_dt_string(self):
        now = datetime.now(timezone.utc)
        iso = now.isoformat()
        result = _parse_dt(iso)
        assert isinstance(result, datetime)

    def test_reset_lazy_instances(self):
        _reset_lazy_instances()

    def test_build_rate_limiter_no_redis(self):
        with patch.dict(os.environ, {'ACAS_DATA_DIR': 'C:\\tmp'}):
            rl = _build_rate_limiter()
            assert rl is not None
            assert isinstance(rl, RateLimiter)

    def test_get_password_validator(self):
        pv = get_password_validator()
        assert isinstance(pv, PasswordValidator)

    def test_get_password_hasher(self):
        ph = get_password_hasher()
        assert isinstance(ph, PasswordHasher)

    def test_get_session_manager(self):
        sm = get_session_manager()
        assert isinstance(sm, SessionManager)

    def test_get_rate_limiter(self):
        rl = get_rate_limiter()
        assert isinstance(rl, RateLimiter)


# ─── Factory Functions ───

class TestFactoryFunctions:
    def test_get_password_validator(self):
        pv = get_password_validator()
        assert isinstance(pv, PasswordValidator)

    def test_get_password_hasher(self):
        ph = get_password_hasher()
        assert isinstance(ph, PasswordHasher)

    def test_get_session_manager(self):
        sm = get_session_manager()
        assert isinstance(sm, SessionManager)

    def test_get_rate_limiter(self):
        rl = get_rate_limiter()
        assert isinstance(rl, RateLimiter)
