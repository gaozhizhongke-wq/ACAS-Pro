"""
结算引擎 - 智能分账与结算管理
"""

import json
import hashlib
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from ..core.config import config
from ..core.logging import get_logger
from ..core.database import DatabaseManager

logger = get_logger(__name__)


class SettlementStatus(Enum):
    """结算状态"""
    PENDING = "pending"                # 待结算
    PROCESSING = "processing"          # 结算中
    COMPLETED = "completed"            # 已完成
    FAILED = "failed"                  # 失败
    DISPUTED = "disputed"              # 争议中


class SettlementType(Enum):
    """结算类型"""
    REVENUE_SHARE = "revenue_share"    # 收益分成
    COST_SPLIT = "cost_split"          # 成本分摊
    COMMISSION = "commission"          # 佣金结算
    BONUS = "bonus"                    # 奖励结算
    REFUND = "refund"                  # 退款结算


@dataclass
class SettlementParty:
    """结算参与方"""
    party_id: str                      # 参与方ID
    party_type: str                    # 类型：platform/creator/supplier/affiliate
    name: str                          # 名称
    wallet_address: Optional[str] = None  # 钱包地址
    share_percentage: float = 0.0      # 分成比例
    fixed_amount: Optional[float] = None  # 固定金额
    
    def calculate_share(self, total_amount: float) -> float:
        """计算应得金额"""
        if self.fixed_amount is not None:
            return self.fixed_amount
        return total_amount * (self.share_percentage / 100)


@dataclass
class SettlementRecord:
    """结算记录"""
    id: str
    settlement_type: SettlementType
    
    # 关联信息
    source_id: str                     # 来源ID（订单/广告/内容等）
    source_type: str                   # 来源类型
    
    # 金额
    total_amount: float                # 总金额
    currency: str = "CNY"              # 货币
    
    # 参与方
    parties: List[SettlementParty] = field(default_factory=list)
    
    # 分配明细
    distribution: Dict[str, float] = field(default_factory=dict)  # {party_id: amount}
    
    # 状态
    status: SettlementStatus = SettlementStatus.PENDING
    
    # 区块链记录
    blockchain_tx_hash: Optional[str] = None
    block_number: Optional[int] = None
    confirmed_at: Optional[str] = None
    
    # 时间
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    settled_at: Optional[str] = None
    
    # 元数据
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_distribution(self) -> Dict[str, float]:
        """计算分配方案"""
        distribution = {}
        remaining = self.total_amount
        
        # 先处理固定金额
        for party in self.parties:
            if party.fixed_amount is not None:
                amount = min(party.fixed_amount, remaining)
                distribution[party.party_id] = amount
                remaining -= amount
        
        # 再按比例分配剩余
        percentage_parties = [p for p in self.parties if p.fixed_amount is None]
        total_percentage = sum(p.share_percentage for p in percentage_parties)
        
        if total_percentage > 0 and remaining > 0:
            for party in percentage_parties:
                amount = remaining * (party.share_percentage / total_percentage)
                distribution[party.party_id] = round(amount, 2)
        
        self.distribution = distribution
        return distribution
    
    def generate_hash(self) -> str:
        """生成结算记录哈希"""
        data = {
            'id': self.id,
            'total_amount': self.total_amount,
            'distribution': self.distribution,
            'created_at': self.created_at,
        }
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()


# Tables managed by core/schema.py — do not add CREATE TABLE here


