#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for services/user_service.py"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock
from acas_pro.services.user_service import UserService


class MockDB:
    """In-memory mock database for testing."""
    def __init__(self):
        self.users = {}
        self.next_user_id = 1

    def insert(self, table, data):
        if table == "users":
            uid = data.get("id") or f"U{self.next_user_id:06d}"
            self.next_user_id += 1
            row = dict(data)
            # Ensure all required fields for _get_profile
            for field in ["email", "phone", "model_preference", "login_count"]:
                row.setdefault(field, "" if field in ["email", "phone", "model_preference"] else 0)
            row["id"] = uid
            self.users[uid] = row
            return uid
        return None

    def fetchone(self, query, params=None):
        if "WHERE id = ?" in query or "WHERE account = ?" in query:
            key = "account" if "account" in query else "id"
            val = params[0] if params else None
            for u in self.users.values():
                if u.get(key) == val:
                    return dict(u)
        if "FROM users" in query:
            return list(self.users.values())
        return None

    def update(self, table, data, where_clause=None, where_params=None):
        if table == "users" and where_params:
            key_val = where_params[0]
            for uid, u in self.users.items():
                if u.get("id") == key_val:
                    u.update(data)
                    return True
        return False

    def execute(self, query, params=None):
        return []


class TestUserService:
    def setup_method(self):
        self.mock_db = MockDB()
        self.mock_hasher = MagicMock()
        self.mock_hasher.hash = MagicMock(return_value="mocked_hash")
        self.mock_hasher.verify = MagicMock(side_effect=lambda pwd, h: h == "mocked_hash")
        self.mock_validator = MagicMock()
        self.mock_validator.validate = MagicMock(side_effect=lambda pwd: (True, ""))
        # CRITICAL: test_auth_routes.py deletes user_service from sys.modules.
        # After that, conftest re-imports, creating a NEW module object.
        # But the top-level `from ... import UserService` bound to the OLD module.
        # The old module's functions reference old _lazy dict via __globals__.
        # Fix: re-import UserService from the CURRENT module in sys.modules.
        import acas_pro.services.user_service as _us_mod
        _UserService = _us_mod.UserService
        self._lazy_backup = dict(_us_mod._lazy)  # save for teardown
        _us_mod._lazy['db'] = self.mock_db
        _us_mod._lazy['password_hasher'] = self.mock_hasher
        _us_mod._lazy['password_validator'] = self.mock_validator
        self.service = _UserService()
        self.service._current_user = None
        self.service._db = self.mock_db

    def teardown_method(self):
        import acas_pro.services.user_service as _us_mod
        _us_mod._lazy.clear()
        _us_mod._lazy.update(self._lazy_backup)

    def test_init(self):
        assert self.service is not None
        # UserService uses lazy db, verify it was initialized
        assert hasattr(self.service, '_current_user')

    def test_register(self):
        success, msg, user = self.service.register(
            account="testuser",
            password="password123",
            nickname="Test User"
        )
        assert success is True
        assert user is not None
        assert user.account == "testuser"
        assert user.nickname == "Test User"
        assert self.mock_hasher.hash.called

    def test_register_existing_user(self):
        self.service.register(account="testuser", password="password123")
        success2, msg2, user2 = self.service.register(account="testuser", password="password456")
        assert success2 is False
        assert user2 is None
        assert "exists" in msg2.lower()

    def test_login(self):
        self.service.register(account="testuser", password="password123")
        success, msg, user = self.service.login("testuser", "password123")
        assert success is True
        assert user is not None
        assert user.account == "testuser"

    def test_login_wrong_password(self):
        self.service.register(account="testuser", password="password123")
        # Override hasher.verify for this test: wrong password should return False
        self.mock_hasher.verify = MagicMock(side_effect=lambda pwd, h: False)
        success, msg, user = self.service.login("testuser", "wrongpassword")
        assert success is False

    def test_login_user_not_found(self):
        success, msg, user = self.service.login("nonexistent", "password123")
        assert success is False

    def test_get_current(self):
        self.service.register(account="testuser", password="password123")
        self.service.login("testuser", "password123")
        user = self.service.get_current()
        assert user is not None

    def test_get_current_not_found(self):
        self.service._current_user = None
        user = self.service.get_current()
        assert user is None

    def test_update_profile(self):
        self.service.register(account="testuser", password="password123")
        self.service.login("testuser", "password123")
        user = self.service.get_current()
        success, msg = self.service.update_profile(
            user.id,
            {"nickname": "New Name"}
        )
        assert success is True

    def test_update_profile_empty(self):
        self.service.register(account="testuser", password="password123")
        self.service.login("testuser", "password123")
        user = self.service.get_current()
        # Empty dict: no valid fields to update → returns False
        success, msg = self.service.update_profile(user.id, {})
        assert success is False

    def test_change_password(self):
        self.service.register(account="testuser", password="oldpass")
        self.service.login("testuser", "oldpass")
        user = self.service.get_current()
        success, msg = self.service.change_password(user.id, "oldpass", "newpass")
        assert success is True

    def test_change_password_wrong_old(self):
        self.service.register(account="testuser", password="oldpass")
        self.service.login("testuser", "oldpass")
        user = self.service.get_current()
        # Override hasher.verify for wrong old password
        self.mock_hasher.verify = MagicMock(side_effect=lambda pwd, h: False)
        success, msg = self.service.change_password(user.id, "wrongpass", "newpass")
        assert success is False

    def test_logout(self):
        self.service.register(account="testuser", password="password123")
        self.service.login("testuser", "password123")
        self.service.logout()
        assert self.service._current_user is None

    def test_is_authenticated(self):
        self.service.register(account="testuser", password="password123")
        self.service.login("testuser", "password123")
        assert self.service.is_authenticated() is True

    def test_is_authenticated_not_found(self):
        self.service._current_user = None
        assert self.service.is_authenticated() is False

    def test_login_guest(self):
        user = self.service.login_guest()
        assert user is not None
        assert user.role == "guest"
