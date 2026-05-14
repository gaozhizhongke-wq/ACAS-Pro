"""
Comprehensive tests for user_service.py
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timedelta, timezone


@pytest.fixture
def mock_deps():
    """Mock all module-level dependencies for user_service"""
    patches = {
        'db': MagicMock(),
        'password_validator': MagicMock(),
        'password_hasher': MagicMock(),
        'session_manager': MagicMock(),
        'rate_limiter': MagicMock(),
        'logger': MagicMock(),
        'audit_logger': MagicMock(),
    }
    with patch.multiple(
        'acas_pro.services.user_service',
        **patches,
    ):
        from acas_pro.services.user_service import UserService
        yield patches, UserService


class TestUserServiceInit:
    def test_init_creates_service(self, mock_deps):
        _, UserService = mock_deps
        svc = UserService()
        assert svc._current_user is None


class TestRegister:
    def test_register_short_account(self, mock_deps):
        deps, UserService = mock_deps
        svc = UserService()
        ok, msg, profile = svc.register("ab", "password123")
        assert ok is False
        assert "3 characters" in msg
        assert profile is None

    def test_register_empty_account(self, mock_deps):
        deps, UserService = mock_deps
        svc = UserService()
        ok, msg, profile = svc.register("", "password123")
        assert ok is False
        assert profile is None

    def test_register_weak_password(self, mock_deps):
        deps, UserService = mock_deps
        deps['password_validator'].validate.return_value = (False, "Too short")
        svc = UserService()
        ok, msg, profile = svc.register("testuser", "abc")
        assert ok is False
        assert msg == "Too short"
        deps['password_validator'].validate.assert_called_once_with("abc")

    def test_register_account_exists(self, mock_deps):
        deps, UserService = mock_deps
        deps['password_validator'].validate.return_value = (True, "")
        deps['db'].fetchone.return_value = {"id": "existing"}
        svc = UserService()
        ok, msg, profile = svc.register("existing", "password123")
        assert ok is False
        assert "already exists" in msg

    def test_register_success_global(self, mock_deps):
        deps, UserService = mock_deps
        deps['password_validator'].validate.return_value = (True, "")
        deps['db'].fetchone.return_value = None
        deps['password_hasher'].hash.return_value = "hashed_pw"
        deps['db'].fetchone.side_effect = [
            None,  # account check
            {"id": "U123", "account": "testuser", "nickname": "testuser",
             "email": "", "phone": "", "role": "user", "status": "active",
             "region": "global", "language": "zh", "timezone": "UTC",
             "created_at": "2024-01-01T00:00:00", "last_login": None,
             "wallet_balance": 0.0, "wallet_currency": "USD", "model_preference": "auto"}
        ]
        svc = UserService()
        ok, msg, profile = svc.register("testuser", "StrongPass1!")
        assert ok is True
        assert "successful" in msg
        assert profile is not None
        assert profile.account == "testuser"
        deps['db'].insert.assert_called_once()
        insert_args = deps['db'].insert.call_args
        assert insert_args[0][1]['language'] == "zh"

    def test_register_success_mena(self, mock_deps):
        deps, UserService = mock_deps
        deps['password_validator'].validate.return_value = (True, "")
        deps['db'].fetchone.side_effect = [None, {"id": "U1", "account": "u", "nickname": "u",
            "email": "", "phone": "", "role": "user", "status": "active",
            "region": "mena", "language": "ar", "timezone": "UTC",
            "created_at": "2024-01-01T00:00:00", "last_login": None,
            "wallet_balance": 0.0, "wallet_currency": "USD", "model_preference": "auto"}]
        deps['password_hasher'].hash.return_value = "h"
        svc = UserService()
        ok, msg, profile = svc.register("user1", "StrongPass1!", region="mena")
        assert ok is True
        insert_args = deps['db'].insert.call_args
        assert insert_args[0][1]['language'] == "ar"

    def test_register_success_ssa(self, mock_deps):
        deps, UserService = mock_deps
        deps['password_validator'].validate.return_value = (True, "")
        deps['db'].fetchone.side_effect = [None, {"id": "U1", "account": "u", "nickname": "u",
            "email": "", "phone": "", "role": "user", "status": "active",
            "region": "ssa", "language": "en", "timezone": "UTC",
            "created_at": "2024-01-01T00:00:00", "last_login": None,
            "wallet_balance": 0.0, "wallet_currency": "USD", "model_preference": "auto"}]
        deps['password_hasher'].hash.return_value = "h"
        svc = UserService()
        ok, msg, profile = svc.register("user1", "StrongPass1!", region="ssa")
        assert ok is True
        insert_args = deps['db'].insert.call_args
        assert insert_args[0][1]['language'] == "en"

    def test_register_success_sea(self, mock_deps):
        deps, UserService = mock_deps
        deps['password_validator'].validate.return_value = (True, "")
        deps['db'].fetchone.side_effect = [None, {"id": "U1", "account": "u", "nickname": "u",
            "email": "", "phone": "", "role": "user", "status": "active",
            "region": "sea", "language": "en", "timezone": "UTC",
            "created_at": "2024-01-01T00:00:00", "last_login": None,
            "wallet_balance": 0.0, "wallet_currency": "USD", "model_preference": "auto"}]
        deps['password_hasher'].hash.return_value = "h"
        svc = UserService()
        ok, msg, profile = svc.register("user1", "StrongPass1!", region="sea")
        assert ok is True
        insert_args = deps['db'].insert.call_args
        assert insert_args[0][1]['language'] == "en"

    def test_register_success_cn_northwest(self, mock_deps):
        deps, UserService = mock_deps
        deps['password_validator'].validate.return_value = (True, "")
        deps['db'].fetchone.side_effect = [None, {"id": "U1", "account": "u", "nickname": "u",
            "email": "", "phone": "", "role": "user", "status": "active",
            "region": "cn_northwest", "language": "zh", "timezone": "Asia/Shanghai",
            "created_at": "2024-01-01T00:00:00", "last_login": None,
            "wallet_balance": 0.0, "wallet_currency": "USD", "model_preference": "auto"}]
        deps['password_hasher'].hash.return_value = "h"
        svc = UserService()
        ok, msg, profile = svc.register("user1", "StrongPass1!", region="cn_northwest")
        assert ok is True
        insert_args = deps['db'].insert.call_args
        assert insert_args[0][1]['timezone'] == "Asia/Shanghai"

    def test_register_db_error(self, mock_deps):
        deps, UserService = mock_deps
        deps['password_validator'].validate.return_value = (True, "")
        deps['db'].fetchone.return_value = None
        deps['db'].insert.side_effect = Exception("DB Error")
        svc = UserService()
        ok, msg, profile = svc.register("testuser", "StrongPass1!")
        assert ok is False
        assert "failed" in msg.lower()
        assert profile is None


class TestLogin:
    def test_login_rate_limited(self, mock_deps):
        deps, UserService = mock_deps
        deps['rate_limiter'].is_allowed.return_value = False
        svc = UserService()
        ok, msg, profile = svc.login("testuser", "password123", ip_address="1.2.3.4")
        assert ok is False
        assert "Too many" in msg
        deps['audit_logger'].log.assert_called_once()

    def test_login_user_not_found(self, mock_deps):
        deps, UserService = mock_deps
        deps['rate_limiter'].is_allowed.return_value = True
        deps['db'].fetchone.return_value = None
        svc = UserService()
        ok, msg, profile = svc.login("testuser", "password123")
        assert ok is False
        assert "Invalid" in msg
        deps['rate_limiter'].record_attempt.assert_called_once()

    def test_login_account_locked(self, mock_deps):
        deps, UserService = mock_deps
        deps['rate_limiter'].is_allowed.return_value = True
        future_time = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        deps['db'].fetchone.return_value = {
            "id": "U1", "account": "testuser", "password_hash": "hash",
            "locked_until": future_time, "status": "active",
            "failed_login_count": 5, "login_count": 0
        }
        svc = UserService()
        ok, msg, profile = svc.login("testuser", "password123")
        assert ok is False
        assert "locked" in msg.lower()

    def test_login_inactive_user(self, mock_deps):
        deps, UserService = mock_deps
        deps['rate_limiter'].is_allowed.return_value = True
        deps['db'].fetchone.return_value = {
            "id": "U1", "account": "testuser", "password_hash": "hash",
            "status": "inactive", "failed_login_count": 0, "login_count": 0
        }
        svc = UserService()
        ok, msg, profile = svc.login("testuser", "password123")
        assert ok is False
        assert "inactive" in msg.lower()

    def test_login_wrong_password_under_5(self, mock_deps):
        deps, UserService = mock_deps
        deps['rate_limiter'].is_allowed.return_value = True
        deps['password_hasher'].verify.return_value = False
        deps['db'].fetchone.return_value = {
            "id": "U1", "account": "testuser", "password_hash": "hash",
            "status": "active", "failed_login_count": 2, "login_count": 5
        }
        svc = UserService()
        ok, msg, profile = svc.login("testuser", "wrongpassword")
        assert ok is False
        assert "Invalid" in msg
        deps['db'].update.assert_called_once()
        deps['rate_limiter'].record_attempt.assert_called_once()

    def test_login_wrong_password_locks_account(self, mock_deps):
        deps, UserService = mock_deps
        deps['rate_limiter'].is_allowed.return_value = True
        deps['password_hasher'].verify.return_value = False
        deps['db'].fetchone.return_value = {
            "id": "U1", "account": "testuser", "password_hash": "hash",
            "status": "active", "failed_login_count": 4, "login_count": 5
        }
        svc = UserService()
        ok, msg, profile = svc.login("testuser", "wrongpassword")
        assert ok is False
        assert "locked" in msg.lower()
        deps['db'].update.assert_called_once()
        update_args = deps['db'].update.call_args
        assert update_args[0][1]['locked_until'] is not None

    def test_login_success(self, mock_deps):
        deps, UserService = mock_deps
        deps['rate_limiter'].is_allowed.return_value = True
        deps['password_hasher'].verify.return_value = True
        deps['db'].fetchone.return_value = {
            "id": "U1", "account": "testuser", "password_hash": "hash",
            "status": "active", "failed_login_count": 0, "login_count": 5,
            "nickname": "Test", "email": "test@test.com", "phone": "",
            "role": "user", "region": "global", "language": "zh",
            "timezone": "UTC", "created_at": "2024-01-01T00:00:00",
            "last_login": "2024-01-01T00:00:00",
            "wallet_balance": 0.0, "wallet_currency": "USD",
            "model_preference": "auto"
        }
        svc = UserService()
        ok, msg, profile = svc.login("testuser", "password123", ip_address="1.2.3.4")
        assert ok is True
        assert "successful" in msg
        assert profile.account == "testuser"
        assert svc._current_user is not None
        deps['rate_limiter'].reset.assert_called_once()


class TestLoginGuest:
    def test_login_guest(self, mock_deps):
        deps, UserService = mock_deps
        deps['db'].fetchone.return_value = {
            "id": "G1", "account": "G1", "nickname": "Guest",
            "email": "", "phone": "", "role": "guest", "status": "active",
            "region": "global", "language": "zh", "timezone": "UTC",
            "created_at": "2024-01-01T00:00:00", "last_login": "2024-01-01T00:00:00",
            "wallet_balance": 1000.0, "wallet_currency": "USD",
            "model_preference": "auto"
        }
        svc = UserService()
        profile = svc.login_guest()
        assert profile is not None
        assert profile.role == "guest"
        assert profile.wallet_balance == 1000.0
        deps['db'].insert.assert_called_once()
        deps['audit_logger'].log.assert_called_once()


class TestLogout:
    def test_logout_with_user(self, mock_deps):
        deps, UserService = mock_deps
        mock_profile = MagicMock()
        svc = UserService()
        svc._current_user = mock_profile
        svc.logout()
        assert svc._current_user is None
        deps['audit_logger'].log.assert_called_once()

    def test_logout_without_user(self, mock_deps):
        deps, UserService = mock_deps
        svc = UserService()
        svc._current_user = None
        svc.logout()
        assert svc._current_user is None
        deps['audit_logger'].log.assert_not_called()


class TestGetProfile:
    def test_get_profile_found(self, mock_deps):
        deps, UserService = mock_deps
        deps['db'].fetchone.return_value = {
            "id": "U1", "account": "testuser", "nickname": "Test",
            "email": "t@t.com", "phone": "123", "role": "user",
            "status": "active", "region": "global", "language": "zh",
            "timezone": "UTC", "created_at": "2024-01-01T00:00:00",
            "last_login": None, "wallet_balance": 0.0,
            "wallet_currency": "USD", "model_preference": "auto"
        }
        svc = UserService()
        profile = svc._get_profile("U1")
        assert profile is not None
        assert profile.id == "U1"
        assert profile.account == "testuser"

    def test_get_profile_not_found(self, mock_deps):
        deps, UserService = mock_deps
        deps['db'].fetchone.return_value = None
        svc = UserService()
        profile = svc._get_profile("nonexistent")
        assert profile is None


class TestGetCurrent:
    def test_get_current_with_user(self, mock_deps):
        deps, UserService = mock_deps
        svc = UserService()
        svc._current_user = MagicMock()
        assert svc.get_current() is not None

    def test_get_current_without_user(self, mock_deps):
        deps, UserService = mock_deps
        svc = UserService()
        assert svc.get_current() is None


class TestIsAuthenticated:
    def test_authenticated_user(self, mock_deps):
        deps, UserService = mock_deps
        svc = UserService()
        mock_user = MagicMock()
        mock_user.role = "user"
        svc._current_user = mock_user
        assert svc.is_authenticated() is True

    def test_guest_user(self, mock_deps):
        deps, UserService = mock_deps
        svc = UserService()
        mock_user = MagicMock()
        mock_user.role = "guest"
        svc._current_user = mock_user
        assert svc.is_authenticated() is False

    def test_no_user(self, mock_deps):
        deps, UserService = mock_deps
        svc = UserService()
        assert svc.is_authenticated() is False


class TestUpdateProfile:
    def test_update_valid_fields(self, mock_deps):
        deps, UserService = mock_deps
        svc = UserService()
        ok, msg = svc.update_profile("U1", {"nickname": "NewName", "email": "new@test.com"})
        assert ok is True
        assert "successful" in msg.lower()
        deps['db'].update.assert_called_once()

    def test_update_no_valid_fields(self, mock_deps):
        deps, UserService = mock_deps
        svc = UserService()
        ok, msg = svc.update_profile("U1", {"invalid_field": "value"})
        assert ok is False
        assert "No valid" in msg

    def test_update_db_error(self, mock_deps):
        deps, UserService = mock_deps
        deps['db'].update.side_effect = Exception("DB Error")
        svc = UserService()
        ok, msg = svc.update_profile("U1", {"nickname": "Test"})
        assert ok is False
        assert "failed" in msg.lower()


class TestChangePassword:
    def test_change_weak_password(self, mock_deps):
        deps, UserService = mock_deps
        deps['password_validator'].validate.return_value = (False, "Too weak")
        svc = UserService()
        ok, msg = svc.change_password("U1", "oldpass", "weak")
        assert ok is False
        assert msg == "Too weak"

    def test_change_user_not_found(self, mock_deps):
        deps, UserService = mock_deps
        deps['password_validator'].validate.return_value = (True, "")
        deps['db'].fetchone.return_value = None
        svc = UserService()
        ok, msg = svc.change_password("U1", "oldpass", "NewPass1!")
        assert ok is False
        assert "not found" in msg.lower()

    def test_change_wrong_old_password(self, mock_deps):
        deps, UserService = mock_deps
        deps['password_validator'].validate.return_value = (True, "")
        deps['db'].fetchone.return_value = {"password_hash": "hash"}
        deps['password_hasher'].verify.return_value = False
        svc = UserService()
        ok, msg = svc.change_password("U1", "wrongold", "NewPass1!")
        assert ok is False
        assert "incorrect" in msg.lower()

    def test_change_password_success(self, mock_deps):
        deps, UserService = mock_deps
        deps['password_validator'].validate.return_value = (True, "")
        deps['db'].fetchone.return_value = {"password_hash": "oldhash"}
        deps['password_hasher'].verify.return_value = True
        deps['password_hasher'].hash.return_value = "newhash"
        svc = UserService()
        ok, msg = svc.change_password("U1", "oldpass", "NewPass1!")
        assert ok is True
        assert "successful" in msg.lower()
        deps['db'].update.assert_called_once()