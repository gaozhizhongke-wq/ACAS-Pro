"""
钱包管理 - 区块链钱包与交易管理
"""

import json
import secrets
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from ..core.logging import get_logger
from ..core.database import DatabaseManager
from ..core.security import encrypt_data

logger = get_logger(__name__)


class TransactionType(Enum):
    """交易类型"""

    DEPOSIT = "deposit"  # 充值
    WITHDRAWAL = "withdrawal"  # 提现
    TRANSFER = "transfer"  # 转账
    SETTLEMENT = "settlement"  # 结算
    FEE = "fee"  # 手续费


class TransactionStatus(Enum):
    """交易状态"""

    PENDING = "pending"  # 待处理
    CONFIRMING = "confirming"  # 确认中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"  # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class Wallet:
    """钱包实体"""

    id: str
    owner_id: str  # 所有者ID
    owner_type: str  # 类型：user/shop/platform

    # 地址
    address: str  # 钱包地址
    chain_type: str = "ethereum"  # 链类型：ethereum/bsc/polygon

    # 余额
    balances: Dict[str, float] = field(default_factory=dict)  # {currency: amount}

    # 安全
    encrypted_private_key: Optional[str] = None

    # 状态
    is_active: bool = True

    # 时间
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_activity: Optional[str] = None

    def get_balance(self, currency: str = "USDT") -> float:
        """获取余额"""
        return self.balances.get(currency, 0.0)

    def update_balance(self, currency: str, delta: float) -> None:
        """更新余额"""
        current = self.balances.get(currency, 0.0)
        self.balances[currency] = max(0, current + delta)
        self.last_activity = datetime.now().isoformat()


@dataclass
class Transaction:
    """交易记录"""

    id: str
    tx_type: TransactionType

    # 参与方
    from_wallet: Optional[str]  # 转出钱包
    to_wallet: Optional[str]  # 转入钱包

    # 金额
    amount: float
    currency: str = "USDT"
    fee: float = 0.0

    # 状态
    status: TransactionStatus = TransactionStatus.PENDING

    # 区块链信息
    blockchain_tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    confirmations: int = 0

    # 关联
    settlement_id: Optional[str] = None
    description: str = ""

    # 时间
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    confirmed_at: Optional[str] = None

    def get_total_amount(self) -> float:
        """获取总金额（含手续费）"""
        return self.amount + self.fee


# Tables managed by core/schema.py — do not add CREATE TABLE here


