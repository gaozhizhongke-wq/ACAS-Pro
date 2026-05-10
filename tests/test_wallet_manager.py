#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Wallet Manager Tests
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch

from acas_pro.blockchain.wallet_manager import (
    WalletManager, Wallet, Transaction,
    TransactionType, TransactionStatus
)


class TestTransactionType:
    """Transaction type enum tests"""
    
    def test_transaction_type_values(self):
        """Test transaction type values"""
        assert TransactionType.DEPOSIT.value == "deposit"
        assert TransactionType.WITHDRAWAL.value == "withdrawal"
        assert TransactionType.TRANSFER.value == "transfer"
        assert TransactionType.SETTLEMENT.value == "settlement"
        assert TransactionType.FEE.value == "fee"


class TestTransactionStatus:
    """Transaction status enum tests"""
    
    def test_transaction_status_values(self):
        """Test transaction status values"""
        assert TransactionStatus.PENDING.value == "pending"
        assert TransactionStatus.CONFIRMING.value == "confirming"
        assert TransactionStatus.COMPLETED.value == "completed"
        assert TransactionStatus.FAILED.value == "failed"
        assert TransactionStatus.CANCELLED.value == "cancelled"


class TestWallet:
    """Wallet dataclass tests"""
    
    def test_wallet_creation(self):
        """Test wallet creation"""
        wallet = Wallet(
            id="wal_001",
            owner_id="user_001",
            owner_type="user",
            address="0x1234567890abcdef",
            chain_type="ethereum",
            balances={"USDT": 100.0}
        )
        
        assert wallet.id == "wal_001"
        assert wallet.get_balance("USDT") == 100.0
        assert wallet.get_balance("USDC") == 0.0  # default
    
    def test_wallet_update_balance(self):
        """Test wallet balance update"""
        wallet = Wallet(
            id="wal_001",
            owner_id="user_001",
            owner_type="user",
            address="0x1234567890abcdef",
            balances={"USDT": 100.0}
        )
        
        wallet.update_balance("USDT", 50.0)
        assert wallet.get_balance("USDT") == 150.0
        
        wallet.update_balance("USDT", -30.0)
        assert wallet.get_balance("USDT") == 120.0
        
        # Should not go below 0
        wallet.update_balance("USDT", -200.0)
        assert wallet.get_balance("USDT") == 0.0


class TestTransaction:
    """Transaction dataclass tests"""
    
    def test_transaction_creation(self):
        """Test transaction creation"""
        tx = Transaction(
            id="tx_001",
            tx_type=TransactionType.TRANSFER,
            from_wallet="0x123",
            to_wallet="0x456",
            amount=100.0,
            currency="USDT",
            fee=1.0
        )
        
        assert tx.id == "tx_001"
        assert tx.get_total_amount() == 101.0  # amount + fee
        assert tx.status == TransactionStatus.PENDING  # default


class TestWalletManager:
    """Wallet manager tests"""
    
    @pytest.fixture
    def mock_db(self):
        mock = Mock()
        mock.execute = Mock()
        mock.fetch_one = Mock(return_value=None)
        mock.fetch_all = Mock(return_value=[])
        return mock
    
    @pytest.fixture
    def manager(self, mock_db):
        with patch('acas_pro.blockchain.wallet_manager.DatabaseManager', return_value=mock_db):
            with patch('acas_pro.blockchain.wallet_manager.encrypt_data', return_value="encrypted_key"):
                return WalletManager()
    
    def test_init(self, manager, mock_db):
        """Test initialization"""
        mock_db.execute.assert_called()
    
    def test_supported_chains(self, manager):
        """Test supported chains"""
        assert "ethereum" in manager.SUPPORTED_CHAINS
        assert "bsc" in manager.SUPPORTED_CHAINS
        assert "polygon" in manager.SUPPORTED_CHAINS
    
    def test_supported_tokens(self, manager):
        """Test supported tokens"""
        assert "USDT" in manager.SUPPORTED_TOKENS
        assert "USDC" in manager.SUPPORTED_TOKENS
    
    def test_create_wallet(self, manager, mock_db):
        """Test create wallet"""
        with patch('acas_pro.blockchain.wallet_manager.encrypt_data', return_value="encrypted_key"):
            wallet = manager.create_wallet(
                owner_id="user_001",
                owner_type="user",
                chain_type="ethereum"
            )
        
        assert wallet.owner_id == "user_001"
        assert wallet.owner_type == "user"
        assert wallet.chain_type == "ethereum"
        assert wallet.address.startswith("0x")
        mock_db.execute.assert_called()
    
    def test_get_wallet_not_found(self, manager, mock_db):
        """Test get wallet not found"""
        mock_db.fetch_one.return_value = None
        
        result = manager.get_wallet("nonexistent")
        
        assert result is None
    
    def test_get_wallets_by_owner_empty(self, manager, mock_db):
        """Test get wallets by owner empty"""
        mock_db.fetch_all.return_value = []
        
        wallets = manager.get_wallets_by_owner("user_001")
        
        assert wallets == []
    
    def test_create_transaction(self, manager, mock_db):
        """Test create transaction"""
        tx = manager.create_transaction(
            tx_type=TransactionType.TRANSFER,
            from_wallet="0x123",
            to_wallet="0x456",
            amount=100.0,
            currency="USDT",
            fee=1.0,
            description="Test transfer"
        )
        
        assert tx.tx_type == TransactionType.TRANSFER
        assert tx.amount == 100.0
        assert tx.get_total_amount() == 101.0
        mock_db.execute.assert_called()
    
    def test_execute_transfer_wallet_not_found(self, manager, mock_db):
        """Test execute transfer wallet not found"""
        mock_db.fetch_one.return_value = None
        
        result = manager.execute_transfer(
            from_wallet_id="nonexistent",
            to_address="0x456",
            amount=100.0
        )
        
        assert result['success'] is False
        assert 'error' in result
    
    def test_estimate_fee(self, manager):
        """Test estimate fee"""
        fee_usdt = manager._estimate_fee("USDT")
        fee_eth = manager._estimate_fee("ETH")
        
        assert fee_usdt == 1.0
        assert fee_eth == 0.001
    
    def test_execute_on_blockchain(self, manager):
        """Test execute on blockchain"""
        tx = Transaction(
            id="tx_001",
            tx_type=TransactionType.TRANSFER,
            from_wallet="0x123",
            to_wallet="0x456",
            amount=100.0
        )
        
        result = manager._execute_on_blockchain(tx)
        
        assert result['success'] is True
        assert 'tx_hash' in result
        assert result['tx_hash'].startswith("0x")
    
    def test_get_transactions_empty(self, manager, mock_db):
        """Test get transactions empty"""
        mock_db.fetch_all.return_value = []
        
        transactions = manager.get_transactions()
        
        assert transactions == []
    
    def test_get_balance_summary_empty(self, manager, mock_db):
        """Test get balance summary empty"""
        mock_db.fetch_all.return_value = []
        
        summary = manager.get_balance_summary("user_001")
        
        assert summary == {}
    
    def test_get_explorer_url(self, manager):
        """Test get explorer URL"""
        url = manager.get_explorer_url("ethereum", "0x123abc")
        
        assert "etherscan.io" in url
        assert "0x123abc" in url
        
        # Test BSC chain - just verify it returns a valid URL
        url_bsc = manager.get_explorer_url("bsc", "0x456def")
        assert "bscscan.com" in url_bsc or "bsc" in url_bsc.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
