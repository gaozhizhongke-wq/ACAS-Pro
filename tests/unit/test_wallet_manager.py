# -*- coding: utf-8 -*-
"""Tests for blockchain/wallet_manager.py"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

from acas_pro.blockchain.wallet_manager import (
    WalletManager,
    Wallet,
    Transaction,
    TransactionType,
    TransactionStatus,
)


class TestWalletManager:
    """Test WalletManager class"""

    @pytest.fixture
    def mock_db(self):
        """Mock DatabaseManager"""
        db = MagicMock()
        db.fetch_one.return_value = None
        db.fetch_all.return_value = []
        return db

    @pytest.fixture
    def wallet_manager(self, mock_db):
        """Create WalletManager with mocked DB"""
        with patch('acas_pro.blockchain.wallet_manager.DatabaseManager', return_value=mock_db):
            wm = WalletManager()
            wm.db = mock_db
            return wm

    @pytest.fixture
    def sample_wallet(self):
        """Create a sample wallet"""
        return Wallet(
            id='wal_20260101000000',
            owner_id='user_001',
            owner_type='user',
            address='0x1234567890abcdef',
            chain_type='ethereum',
            balances={'USDT': 1000.0, 'USDC': 500.0},
            encrypted_private_key='encrypted_data',
            is_active=True,
            created_at='2026-01-01T00:00:00',
            last_activity=None,
        )

    @pytest.fixture
    def sample_transaction(self):
        """Create a sample transaction"""
        return Transaction(
            id='tx_20260101000000',
            tx_type=TransactionType.TRANSFER,
            from_wallet='0x1234567890abcdef',
            to_wallet='0xabcdef123456789',
            amount=100.0,
            currency='USDT',
            fee=1.0,
            status=TransactionStatus.PENDING,
            blockchain_tx_hash=None,
            block_number=None,
            confirmations=0,
            settlement_id=None,
            description='Test transfer',
            created_at='2026-01-01T00:00:00',
            confirmed_at=None,
        )

    # ===== 初始化测试 =====
    def test_init(self, mock_db):
        """Test WalletManager initialization"""
        with patch('acas_pro.blockchain.wallet_manager.DatabaseManager', return_value=mock_db):
            wm = WalletManager()
            assert wm.db is not None

    def test_supported_chains(self):
        """Test SUPPORTED_CHAINS constant"""
        assert 'ethereum' in WalletManager.SUPPORTED_CHAINS
        assert 'bsc' in WalletManager.SUPPORTED_CHAINS
        assert 'polygon' in WalletManager.SUPPORTED_CHAINS

    def test_supported_tokens(self):
        """Test SUPPORTED_TOKENS constant"""
        assert 'USDT' in WalletManager.SUPPORTED_TOKENS
        assert 'USDC' in WalletManager.SUPPORTED_TOKENS

    # ===== 钱包管理测试 =====
    def test_create_wallet(self, wallet_manager, mock_db):
        """Test creating a wallet"""
        with patch('acas_pro.blockchain.wallet_manager.encrypt_data', return_value='encrypted'):
            wallet = wallet_manager.create_wallet(
                owner_id='user_001',
                owner_type='user',
                chain_type='ethereum',
            )
            assert wallet is not None
            assert wallet.owner_id == 'user_001'
            assert wallet.chain_type == 'ethereum'
            mock_db.execute.assert_called()

    def test_get_wallet_found(self, wallet_manager, mock_db, sample_wallet):
        """Test getting an existing wallet"""
        row = {
            'id': sample_wallet.id,
            'owner_id': sample_wallet.owner_id,
            'owner_type': sample_wallet.owner_type,
            'address': sample_wallet.address,
            'chain_type': sample_wallet.chain_type,
            'balances': '{"USDT": 1000.0}',
            'encrypted_private_key': sample_wallet.encrypted_private_key,
            'is_active': 1,
            'created_at': sample_wallet.created_at,
            'last_activity': sample_wallet.last_activity,
        }
        mock_db.fetch_one.return_value = row
        wallet = wallet_manager.get_wallet(sample_wallet.id)
        assert wallet is not None
        assert wallet.id == sample_wallet.id

    def test_get_wallet_not_found(self, wallet_manager, mock_db):
        """Test getting non-existent wallet"""
        mock_db.fetch_one.return_value = None
        wallet = wallet_manager.get_wallet('nonexistent')
        assert wallet is None

    def test_get_wallet_by_address(self, wallet_manager, mock_db, sample_wallet):
        """Test getting wallet by address"""
        row = {
            'id': sample_wallet.id,
            'owner_id': sample_wallet.owner_id,
            'owner_type': sample_wallet.owner_type,
            'address': sample_wallet.address,
            'chain_type': sample_wallet.chain_type,
            'balances': '{"USDT": 1000.0}',
            'encrypted_private_key': sample_wallet.encrypted_private_key,
            'is_active': 1,
            'created_at': sample_wallet.created_at,
            'last_activity': sample_wallet.last_activity,
        }
        mock_db.fetch_one.return_value = row
        wallet = wallet_manager.get_wallet_by_address(sample_wallet.address)
        assert wallet is not None
        assert wallet.address == sample_wallet.address

    def test_get_wallets_by_owner(self, wallet_manager, mock_db, sample_wallet):
        """Test getting wallets by owner"""
        rows = [{
            'id': sample_wallet.id,
            'owner_id': sample_wallet.owner_id,
            'owner_type': sample_wallet.owner_type,
            'address': sample_wallet.address,
            'chain_type': sample_wallet.chain_type,
            'balances': '{"USDT": 1000.0}',
            'encrypted_private_key': sample_wallet.encrypted_private_key,
            'is_active': 1,
            'created_at': sample_wallet.created_at,
            'last_activity': sample_wallet.last_activity,
        }]
        mock_db.fetch_all.return_value = rows
        wallets = wallet_manager.get_wallets_by_owner('user_001')
        assert len(wallets) == 1
        assert wallets[0].owner_id == 'user_001'

    # ===== 交易管理测试 =====
    def test_create_transaction(self, wallet_manager, mock_db, sample_transaction):
        """Test creating a transaction"""
        with patch.object(wallet_manager, '_save_transaction'):
            tx = wallet_manager.create_transaction(
                tx_type=TransactionType.TRANSFER,
                from_wallet='0x123',
                to_wallet='0xabc',
                amount=100.0,
            )
            assert tx is not None
            assert tx.tx_type == TransactionType.TRANSFER
            assert tx.amount == 100.0

    def test_execute_transfer_success(self, wallet_manager, mock_db, sample_wallet):
        """Test executing a transfer"""
        with patch.object(wallet_manager, 'get_wallet', return_value=sample_wallet):
            with patch.object(wallet_manager, '_execute_on_blockchain', return_value={
                'success': True,
                'tx_hash': '0xabc',
                'block_number': 12345,
            }):
                with patch.object(wallet_manager, '_save_wallet'):
                    result = wallet_manager.execute_transfer(
                        from_wallet_id=sample_wallet.id,
                        to_address='0xabcdef',
                        amount=100.0,
                    )
                    assert result['success'] is True
                    assert 'transaction_id' in result

    def test_execute_transfer_wallet_not_found(self, wallet_manager):
        """Test transfer with non-existent wallet"""
        with patch.object(wallet_manager, 'get_wallet', return_value=None):
            result = wallet_manager.execute_transfer(
                from_wallet_id='nonexistent',
                to_address='0xabc',
                amount=100.0,
            )
            assert result['success'] is False
            assert 'Wallet not found' in result['error']

    def test_get_transactions(self, wallet_manager, mock_db):
        """Test getting transactions"""
        rows = []
        mock_db.fetch_all.return_value = rows
        txs = wallet_manager.get_transactions(limit=10)
        assert isinstance(txs, list)

    # ===== 余额和查询测试 =====
    def test_get_balance_summary(self, wallet_manager, mock_db, sample_wallet):
        """Test getting balance summary"""
        mock_db.fetch_all.return_value = [{
            'id': sample_wallet.id,
            'owner_id': sample_wallet.owner_id,
            'owner_type': sample_wallet.owner_type,
            'address': sample_wallet.address,
            'chain_type': sample_wallet.chain_type,
            'balances': '{"USDT": 1000.0, "USDC": 500.0}',
            'encrypted_private_key': None,
            'is_active': 1,
            'created_at': sample_wallet.created_at,
            'last_activity': None,
        }]
        summary = wallet_manager.get_balance_summary('user_001')
        assert isinstance(summary, dict)

    def test_get_explorer_url(self, wallet_manager):
        """Test getting explorer URL"""
        url = wallet_manager.get_explorer_url('ethereum', '0xabc')
        assert 'etherscan.io' in url

        url = wallet_manager.get_explorer_url('bsc', '0xabc')
        assert 'bscscan.com' in url

    # ===== 工具方法测试 =====
    def test_estimate_fee(self, wallet_manager):
        """Test fee estimation"""
        fee_usdt = wallet_manager._estimate_fee('USDT')
        assert fee_usdt == 1.0

        fee_eth = wallet_manager._estimate_fee('ETH')
        assert fee_eth == 0.001

    def test_execute_on_blockchain(self, wallet_manager, sample_transaction):
        """Test blockchain execution simulation"""
        result = wallet_manager._execute_on_blockchain(sample_transaction)
        assert result['success'] is True
        assert 'tx_hash' in result
        assert 'block_number' in result


class TestWallet:
    """Test Wallet dataclass"""

    def test_wallet_creation(self):
        """Test Wallet creation"""
        wallet = Wallet(
            id='wal_001',
            owner_id='user_001',
            owner_type='user',
            address='0x123',
        )
        assert wallet.id == 'wal_001'
        assert wallet.balances == {}

    def test_get_balance(self):
        """Test get_balance method"""
        wallet = Wallet(
            id='wal_001',
            owner_id='user_001',
            owner_type='user',
            address='0x123',
            balances={'USDT': 1000.0, 'USDC': 500.0},
        )
        assert wallet.get_balance('USDT') == 1000.0
        assert wallet.get_balance('USDC') == 500.0
        assert wallet.get_balance('ETH') == 0.0

    def test_update_balance(self):
        """Test update_balance method"""
        wallet = Wallet(
            id='wal_001',
            owner_id='user_001',
            owner_type='user',
            address='0x123',
            balances={'USDT': 1000.0},
        )
        wallet.update_balance('USDT', -100.0)
        assert wallet.get_balance('USDT') == 900.0

        wallet.update_balance('USDT', -2000.0)  # Should not go below 0
        assert wallet.get_balance('USDT') == 0.0


class TestTransaction:
    """Test Transaction dataclass"""

    def test_transaction_creation(self):
        """Test Transaction creation"""
        tx = Transaction(
            id='tx_001',
            tx_type=TransactionType.TRANSFER,
            from_wallet='0x123',
            to_wallet='0xabc',
            amount=100.0,
        )
        assert tx.id == 'tx_001'
        assert tx.status == TransactionStatus.PENDING

    def test_get_total_amount(self):
        """Test get_total_amount method"""
        tx = Transaction(
            id='tx_001',
            tx_type=TransactionType.TRANSFER,
            from_wallet='0x123',
            to_wallet='0xabc',
            amount=100.0,
            fee=1.0,
        )
        assert tx.get_total_amount() == 101.0


class TestEnums:
    """Test enums"""

    def test_transaction_type_values(self):
        """Test TransactionType enum values"""
        assert TransactionType.DEPOSIT.value == 'deposit'
        assert TransactionType.WITHDRAWAL.value == 'withdrawal'
        assert TransactionType.TRANSFER.value == 'transfer'
        assert TransactionType.SETTLEMENT.value == 'settlement'
        assert TransactionType.FEE.value == 'fee'

    def test_transaction_status_values(self):
        """Test TransactionStatus enum values"""
        assert TransactionStatus.PENDING.value == 'pending'
        assert TransactionStatus.CONFIRMING.value == 'confirming'
        assert TransactionStatus.COMPLETED.value == 'completed'
        assert TransactionStatus.FAILED.value == 'failed'
        assert TransactionStatus.CANCELLED.value == 'cancelled'
