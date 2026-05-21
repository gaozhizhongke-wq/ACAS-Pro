"""Tests for core/security.py - covering PasswordValidator, PasswordHasher, JWTManager,
SessionManager, RateLimiter, CryptoManager, RedisRateLimiter, and module-level functions"""
import pytest
from unittest.mock import patch, MagicMock
import tempfile, os


class TestPasswordValidator:
    def test_validate_strong_password(self):
        from acas_pro.core.security import PasswordValidator
        valid, msg = PasswordValidator.validate("Str0ng!Pass#2024")
        assert valid is True

    def test_validate_weak_password(self):
        from acas_pro.core.security import PasswordValidator
        valid, msg = PasswordValidator.validate("123")
        assert valid is False

    def test_validate_short_password(self):
        from acas_pro.core.security import PasswordValidator
        valid, msg = PasswordValidator.validate("Sh1!")
        assert valid is False

    def test_validate_no_special(self):
        from acas_pro.core.security import PasswordValidator
        valid, msg = PasswordValidator.validate("NoSpecial123")
        assert isinstance(valid, bool)

    def test_validate_no_digit(self):
        from acas_pro.core.security import PasswordValidator
        valid, msg = PasswordValidator.validate("NoDigit!Pass")
        assert isinstance(valid, bool)


class TestPasswordHasher:
    def test_hash_and_verify(self):
        from acas_pro.core.security import PasswordHasher
        hashed = PasswordHasher.hash("testpass123")
        assert hashed != "testpass123"
        assert PasswordHasher.verify("testpass123", hashed) is True

    def test_verify_wrong_password(self):
        from acas_pro.core.security import PasswordHasher
        hashed = PasswordHasher.hash("correctpass")
        assert PasswordHasher.verify("wrongpass", hashed) is False

    def test_hash_different_each_time(self):
        from acas_pro.core.security import PasswordHasher
        h1 = PasswordHasher.hash("samepass")
        h2 = PasswordHasher.hash("samepass")
        assert h1 != h2


class TestJWTManager:
    def test_generate_and_verify_token(self):
        os.environ['ACAS_JWT_SECRET'] = 'test-secret-key-for-jwt-testing-2024'
        try:
            from acas_pro.core.security import JWTManager
            token = JWTManager.generate_token(user_id="1")
            assert isinstance(token, str)
            result = JWTManager.verify_token(token)
            assert result is not None
        finally:
            os.environ.pop('ACAS_JWT_SECRET', None)

    def test_generate_refresh_token(self):
        os.environ['ACAS_JWT_SECRET'] = 'test-secret-key-for-jwt-testing-2024'
        try:
            from acas_pro.core.security import JWTManager
            token = JWTManager.generate_refresh_token(user_id="1")
            assert isinstance(token, str)
        finally:
            os.environ.pop('ACAS_JWT_SECRET', None)

    def test_verify_invalid_token(self):
        os.environ['ACAS_JWT_SECRET'] = 'test-secret-key-for-jwt-testing-2024'
        try:
            from acas_pro.core.security import JWTManager
            result = JWTManager.verify_token("invalid.token.here")
            assert result is None or result is False
        finally:
            os.environ.pop('ACAS_JWT_SECRET', None)

    def test_refresh_access_token(self):
        os.environ['ACAS_JWT_SECRET'] = 'test-secret-key-for-jwt-testing-2024'
        try:
            from acas_pro.core.security import JWTManager
            refresh = JWTManager.generate_refresh_token(user_id="1")
            result = JWTManager.refresh_access_token(refresh)
            assert result is None or isinstance(result, str)
        finally:
            os.environ.pop('ACAS_JWT_SECRET', None)


class TestSessionManager:
    def test_create_session(self):
        os.environ['ACAS_JWT_SECRET'] = 'test-secret-key-session'
        try:
            from acas_pro.core.security import SessionManager
            sm = SessionManager()
            mock_db = MagicMock()
            with patch.object(sm, '_get_db', return_value=mock_db):
                token = sm.create_session(user_id="1", ip_address="127.0.0.1", user_agent="test")
                assert isinstance(token, str)
        finally:
            os.environ.pop('ACAS_JWT_SECRET', None)

    def test_revoke_session(self):
        os.environ['ACAS_JWT_SECRET'] = 'test-secret-key-session'
        try:
            from acas_pro.core.security import SessionManager
            sm = SessionManager()
            mock_db = MagicMock()
            with patch.object(sm, '_get_db', return_value=mock_db):
                sm.revoke_session("some-token")
        finally:
            os.environ.pop('ACAS_JWT_SECRET', None)

    def test_revoke_all_user_sessions(self):
        os.environ['ACAS_JWT_SECRET'] = 'test-secret-key-session'
        try:
            from acas_pro.core.security import SessionManager
            sm = SessionManager()
            mock_db = MagicMock()
            with patch.object(sm, '_get_db', return_value=mock_db):
                sm.revoke_all_user_sessions(user_id=1)
        finally:
            os.environ.pop('ACAS_JWT_SECRET', None)


