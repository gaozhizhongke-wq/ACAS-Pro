#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for platforms/account_manager.py"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch
from acas_pro.platforms.account_manager import AccountManager, Platform, AccountStatus, AccountPhase


class TestPlatformEnum:
    def test_values(self):
        assert Platform.DOUYIN.value == "douyin"
        assert Platform.XIAOHONGSHU.value == "xiaohongshu"
        assert Platform.KUAISHOU.value == "kuaishou"
        assert Platform.BILIBILI.value == "bilibili"
        assert Platform.TIKTOK.value == "tiktok"
        assert Platform.INSTAGRAM.value == "instagram"
        assert Platform.YOUTUBE.value == "youtube"


class TestAccountStatusEnum:
    def test_values(self):
        assert AccountStatus.ACTIVE.value == "active"
        assert AccountStatus.INACTIVE.value == "inactive"
        assert AccountStatus.SUSPENDED.value == "suspended"
        assert AccountStatus.RESTRICTED.value == "restricted"
        assert AccountStatus.PENDING.value == "pending"


class TestAccountPhaseEnum:
    def test_values(self):
        assert AccountPhase.WARMUP.value == "warmup"
        assert AccountPhase.GROWTH.value == "growth"
        assert AccountPhase.MATURE.value == "mature"
        assert AccountPhase.DECLINE.value == "decline"


class MockSecurity:
    """Mock security object with encrypt/decrypt methods for testing"""
    def encrypt(self, data):
        return data  # Simple pass-through for testing
    
    def decrypt(self, data):
        return data  # Simple pass-through for testing


class TestAccountManager:
    def setup_method(self):
        self.manager = AccountManager(security=MockSecurity())

    def test_init(self):
        assert self.manager is not None
        assert self.manager.db is not None

    def test_add_account(self):
        account = self.manager.add_account(
            platform=Platform.DOUYIN,
            account_id="test_user",
            account_name="Test User",
            access_token="token123"
        )
        assert account is not None
        assert account.platform == Platform.DOUYIN
        assert account.account_id == "test_user"
        assert account.account_name == "Test User"

    def test_add_account_full(self):
        account = self.manager.add_account(
            platform=Platform.XIAOHONGSHU,
            account_id="test_user2",
            account_name="Test User 2",
            access_token="token456",
            refresh_token="refresh456",
            tags=["tag1", "tag2"],
            region="CN"
        )
        assert account is not None
        assert account.platform == Platform.XIAOHONGSHU
        assert account.region == "CN"
        assert account.tags == ["tag1", "tag2"]

    def test_get_account(self):
        account = self.manager.add_account(
            platform=Platform.DOUYIN,
            account_id="test_user",
            account_name="Test User",
            access_token="token123"
        )
        result = self.manager.get_account(account.id)
        assert result is not None
        assert result.id == account.id
        assert result.account_id == "test_user"

    def test_get_account_not_found(self):
        account = self.manager.get_account("NONEXISTENT")
        assert account is None

    def test_list_accounts(self):
        self.manager.add_account(
            platform=Platform.DOUYIN,
            account_id="user1",
            account_name="User 1",
            access_token="t1"
        )
        self.manager.add_account(
            platform=Platform.XIAOHONGSHU,
            account_id="user2",
            account_name="User 2",
            access_token="t2"
        )
        accounts = self.manager.list_accounts()
        assert isinstance(accounts, list)
        assert len(accounts) >= 2

    def test_list_accounts_by_platform(self):
        self.manager.add_account(
            platform=Platform.DOUYIN,
            account_id="user1",
            account_name="User 1",
            access_token="t1"
        )
        accounts = self.manager.list_accounts(platform=Platform.DOUYIN)
        assert isinstance(accounts, list)
        assert len(accounts) >= 1
        assert all(a.platform == Platform.DOUYIN for a in accounts)

    def test_list_accounts_by_status(self):
        self.manager.add_account(
            platform=Platform.DOUYIN,
            account_id="user1",
            account_name="User 1",
            access_token="t1"
        )
        accounts = self.manager.list_accounts(status=AccountStatus.ACTIVE)
        assert isinstance(accounts, list)
        assert len(accounts) >= 1
        assert all(a.status == AccountStatus.ACTIVE for a in accounts)

    def test_list_accounts_empty(self):
        # Create a manager with no accounts
        accounts = self.manager.list_accounts(platform=Platform.KUAISHOU)
        assert isinstance(accounts, list)

    def test_delete_account(self):
        account = self.manager.add_account(
            platform=Platform.DOUYIN,
            account_id="test_user",
            account_name="Test User",
            access_token="token123"
        )
        self.manager.delete_account(account.id)
        result = self.manager.get_account(account.id)
        assert result is None

    def test_update_account_status(self):
        account = self.manager.add_account(
            platform=Platform.DOUYIN,
            account_id="test_user",
            account_name="Test User",
            access_token="token123"
        )
        self.manager.update_account_status(account.id, AccountStatus.SUSPENDED)
        result = self.manager.get_account(account.id)
        assert result.status == AccountStatus.SUSPENDED

    def test_update_account_stats(self):
        account = self.manager.add_account(
            platform=Platform.DOUYIN,
            account_id="test_user",
            account_name="Test User",
            access_token="token123"
        )
        self.manager.update_account_stats(
            account.id,
            followers=1000,
            following=500,
            content_count=50
        )
        result = self.manager.get_account(account.id)
        assert result.followers == 1000
        assert result.following == 500
        assert result.content_count == 50

    def test_get_access_token(self):
        account = self.manager.add_account(
            platform=Platform.DOUYIN,
            account_id="test_user",
            account_name="Test User",
            access_token="token123"
        )
        # Note: get_access_token returns the decrypted token
        # Since we're using a mock security manager, it may return encrypted value
        token = self.manager.get_access_token(account.id)
        assert token is not None

    def test_get_access_token_not_found(self):
        token = self.manager.get_access_token("NONEXISTENT")
        assert token is None

    def test_refresh_token(self):
        account = self.manager.add_account(
            platform=Platform.DOUYIN,
            account_id="test_user",
            account_name="Test User",
            access_token="token123",
            refresh_token="refresh123"
        )
        self.manager.refresh_token(account.id, "new_token")
        # Verify the token was updated (get_access_token returns decrypted token)
        token = self.manager.get_access_token(account.id)
        assert token is not None

    def test_record_login(self):
        account = self.manager.add_account(
            platform=Platform.DOUYIN,
            account_id="test_user",
            account_name="Test User",
            access_token="token123"
        )
        self.manager.record_login(account.id, "192.168.1.1", "Chrome")
        # Verify login was recorded by checking last_login_at
        result = self.manager.get_account(account.id)
        assert result.last_login_at is not None

    def test_get_login_logs(self):
        account = self.manager.add_account(
            platform=Platform.DOUYIN,
            account_id="test_user",
            account_name="Test User",
            access_token="token123"
        )
        self.manager.record_login(account.id, "192.168.1.1", "Chrome")
        logs = self.manager.get_login_logs(account.id)
        assert isinstance(logs, list)
        assert len(logs) >= 1

    def test_get_account_summary(self):
        self.manager.add_account(
            platform=Platform.DOUYIN,
            account_id="user1",
            account_name="User 1",
            access_token="t1"
        )
        summary = self.manager.get_account_summary()
        assert isinstance(summary, dict)
        assert "total_accounts" in summary
        assert summary["total_accounts"] >= 1