class SettlementEngine:
    """结算引擎"""
    
    # 预设分账模板
    SETTLEMENT_TEMPLATES = {
        'content_revenue': {
            'name': '内容收益分成',
            'parties': [
                {'type': 'platform', 'share': 30},
                {'type': 'creator', 'share': 50},
                {'type': 'affiliate', 'share': 20},
            ]
        },
        'ad_revenue': {
            'name': '广告收益分成',
            'parties': [
                {'type': 'platform', 'share': 20},
                {'type': 'advertiser', 'share': 70},
                {'type': 'agency', 'share': 10},
            ]
        },
        'ecommerce_sale': {
            'name': '电商销售分成',
            'parties': [
                {'type': 'platform', 'share': 5},
                {'type': 'seller', 'share': 85},
                {'type': 'logistics', 'share': 10},
            ]
        },
        'live_streaming': {
            'name': '直播打赏分成',
            'parties': [
                {'type': 'platform', 'share': 50},
                {'type': 'streamer', 'share': 45},
                {'type': 'guild', 'share': 5},
            ]
        },
    }
    
    def __init__(self):
        self.db = DatabaseManager()
    
    def create_settlement(
        self,
        settlement_type: SettlementType,
        source_id: str,
        total_amount: float,
        parties: List[SettlementParty],
        source_type: str = "",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ) -> SettlementRecord:
        """创建结算记录"""
        settlement_id = f"stl_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        record = SettlementRecord(
            id=settlement_id,
            settlement_type=settlement_type,
            source_id=source_id,
            source_type=source_type,
            total_amount=total_amount,
            parties=parties,
            description=description,
            metadata=metadata or {}
        )
        
        # 计算分配
        record.calculate_distribution()
        
        # 保存
        self._save_settlement(record)
        
        logger.info(f"Created settlement: {settlement_id} for {source_id}")
        return record
    
    def create_from_template(
        self,
        template_name: str,
        source_id: str,
        total_amount: float,
        party_configs: List[Dict[str, Any]],  # [{'party_id': '', 'name': '', 'wallet': ''}]
        **kwargs
    ) -> Optional[SettlementRecord]:
        """从模板创建结算"""
        template = self.SETTLEMENT_TEMPLATES.get(template_name)
        if not template:
            logger.error(f"Settlement template not found: {template_name}")
            return None
        
        parties = []
        for i, party_config in enumerate(party_configs):
            template_party = template['parties'][i] if i < len(template['parties']) else {'share': 0}
            
            party = SettlementParty(
                party_id=party_config['party_id'],
                party_type=template_party.get('type', 'other'),
                name=party_config['name'],
                wallet_address=party_config.get('wallet'),
                share_percentage=template_party.get('share', 0)
            )
            parties.append(party)
        
        settlement_type = SettlementType.REVENUE_SHARE
        if template_name == 'ad_revenue':
            settlement_type = SettlementType.COMMISSION
        elif template_name == 'ecommerce_sale':
            settlement_type = SettlementType.REVENUE_SHARE
        
        return self.create_settlement(
            settlement_type=settlement_type,
            source_id=source_id,
            total_amount=total_amount,
            parties=parties,
            description=f"{template['name']} - {source_id}",
            **kwargs
        )
    
    def _save_settlement(self, record: SettlementRecord) -> None:
        """保存结算记录"""
        self.db.execute("""
            INSERT OR REPLACE INTO settlements (
                id, settlement_type, source_id, source_type, total_amount,
                currency, parties, distribution, status, blockchain_tx_hash,
                block_number, confirmed_at, created_at, settled_at,
                description, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.id,
            record.settlement_type.value,
            record.source_id,
            record.source_type,
            record.total_amount,
            record.currency,
            json.dumps([p.__dict__ for p in record.parties]),
            json.dumps(record.distribution),
            record.status.value,
            record.blockchain_tx_hash,
            record.block_number,
            record.confirmed_at,
            record.created_at,
            record.settled_at,
            record.description,
            json.dumps(record.metadata)
        ))
    
    def get_settlement(self, settlement_id: str) -> Optional[SettlementRecord]:
        """获取结算记录"""
        row = self.db.fetchone(
            "SELECT * FROM settlements WHERE id = ?",
            (settlement_id,)
        )
        if row:
            return self._row_to_settlement(row)
        return None
    
    def get_settlements_by_source(
        self,
        source_id: str,
        source_type: Optional[str] = None
    ) -> List[SettlementRecord]:
        """获取来源的结算记录"""
        if source_type:
            rows = self.db.fetchall(
                "SELECT * FROM settlements WHERE source_id = ? AND source_type = ? ORDER BY created_at DESC",
                (source_id, source_type)
            )
        else:
            rows = self.db.fetchall(
                "SELECT * FROM settlements WHERE source_id = ? ORDER BY created_at DESC",
                (source_id,)
            )
        return [self._row_to_settlement(row) for row in rows]
    
    def _row_to_settlement(self, row: Dict[str, Any]) -> SettlementRecord:
        """数据库行转结算对象"""
        parties_data = json.loads(row['parties'] or '[]')
        parties = [SettlementParty(**p) for p in parties_data]
        
        return SettlementRecord(
            id=row['id'],
            settlement_type=SettlementType(row['settlement_type']),
            source_id=row['source_id'],
            source_type=row['source_type'] or "",
            total_amount=row['total_amount'],
            currency=row['currency'] or "CNY",
            parties=parties,
            distribution=json.loads(row['distribution'] or '{}'),
            status=SettlementStatus(row['status']) if row['status'] else SettlementStatus.PENDING,
            blockchain_tx_hash=row['blockchain_tx_hash'],
            block_number=row['block_number'],
            confirmed_at=row['confirmed_at'],
            created_at=row['created_at'],
            settled_at=row['settled_at'],
            description=row['description'] or "",
            metadata=json.loads(row['metadata'] or '{}'),
        )
    
    def execute_settlement(self, settlement_id: str) -> Dict[str, Any]:
        """执行结算"""
        record = self.get_settlement(settlement_id)
        if not record:
            return {'success': False, 'error': 'Settlement not found'}
        
        if record.status != SettlementStatus.PENDING:
            return {'success': False, 'error': f'Invalid status: {record.status.value}'}
        
        # 更新状态
        record.status = SettlementStatus.PROCESSING
        self._save_settlement(record)
        
        results = {
            'success': True,
            'settlement_id': settlement_id,
            'transactions': [],
        }
        
        # 为每个参与方创建结算明细
        for party_id, amount in record.distribution.items():
            party = next((p for p in record.parties if p.party_id == party_id), None)
            if party and party.wallet_address:
                detail_id = f"{settlement_id}_{party_id}"
                
                # 模拟区块链转账
                tx_result = self._execute_blockchain_transfer(
                    to_address=party.wallet_address,
                    amount=amount,
                    currency=record.currency
                )
                
                self.db.execute("""
                    INSERT OR REPLACE INTO settlement_details (
                        id, settlement_id, party_id, party_type, amount,
                        wallet_address, tx_hash, status, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    detail_id, settlement_id, party_id, party.party_type,
                    amount, party.wallet_address,
                    tx_result.get('tx_hash'), 'completed',
                    datetime.now().isoformat()
                ))
                
                results['transactions'].append({
                    'party_id': party_id,
                    'amount': amount,
                    'tx_hash': tx_result.get('tx_hash'),
                })
        
        # 更新结算状态
        record.status = SettlementStatus.COMPLETED
        record.settled_at = datetime.now().isoformat()
        record.blockchain_tx_hash = results['transactions'][0]['tx_hash'] if results['transactions'] else None
        self._save_settlement(record)
        
        return results
    
    def _execute_blockchain_transfer(
        self,
        to_address: str,
        amount: float,
        currency: str
    ) -> Dict[str, Any]:
        """执行区块链转账（模拟）"""
        # 生成模拟交易哈希
        tx_data = f"{to_address}:{amount}:{currency}:{datetime.now().isoformat()}"
        tx_hash = "0x" + hashlib.sha256(tx_data.encode()).hexdigest()[:64]
        
        return {
            'success': True,
            'tx_hash': tx_hash,
            'block_number': 12345678,
            'gas_used': 21000,
        }
    
    def get_settlement_statistics(
        self,
        start_date: str,
        end_date: str,
        party_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """获取结算统计"""
        query = """
            SELECT * FROM settlements 
            WHERE created_at >= ? AND created_at <= ?
        """
        params = [start_date, end_date]
        
        if party_id:
            query += " AND parties LIKE ?"
            params.append(f'%"party_id": "{party_id}"%')
        
        rows = self.db.fetchall(query, tuple(params))
        settlements = [self._row_to_settlement(row) for row in rows]
        
        total_settlements = len(settlements)
        total_amount = sum(s.total_amount for s in settlements)
        completed = len([s for s in settlements if s.status == SettlementStatus.COMPLETED])
        
        # 按类型统计
        by_type = {}
        for s in settlements:
            t = s.settlement_type.value
            by_type[t] = by_type.get(t, {'count': 0, 'amount': 0.0})
            by_type[t]['count'] += 1
            by_type[t]['amount'] += s.total_amount
        
        return {
            'total_settlements': total_settlements,
            'total_amount': total_amount,
            'completed': completed,
            'completion_rate': completed / total_settlements if total_settlements > 0 else 0,
            'by_type': by_type,
        }
    
    def verify_settlement(self, settlement_id: str) -> Dict[str, Any]:
        """验证结算记录（区块链验证）"""
        record = self.get_settlement(settlement_id)
        if not record:
            return {'verified': False, 'error': 'Settlement not found'}
        
        # 重新计算哈希
        current_hash = record.generate_hash()
        
        # 模拟区块链验证
        return {
            'verified': record.status == SettlementStatus.COMPLETED,
            'settlement_id': settlement_id,
            'tx_hash': record.blockchain_tx_hash,
            'block_number': record.block_number,
            'current_hash': current_hash,
            'timestamp': record.settled_at,
        }
    
    def get_templates(self) -> Dict[str, Any]:
        """获取结算模板"""
        return self.SETTLEMENT_TEMPLATES
    
    def complete_settlement(self, settlement_id: str) -> bool:
        """完成结算"""
        try:
            self.db.execute(
                "UPDATE settlements SET status = ?, settled_at = ? WHERE id = ?",
                (SettlementStatus.COMPLETED.value, datetime.now().isoformat(), settlement_id)
            )
            return True
        except Exception as e:
            logger.warning(f"Settlement status update failed: {e}")
            return False
