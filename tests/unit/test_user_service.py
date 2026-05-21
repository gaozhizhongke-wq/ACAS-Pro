#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for services/user_service.py"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from acas_pro.services.user_service import UserService


class TestUserService:
    def setup_method(self):
        self.service = UserService()

    def test_init(self):
        assert self.service is not None
        assert self.service.db is not None

    def test_register(self):
        with patch('acas_pro.services.user_service.hash_password') as mock_hash:
            mock_hash.return_value = "hashed_password"
            user = self.service.register(
                username="testuser",
                email="test@example.com",
                password="password123",
                display_name="Test User"
            )
            assert user is not None
            assert user.username == "testuser"
            assert user.email == "test@example.com"

    def test_register_existing_user(self):
        # First register
        with patch('acas_pro.services.user_service.hash_password') as mock_hash:
            mock_hash.return_value = "hashed_password"
            self.service.register(
                username="testuser",
                email="test@example.com",
                password="password123"
            )
        # Try again - should fail
        user = self.service.register(
            username="testuser",
            email="test@example.com",
            password="password123"
        )
        assert user is None

    def test_login(self):
        with patch('acas_pro.services.user_service.hash_password') as mock_hash:
            mock_hash.return_value = "hashed_password"
            self.service.register(
                username="testuser",
                email="test@example.com",
                password="password123"
            )
        with patch('acas_pro.services.user_service.verify_password') as mock_verify:
            mock_verify.return_value = True
            user = self.service.login("testuser", "password123")
            assert user is not None
            assert user.username == "testuser"

    def test_login_wrong_password(self):
        with patch('acas_pro.services.user_service.hash_password') as mock_hash:
            mock_hash.return_value = "hashed_password"
            self.service.register(
                username="testuser",
                email="test@example.com",
                password="password123"
            )
        with patch('acas_pro.services.user_service.verify_password') as mock_verify:
            mock_verify.return_value = False
            user = self.service.login("testuser", "wrongpassword")
            assert user is None

    def test_login_user_not_found(self):
        user = self.service.login("nonexistent", "password123")
        assert user is None

    def test_get_current(self):
        with patch('acas_pro.services.user_service.hash_password') as mock_hash:
            mock_hash.return_value = "hashed_password"
            registered = self.service.register(
                username="testuser",
                email="test@example.com",
                password="password123"
            )
        user = self.service.get_current(registered.id)
        assert user is not None
        assert user.id == registered.id

    def test_get_current_not_found(self):
        user = self.service.get_current("NONEXISTENT")
        assert user is None

    def test_update_profile(self):
        with patch('acas_pro.services.user_service.hash_password') as mock_hash:
            mock_hash.return_value = "hashed_password"
            registered = self.service.register(
                username="testuser",
                email="test@example.com",
                password="password123"
            )
        result = self.service.update_profile(
            registered.id,
            display_name="New Name",
            avatar_url="https://example.com/avatar.png"
        )
        assert result is True

    def test_update_profile_empty(self):
        with patch('acas_pro.services.user_service.hash_password') as mock_hash:
            mock_hash.return_value = "hashed_password"
            registered = self.service.register(
                username="testuser",
                email="test@example.com",
                password="password123"
            )
        result = self.service.update_profile(registered.id)
        assert result is True

    def test_change_password(self):
        with patch('acas_pro.services.user_service.hash_password') as mock_hash:
            mock_hash.return_value = "old_hash"
            registered = self.service.register(
                username="testuser",
                email="test@example.com",
                password="oldpass"
            )
        with patch('acas_pro.services.user_service.verify_password') as mock_verify:
            mock_verify.return_value = True
            with patch('acas_pro.services.user_service.hash_password') as mock_hash2:
                mock_hash2.return_value = "new_hash"
                result = self.service.change_password(
                    registered.id,
                    old_password="oldpass",
                    new_password="newpass"
                )
                assert result is True

    def test_change_password_wrong_old(self):
        with patch('acas_pro.services.user_service.hash_password') as mock_hash:
            mock_hash.return_value = "old_hash"
            registered = self.service.register(
                username="testuser",
                email="test@example.com",
                password="oldpass"
            )
        with patch('acas_pro.services.user_service.verify_password') as mock_verify:
            mock_verify.return_value = False
            result = self.service.change_password(
                registered.id,
                old_password="wrongpass",
                new_password="newpass"
            )
            assert result is False

    def test_logout(self):
        with patch('acas_pro.services.user_service.hash_password') as mock_hash:
            mock_hash.return_value = "hashed_password"
            registered = self.service.register(
                username="testuser",
                email="test@example.com",
                password="password123"
            )
        result = self.service.logout(registered.id)
        assert result is True

    def test_is_authenticated(self):
        with patch('acas_pro.services.user_service.hash_password') as mock_hash:
            mock_hash.return_value = "hashed_password"
            registered = self.service.register(
                username="testuser",
                email="test@example.com",
                password="password123"
            )
        result = self.service.is_authenticated(registered.id)
        assert result is True

    def test_is_authenticated_not_found(self):
        result = self.service.is_authenticated("NONEXISTENT")
        assert result is False

    def test_login_guest(self):
        user = self.service.login_guest()
        assert user is not None
        assert user.role == "guest"