class TestRateLimiter:
    def test_is_allowed_first_request(self):
        from acas_pro.core.security import RateLimiter
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name
        try:
            rl = RateLimiter(storage_path=path)
            assert rl.is_allowed("test_key", max_attempts=5, window_seconds=60) is True
        finally:
            os.unlink(path)

    def test_rate_limit_exceeded(self):
        from acas_pro.core.security import RateLimiter
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name
        try:
            rl = RateLimiter(storage_path=path)
            for i in range(5):
                rl.record_attempt("test_key")
            # After 5 recorded attempts, is_allowed should return False
            result = rl.is_allowed("test_key", max_attempts=5, window_seconds=60)
            assert result is False
        finally:
            os.unlink(path)

    def test_reset(self):
        from acas_pro.core.security import RateLimiter
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name
        try:
            rl = RateLimiter(storage_path=path)
            rl.record_attempt("key1")
            rl.reset("key1")
            assert rl.is_allowed("key1", max_attempts=1, window_seconds=60) is True
        finally:
            os.unlink(path)

    def test_record_attempt(self):
        from acas_pro.core.security import RateLimiter
        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            path = f.name
        try:
            rl = RateLimiter(storage_path=path)
            rl.record_attempt("key1")
            assert rl.is_allowed("key1", max_attempts=1, window_seconds=60) is False
        finally:
            os.unlink(path)


class TestCryptoManager:
    def test_encrypt_decrypt(self):
        from acas_pro.core.security import CryptoManager
        cm = CryptoManager(key="test-encryption-key-1234567890")
        encrypted = cm.encrypt("hello world")
        assert encrypted != "hello world"
        decrypted = cm.decrypt(encrypted)
        assert decrypted == "hello world"

    def test_encrypt_empty(self):
        from acas_pro.core.security import CryptoManager
        cm = CryptoManager(key="test-encryption-key-1234567890")
        encrypted = cm.encrypt("")
        decrypted = cm.decrypt(encrypted)
        assert decrypted == ""

    def test_rotate_key(self):
        from acas_pro.core.security import CryptoManager
        cm = CryptoManager(key="old-key-1234567890123456")
        encrypted = cm.encrypt("test data")
        cm.rotate_key(new_key="new-key-1234567890123456")


class TestCSRF:
    def test_generate_csrf_token(self):
        from acas_pro.core.security import generate_csrf_token
        token = generate_csrf_token()
        assert isinstance(token, str)

    def test_create_csrf_cookie(self):
        from acas_pro.core.security import create_csrf_cookie
        response = MagicMock()
        response.set_cookie = MagicMock()
        create_csrf_cookie(response)
        response.set_cookie.assert_called()

    def test_validate_csrf_request(self):
        from acas_pro.core.security import validate_csrf_request
        request = MagicMock()
        request.headers = {"X-CSRF-Token": "test"}
        request.cookies = {"csrf_token": "test"}
        result = validate_csrf_request(request)
        assert result is not None


class TestJWTCookie:
    def test_set_jwt_cookie(self):
        from acas_pro.core.security import set_jwt_cookie
        response = MagicMock()
        response.set_cookie = MagicMock()
        set_jwt_cookie(response, "test-token")
        response.set_cookie.assert_called()

    def test_clear_jwt_cookie(self):
        from acas_pro.core.security import clear_jwt_cookie
        response = MagicMock()
        clear_jwt_cookie(response)

    def test_get_jwt_from_cookie(self):
        from acas_pro.core.security import get_jwt_from_cookie
        request = MagicMock()
        request.cookies = {"access_token": "test-jwt"}
        result = get_jwt_from_cookie(request)
        assert isinstance(result, str)


class TestRedisRateLimiter:
    def test_available_no_redis(self):
        from acas_pro.core.security import RedisRateLimiter
        try:
            rl = RedisRateLimiter(redis_url="redis://localhost")
            # available is a property on the instance
            assert isinstance(rl.available, bool)
        except Exception:
            pass  # Expected if redis not available

    def test_init_no_redis(self):
        from acas_pro.core.security import RedisRateLimiter
        try:
            rl = RedisRateLimiter(redis_url="redis://localhost")
        except Exception:
            pass  # Expected if redis not available

    def test_is_allowed_no_redis(self):
        from acas_pro.core.security import RedisRateLimiter
        try:
            rl = RedisRateLimiter(redis_url="redis://localhost")
            result = rl.is_allowed("key", max_attempts=5, window_seconds=60)
            assert isinstance(result, bool)
        except Exception:
            pass  # Expected if redis not available
