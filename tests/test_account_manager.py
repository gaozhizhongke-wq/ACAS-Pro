#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Account Manager Tests
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from acas_pro.platforms.account_manager import (
    AccountManager, PlatformAccount, Platform, AccountStatus, AccountPhase, AccountStats
)


class TestPlatform:
    """Platform enum tests"""
    
    def test_platform_values(self):
        """Test platform values"""
        assert Platform.DOUYIN.value == "douyin"
        assert Platform.XIAOHONGSHU.value == "xiaohongshu"
        assert Platform.KUAISHOU.value == "kuaishou"
        assert Platform.BILIBILI.value == "bilibili"


class TestAccountStatus:
    """Account status enum tests"""
    
    def test_status_values(self):
        """Test status values"""
        assert AccountStatus.ACTIVE.value == "active"
        assert AccountStatus.INACTIVE.value == "inactive"
        assert AccountStatus.SUSPENDED.value == "suspended"
        assert AccountStatus.RESTRICTED.value == "restricted"
        assert AccountStatus.PENDING.value == "pending"


class TestAccountPhase:
    """Account phase enum tests"""
    
    def test_phase_values(self):
        """Test phase values"""
        assert AccountPhase.WARMUP.value == "warmup"
        assert AccountPhase.GROWTH.value == "growth"
        assert AccountPhase.MATURE.value == "mature"
        assert AccountPhase.DECLINE.value == "decline"


class TestPlatformAccount:
    """Platform account tests"""
    
    def test_account_creation(self):
        """Test account creation"""
        account = PlatformAccount(
            id="acc_001",
            platform=Platform.DOUYIN,
            account_id="123456",
            account_name="Test Account",
            nickname="TestNick",
            access_token="token123",
            refresh_token="refresh456",
            token_expires_at=datetime.now() + timedelta(hours=1)
        )
        
        assert account.id == "acc_001"
        assert account.platform == Platform.DOUYIN
        assert account.status == AccountStatus.ACTIVE  # default
        assert account.phase == AccountPhase.WARMUP  # default
        assert account.tags == []  # default
    
    def test_account_with_tags(self):
        """Test account with tags"""
        account = PlatformAccount(
            id="acc_001",
            platform=Platform.DOUYIN,
            account_id="123456",
            account_name="Test",
            nickname="Test",
            access_token="token",
            refresh_token="refresh",
            token_expires_at=datetime.now(),
            tags=["美妆", "时尚"]
        )
        
        assert len(account.tags) == 2
        assert "美妆" in account.tags


class TestAccountStats:
    """Account stats tests"""
    
    def test_stats_creation(self):
        """Test stats creation"""
        stats = AccountStats(
            account_id="acc_001",
            date=datetime.now(),
            new_content=5,
            total_views=10000,
            total_likes=500,
            new_followers=100
        )
        
        assert stats.account_id == "acc_001"
        assert stats.new_content == 5
        assert stats.total_views == 10000


class TestAccountManager:
    """Account manager tests"""
    
    @pytest.fixture
    def mock_db(self):
        mock = Mock()
        mock.execute = Mock()
        mock.fetchone = Mock(return_value=None)
        mock.fetchall = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def mock_security(self):
        mock = Mock()
        mock.encrypt = Mock(return_value="encrypted")
        mock.decrypt = Mock(return_value="decrypted")
        return mock
    
    @pytest.fixture
    def manager(self, mock_db, mock_security):
        with patch('acas_pro.platforms.account_manager.DatabaseManager', return_value=mock_db):
            with patch('acas_pro.platforms.account_manager.SessionManager', return_value=mock_security):
                from acas_pro.platforms.account_manager import AccountManager
                return AccountManager()
    
    def test_init(self, manager, mock_db):
        """Test initialization"""
        mock_db.execute.assert_called()
    
    def test_get_account_not_found(self, manager, mock_db):
        """Test get account not found"""
        mock_db.fetchone.return_value = None
        
        result = manager.get_account("nonexistent")
        
        assert result is None
    
    def test_list_accounts_empty(self, manager, mock_db):
        """Test list accounts empty"""
        mock_db.fetchall.return_value = []
        
        accounts = manager.list_accounts()
        
        assert accounts == []
    
    def test_update_account_stats(self, manager, mock_db):
        """Test update account stats"""
        manager.update_account_stats(
            account_id="acc_001",
            followers=1000,
            total_likes=5000
        )
        
        mock_db.execute.assert_called()
    
    def test_get_access_token_not_found(self, manager, mock_db):
        """Test get access token not found"""
        mock_db.fetchone.return_value = None
        
        result = manager.get_access_token("nonexistent")
        
        assert result is None
    
    def test_get_login_logs_empty(self, manager, mock_db):
        """Test get login logs empty"""
        mock_db.fetchall.return_value = []
        
        logs = manager.get_login_logs("acc_001")
        
        assert logs == []
    
    def test_get_account_summary_empty(self, manager, mock_db):
        """Test get account summary empty"""
        mock_db.fetchone.return_value = {
            'total_accounts': 0,
            'active_accounts': 0,
            'suspended_accounts': 0,
            'total_followers': 0,
            'total_content': 0
        }
        mock_db.fetchall.return_value = []
        
        summary = manager.get_account_summary()
        
        assert summary['total_accounts'] == 0
        assert summary['platform_distribution'] == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