class WalletManager:
    """钱包管理器"""

    SUPPORTED_CHAINS = {
        "ethereum": {
            "name": "Ethereum",
            "symbol": "ETH",
            "decimals": 18,
            "explorer": "https://etherscan.io",
        },
        "bsc": {
            "name": "BSC",
            "symbol": "BNB",
            "decimals": 18,
            "explorer": "https://bscscan.com",
        },
        "polygon": {
            "name": "Polygon",
            "symbol": "MATIC",
            "decimals": 18,
            "explorer": "https://polygonscan.com",
        },
    }

    SUPPORTED_TOKENS = {
        "USDT": {
            "chain": "ethereum",
            "contract": "0xdAC17F958D2ee523a2206206994597C13D831ec7",
        },
        "USDC": {
            "chain": "ethereum",
            "contract": "0xA0b86a33E6441e0A421e56E4773C3C4b0Db7E5f0",
        },
        "DAI": {
            "chain": "ethereum",
            "contract": "0x6B175474E89094C44Da98b954EedeAC495271d0F",
        },
    }

    def __init__(self):
        self.db = DatabaseManager()

    def create_wallet(
        self, owner_id: str, owner_type: str, chain_type: str = "ethereum"
    ) -> Wallet:
        """创建钱包"""
        wallet_id = f"wal_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # 生成地址（模拟）
        address = self._generate_address(chain_type)

        # 生成私钥（模拟，实际应使用加密库）
        private_key = secrets.token_hex(32)
        encrypted_key = encrypt_data(private_key)

        wallet = Wallet(
            id=wallet_id,
            owner_id=owner_id,
            owner_type=owner_type,
            address=address,
            chain_type=chain_type,
            encrypted_private_key=encrypted_key,
            balances={"USDT": 0.0, "USDC": 0.0},
        )

        self._save_wallet(wallet)
        logger.info(f"Created wallet: {wallet_id} for {owner_id}")
        return wallet

    def _generate_address(self, chain_type: str) -> str:
        """生成钱包地址（模拟）"""
        # 实际应使用加密库生成
        random_bytes = secrets.token_bytes(20)
        address = "0x" + random_bytes.hex()
        return address

    def _save_wallet(self, wallet: Wallet) -> None:
        """保存钱包"""
        self.db.execute(
            """
            INSERT OR REPLACE INTO wallets (
                id, owner_id, owner_type, address, chain_type,
                balances, encrypted_private_key, is_active,
                created_at, last_activity
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                wallet.id,
                wallet.owner_id,
                wallet.owner_type,
                wallet.address,
                wallet.chain_type,
                json.dumps(wallet.balances),
                wallet.encrypted_private_key,
                int(wallet.is_active),
                wallet.created_at,
                wallet.last_activity,
            ),
        )

    def get_wallet(self, wallet_id: str) -> Optional[Wallet]:
        """获取钱包"""
        row = self.db.fetch_one("SELECT * FROM wallets WHERE id = ?", (wallet_id,))
        if row:
            return self._row_to_wallet(row)
        return None

    def get_wallet_by_address(self, address: str) -> Optional[Wallet]:
        """通过地址获取钱包"""
        row = self.db.fetch_one("SELECT * FROM wallets WHERE address = ?", (address,))
        if row:
            return self._row_to_wallet(row)
        return None

    def get_wallets_by_owner(self, owner_id: str) -> List[Wallet]:
        """获取所有者的钱包"""
        rows = self.db.fetch_all(
            "SELECT * FROM wallets WHERE owner_id = ? ORDER BY created_at DESC",
            (owner_id,),
        )
        return [self._row_to_wallet(row) for row in rows]

    def _row_to_wallet(self, row: Dict[str, Any]) -> Wallet:
        """数据库行转钱包对象"""
        return Wallet(
            id=row["id"],
            owner_id=row["owner_id"],
            owner_type=row["owner_type"],
            address=row["address"],
            chain_type=row["chain_type"] or "ethereum",
            balances=json.loads(row["balances"] or "{}"),
            encrypted_private_key=row["encrypted_private_key"],
            is_active=bool(row["is_active"]),
            created_at=row["created_at"],
            last_activity=row["last_activity"],
        )

    def create_transaction(
        self,
        tx_type: TransactionType,
        from_wallet: Optional[str],
        to_wallet: Optional[str],
        amount: float,
        currency: str = "USDT",
        fee: float = 0.0,
        description: str = "",
        settlement_id: Optional[str] = None,
    ) -> Transaction:
        """创建交易"""
        tx_id = f"tx_{datetime.now().strftime('%Y%m%d%H%M%S')}"

        tx = Transaction(
            id=tx_id,
            tx_type=tx_type,
            from_wallet=from_wallet,
            to_wallet=to_wallet,
            amount=amount,
            currency=currency,
            fee=fee,
            description=description,
            settlement_id=settlement_id,
        )

        self._save_transaction(tx)

        # 如果是转账，更新余额
        if tx_type == TransactionType.TRANSFER and from_wallet:
            wallet = self.get_wallet_by_address(from_wallet)
            if wallet:
                wallet.update_balance(currency, -(amount + fee))
                self._save_wallet(wallet)

        logger.info(f"Created transaction: {tx_id}")
        return tx

    def _save_transaction(self, tx: Transaction) -> None:
        """保存交易"""
        self.db.execute(
            """
            INSERT OR REPLACE INTO transactions (
                id, tx_type, from_wallet, to_wallet, amount,
                currency, fee, status, blockchain_tx_hash,
                block_number, confirmations, settlement_id,
                description, created_at, confirmed_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                tx.id,
                tx.tx_type.value,
                tx.from_wallet,
                tx.to_wallet,
                tx.amount,
                tx.currency,
                tx.fee,
                tx.status.value,
                tx.blockchain_tx_hash,
                tx.block_number,
                tx.confirmations,
                tx.settlement_id,
                tx.description,
                tx.created_at,
                tx.confirmed_at,
            ),
        )

    def execute_transfer(
        self,
        from_wallet_id: str,
        to_address: str,
        amount: float,
        currency: str = "USDT",
        description: str = "",
    ) -> Dict[str, Any]:
        """执行转账"""
        wallet = self.get_wallet(from_wallet_id)
        if not wallet:
            return {"success": False, "error": "Wallet not found"}

        # 检查余额
        balance = wallet.get_balance(currency)
        if balance < amount:
            return {"success": False, "error": "Insufficient balance"}

        # 计算手续费
        fee = self._estimate_fee(currency)
        if balance < amount + fee:
            return {"success": False, "error": "Insufficient balance for fee"}

        # 创建交易
        tx = self.create_transaction(
            tx_type=TransactionType.TRANSFER,
            from_wallet=wallet.address,
            to_wallet=to_address,
            amount=amount,
            currency=currency,
            fee=fee,
            description=description,
        )

        # 模拟区块链执行
        result = self._execute_on_blockchain(tx)

        if result["success"]:
            tx.status = TransactionStatus.COMPLETED
            tx.blockchain_tx_hash = result["tx_hash"]
            tx.block_number = result["block_number"]
            tx.confirmed_at = datetime.now().isoformat()

            # 更新余额
            wallet.update_balance(currency, -(amount + fee))
            self._save_wallet(wallet)

            # 更新接收方余额
            to_wallet = self.get_wallet_by_address(to_address)
            if to_wallet:
                to_wallet.update_balance(currency, amount)
                self._save_wallet(to_wallet)
        else:
            tx.status = TransactionStatus.FAILED

        self._save_transaction(tx)

        return {
            "success": result["success"],
            "transaction_id": tx.id,
            "tx_hash": tx.blockchain_tx_hash,
            "block_number": tx.block_number,
        }

    def _estimate_fee(self, currency: str) -> float:
        """估算手续费"""
        # 简化估算
        return 1.0 if currency in ["USDT", "USDC"] else 0.001

    def _execute_on_blockchain(self, tx: Transaction) -> Dict[str, Any]:
        """在区块链上执行（模拟）"""
        # 生成模拟交易哈希
        tx_data = f"{tx.from_wallet}:{tx.to_wallet}:{tx.amount}:{tx.created_at}"
        tx_hash = "0x" + hashlib.sha256(tx_data.encode()).hexdigest()[:64]

        return {
            "success": True,
            "tx_hash": tx_hash,
            "block_number": 12345678,
            "gas_used": 21000,
        }

    def get_transactions(
        self,
        wallet_address: Optional[str] = None,
        tx_type: Optional[TransactionType] = None,
        status: Optional[TransactionStatus] = None,
        limit: int = 50,
    ) -> List[Transaction]:
        """获取交易列表"""
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []

        if wallet_address:
            query += " AND (from_wallet = ? OR to_wallet = ?)"
            params.extend([wallet_address, wallet_address])

        if tx_type:
            query += " AND tx_type = ?"
            params.append(tx_type.value)

        if status:
            query += " AND status = ?"
            params.append(status.value)

        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = self.db.fetch_all(query, tuple(params))
        return [self._row_to_transaction(row) for row in rows]

    def _row_to_transaction(self, row: Dict[str, Any]) -> Transaction:
        """数据库行转交易对象"""
        return Transaction(
            id=row["id"],
            tx_type=TransactionType(row["tx_type"]),
            from_wallet=row["from_wallet"],
            to_wallet=row["to_wallet"],
            amount=row["amount"],
            currency=row["currency"] or "USDT",
            fee=row["fee"] or 0.0,
            status=TransactionStatus(row["status"])
            if row["status"]
            else TransactionStatus.PENDING,
            blockchain_tx_hash=row["blockchain_tx_hash"],
            block_number=row["block_number"],
            confirmations=row["confirmations"] or 0,
            settlement_id=row["settlement_id"],
            description=row["description"] or "",
            created_at=row["created_at"],
            confirmed_at=row["confirmed_at"],
        )

    def get_balance_summary(self, owner_id: str) -> Dict[str, float]:
        """获取余额汇总"""
        wallets = self.get_wallets_by_owner(owner_id)

        summary = {}
        for wallet in wallets:
            for currency, amount in wallet.balances.items():
                summary[currency] = summary.get(currency, 0.0) + amount

        return summary

    def get_explorer_url(self, chain_type: str, tx_hash: str) -> str:
        """获取区块链浏览器URL"""
        chain = self.SUPPORTED_CHAINS.get(chain_type, self.SUPPORTED_CHAINS["ethereum"])
        return f"{chain['explorer']}/tx/{tx_hash}"
