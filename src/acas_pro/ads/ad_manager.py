"""
广告账户管理模块
支持多平台广告账户统一管理
重构: 使用 DatabaseManager 替代直接 sqlite3 操作
"""

import json
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict

from ..core.config import config
from ..core.logging import logger
from ..core.security import encrypt_data, decrypt_data
from ..core.database import DatabaseManager


class AdPlatform(Enum):
    """广告平台枚举"""
    OCEAN_ENGINE = "ocean_engine"      # 巨量引擎
    MAGNETIC_ENGINE = "magnetic"       # 磁力引擎
    TENCENT_ADS = "tencent"            # 腾讯广告
    KUAISHOU_ADS = "kuaishou"          # 快手广告
    XIAOHONGSHU = "xiaohongshu"        # 小红书聚光


class CampaignStatus(Enum):
    """广告计划状态"""
    DRAFT = "draft"                    # 草稿
    PENDING = "pending"                # 待审核
    ACTIVE = "active"                  # 投放中
    PAUSED = "paused"                  # 已暂停
    DISABLED = "disabled"              # 已禁用
    FINISHED = "finished"              # 已完成
    REJECTED = "rejected"              # 审核拒绝


class BudgetType(Enum):
    """预算类型"""
    DAILY = "daily"                    # 日预算
    TOTAL = "total"                    # 总预算


@dataclass
class AdCreative:
    """广告创意"""
    id: str
    name: str
    type: str                          # video, image, carousel
    material_urls: List[str]           # 素材URL列表
    title: str
    description: str
    call_to_action: str                # 行动号召按钮
    landing_page: str                  # 落地页
    tracking_url: Optional[str] = None
    impression_url: Optional[str] = None
    click_url: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AdCreative':
        return cls(**data)


@dataclass
class AdSet:
    """广告组"""
    id: str
    name: str
    campaign_id: str
    status: CampaignStatus
    
    # 定向设置
    audience_targeting: Dict[str, Any]  # 人群定向
    geo_targeting: List[str]           # 地域定向
    device_targeting: List[str]        # 设备定向
    time_targeting: Dict[str, Any]     # 时段定向
    
    # 出价设置
    bidding_strategy: str              # 出价策略
    bid_amount: float                  # 出价金额
    budget_type: BudgetType
    budget_amount: float               # 预算金额
    
    # 创意
    creatives: List[AdCreative]
    
    # 统计
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    spend: float = 0.0
    
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['status'] = self.status.value
        data['budget_type'] = self.budget_type.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AdSet':
        data['status'] = CampaignStatus(data['status'])
        data['budget_type'] = BudgetType(data['budget_type'])
        data['creatives'] = [AdCreative.from_dict(c) for c in data.get('creatives', [])]
        return cls(**data)


@dataclass
class AdCampaign:
    """广告计划"""
    id: str
    name: str
    platform: AdPlatform
    account_id: str
    status: CampaignStatus
    
    # 推广目标
    objective: str
    
    # 预算设置
    budget_type: BudgetType
    budget_amount: float
    start_date: str
    
    # Optional fields
    conversion_goal: Optional[str] = None
    end_date: Optional[str] = None
    
    # 广告组
    adsets: Optional[List[AdSet]] = None
    # 统计
    total_impressions: int = 0
    total_clicks: int = 0
    total_conversions: int = 0
    total_spend: float = 0.0
    
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['platform'] = self.platform.value
        data['status'] = self.status.value
        data['budget_type'] = self.budget_type.value
        data['adsets'] = [a.to_dict() for a in self.adsets]
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AdCampaign':
        data['platform'] = AdPlatform(data['platform'])
        data['status'] = CampaignStatus(data['status'])
        data['budget_type'] = BudgetType(data['budget_type'])
        data['adsets'] = [AdSet.from_dict(a) for a in data.get('adsets', [])]
        return cls(**data)


@dataclass
class AdAccount:
    """广告账户"""
    id: str
    platform: AdPlatform
    account_name: str
    account_id: str                     # 平台账户ID
    
    # 认证信息（加密存储）
    access_token: str
    refresh_token: Optional[str] = None
    token_expires_at: Optional[str] = None
    
    # 账户状态
    status: str = "active"              # active, expired, disabled
    balance: float = 0.0
    daily_budget_limit: float = 0.0
    
    # 统计
    total_spend_7d: float = 0.0
    total_spend_30d: float = 0.0
    
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['platform'] = self.platform.value
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AdAccount':
        data['platform'] = AdPlatform(data['platform'])
        return cls(**data)


# ── Row → dataclass helpers ──────────────────────────────────────────
# Column order must match CREATE TABLE statements in _ensure_tables.

_ACCOUNT_COLUMNS = (
    'id', 'platform', 'account_name', 'account_id', 'access_token',
    'refresh_token', 'token_expires_at', 'status', 'balance',
    'daily_budget_limit', 'total_spend_7d', 'total_spend_30d',
    'created_at', 'updated_at',
)

_CAMPAIGN_COLUMNS = (
    'id', 'name', 'platform', 'account_id', 'status', 'objective',
    'conversion_goal', 'budget_type', 'budget_amount', 'start_date',
    'end_date', 'adsets_data', 'total_impressions', 'total_clicks',
    'total_conversions', 'total_spend', 'created_at', 'updated_at',
)


def _row_to_account(row: Dict[str, Any]) -> AdAccount:
    """Convert a DB row dict to an AdAccount, decrypting tokens."""
    return AdAccount(
        id=row['id'],
        platform=AdPlatform(row['platform']),
        account_name=row['account_name'],
        account_id=row['account_id'],
        access_token=decrypt_data(row['access_token']),
        refresh_token=decrypt_data(row['refresh_token']) if row.get('refresh_token') else None,
        token_expires_at=row.get('token_expires_at'),
        status=row.get('status', 'active'),
        balance=row.get('balance', 0.0),
        daily_budget_limit=row.get('daily_budget_limit', 0.0),
        total_spend_7d=row.get('total_spend_7d', 0.0),
        total_spend_30d=row.get('total_spend_30d', 0.0),
        created_at=row.get('created_at'),
        updated_at=row.get('updated_at'),
    )


def _row_to_campaign(row: Dict[str, Any]) -> AdCampaign:
    """Convert a DB row dict to an AdCampaign."""
    adsets_data = json.loads(row.get('adsets_data', '[]'))
    return AdCampaign(
        id=row['id'],
        name=row['name'],
        platform=AdPlatform(row['platform']),
        account_id=row['account_id'],
        status=CampaignStatus(row['status']),
        objective=row['objective'],
        conversion_goal=row.get('conversion_goal'),
        budget_type=BudgetType(row['budget_type']),
        budget_amount=row['budget_amount'],
        start_date=row['start_date'],
        end_date=row.get('end_date'),
        adsets=[AdSet.from_dict(a) for a in adsets_data],
        total_impressions=row.get('total_impressions', 0),
        total_clicks=row.get('total_clicks', 0),
        total_conversions=row.get('total_conversions', 0),
        total_spend=row.get('total_spend', 0.0),
        created_at=row.get('created_at'),
        updated_at=row.get('updated_at'),
    )


class AdManager:
    """广告账户管理器 — uses DatabaseManager for all DB operations"""

    # Tables managed by core/schema.py — do not add CREATE TABLE here

    def __init__(self, db: Optional[DatabaseManager] = None, db_path: Optional[str] = None):
        self._db = db  # None → lazy singleton via property
        self._db_path_override = db_path  # legacy compat
        self._logger = logger.getChild("ad_manager")

    # ── Lazy DatabaseManager access ─────────────────────────────────

    @property
    def db(self) -> DatabaseManager:
        """Return the DatabaseManager singleton (lazy-init)."""
        if self._db is None:
            self._db = DatabaseManager()
        return self._db

    @db.setter
    def db(self, value: DatabaseManager) -> None:
        self._db = value

    # ── Legacy compat ────────────────────────────────────────────────

    def close(self) -> None:
        """Legacy compat — no-op with DatabaseManager."""
        pass

    # ── Table creation ──────────────────────────────────────────────



    # ==================== 账户管理 ====================

    def add_account(self, account: AdAccount) -> bool:
        """添加广告账户"""
        try:
            encrypted_token = encrypt_data(account.access_token)
            encrypted_refresh = encrypt_data(account.refresh_token) if account.refresh_token else None
            now = datetime.now().isoformat()
            self.db.insert('ad_accounts', {
                'id': account.id,
                'platform': account.platform.value,
                'account_name': account.account_name,
                'account_id': account.account_id,
                'access_token': encrypted_token,
                'refresh_token': encrypted_refresh,
                'token_expires_at': account.token_expires_at,
                'status': account.status,
                'balance': account.balance,
                'daily_budget_limit': account.daily_budget_limit,
                'created_at': now,
                'updated_at': now,
            })
            self._logger.info(f"广告账户添加成功: {account.account_name}")
            return True
        except Exception as e:
            self._logger.error(f"添加广告账户失败: {e}")
            return False

    def get_account(self, account_id: str) -> Optional[AdAccount]:
        """获取广告账户"""
        try:
            row = self.db.fetch_one(
                "SELECT * FROM ad_accounts WHERE id = ?", (account_id,)
            )
            if row:
                return _row_to_account(row)
        except Exception as e:
            self._logger.error(f"获取广告账户失败: {e}")
        return None

    def get_all_accounts(self, platform: Optional[AdPlatform] = None) -> List[AdAccount]:
        """获取所有广告账户"""
        try:
            if platform:
                rows = self.db.fetchall(
                    "SELECT * FROM ad_accounts WHERE platform = ?",
                    (platform.value,)
                )
            else:
                rows = self.db.fetchall("SELECT * FROM ad_accounts")
            return [_row_to_account(r) for r in rows]
        except Exception as e:
            self._logger.error(f"获取广告账户列表失败: {e}")
        return []

    def update_account_balance(self, account_id: str, balance: float) -> bool:
        """更新账户余额"""
        try:
            self.db.update('ad_accounts',
                           {'balance': balance, 'updated_at': datetime.now().isoformat()},
                           {'id': account_id})
            return True
        except Exception as e:
            self._logger.error(f"更新账户余额失败: {e}")
            return False

    def delete_account(self, account_id: str) -> bool:
        """删除广告账户"""
        try:
            self.db.delete('ad_accounts', {'id': account_id})
            self._logger.info(f"广告账户已删除: {account_id}")
            return True
        except Exception as e:
            self._logger.error(f"删除广告账户失败: {e}")
            return False

    # ==================== 广告计划管理 ====================

    def create_campaign(self, campaign: AdCampaign) -> bool:
        """创建广告计划"""
        try:
            now = datetime.now().isoformat()
            adsets_json = json.dumps([a.to_dict() for a in campaign.adsets])
            self.db.insert('ad_campaigns', {
                'id': campaign.id,
                'name': campaign.name,
                'platform': campaign.platform.value,
                'account_id': campaign.account_id,
                'status': campaign.status.value,
                'objective': campaign.objective,
                'conversion_goal': campaign.conversion_goal,
                'budget_type': campaign.budget_type.value,
                'budget_amount': campaign.budget_amount,
                'start_date': campaign.start_date,
                'end_date': campaign.end_date,
                'adsets_data': adsets_json,
                'total_impressions': campaign.total_impressions,
                'total_clicks': campaign.total_clicks,
                'total_conversions': campaign.total_conversions,
                'total_spend': campaign.total_spend,
                'created_at': now,
                'updated_at': now,
            })
            self._logger.info(f"广告计划创建成功: {campaign.name}")
            return True
        except Exception as e:
            self._logger.error(f"创建广告计划失败: {e}")
            return False

    def get_campaign(self, campaign_id: str) -> Optional[AdCampaign]:
        """获取广告计划"""
        try:
            row = self.db.fetch_one(
                "SELECT * FROM ad_campaigns WHERE id = ?", (campaign_id,)
            )
            if row:
                return _row_to_campaign(row)
        except Exception as e:
            self._logger.error(f"获取广告计划失败: {e}")
        return None

    def get_campaigns(self, account_id: Optional[str] = None,
                      status: Optional[CampaignStatus] = None) -> List[AdCampaign]:
        """获取广告计划列表"""
        try:
            conditions = []
            params: list = []
            if account_id:
                conditions.append(("account_id", "=", account_id))
                params.append(account_id)
            if status:
                conditions.append(("status", "=", status.value))
                params.append(status.value)

            if conditions:
                where_parts = " AND ".join(f"{col} = ?" for col, _, _ in conditions)
                query = f"SELECT * FROM ad_campaigns WHERE {where_parts}"  # nosec B608  # parameterized
                rows = self.db.fetchall(query, tuple(params))
            else:
                rows = self.db.fetchall("SELECT * FROM ad_campaigns")

            return [_row_to_campaign(r) for r in rows]
        except Exception as e:
            self._logger.error(f"获取广告计划列表失败: {e}")
        return []

    def update_campaign_status(self, campaign_id: str, status: CampaignStatus) -> bool:
        """更新广告计划状态"""
        try:
            self.db.update('ad_campaigns',
                           {'status': status.value, 'updated_at': datetime.now().isoformat()},
                           {'id': campaign_id})
            return True
        except Exception as e:
            self._logger.error(f"更新广告计划状态失败: {e}")
            return False

    def delete_campaign(self, campaign_id: str) -> bool:
        """删除广告计划"""
        try:
            self.db.delete('ad_campaigns', {'id': campaign_id})
            return True
        except Exception as e:
            self._logger.error(f"删除广告计划失败: {e}")
            return False

    # ==================== 数据统计 ====================

    def record_daily_stats(self, campaign_id: str, adset_id: str, date: str,
                           impressions: int, clicks: int, conversions: int,
                           spend: float) -> bool:
        """记录每日投放数据"""
        try:
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            cpc = (spend / clicks) if clicks > 0 else 0
            cpm = (spend / impressions * 1000) if impressions > 0 else 0
            conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
            cost_per_conversion = (spend / conversions) if conversions > 0 else 0

            # Use parameterized query to avoid SQL injection from f-string
            self.db.execute("""
                INSERT OR REPLACE INTO ad_records
                (campaign_id, adset_id, date, impressions, clicks, conversions, spend,
                 ctr, cpc, cpm, conversion_rate, cost_per_conversion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (campaign_id, adset_id, date, impressions, clicks, conversions, spend,
                  ctr, cpc, cpm, conversion_rate, cost_per_conversion))
            return True
        except Exception as e:
            self._logger.error(f"记录投放数据失败: {e}")
            return False

    def get_campaign_stats(self, campaign_id: str, days: int = 30) -> Dict[str, Any]:
        """获取广告计划统计"""
        empty_stats = {
            'impressions': 0, 'clicks': 0, 'conversions': 0, 'spend': 0.0,
            'ctr': 0.0, 'cpc': 0.0, 'cpm': 0.0,
            'conversion_rate': 0.0, 'cost_per_conversion': 0.0,
        }
        try:
            # Parameterized: days is an int, but SQLite date() needs literal.
            # Validate days is a positive integer to prevent injection.
            if not isinstance(days, int) or days < 0:
                raise ValueError(f"Invalid days parameter: {days}")
            # Use date('now', '-N days') with safe integer interpolation
            # nosec B608  # parameterized
            row = self.db.fetch_one(f"""
                SELECT
                    SUM(impressions), SUM(clicks), SUM(conversions), SUM(spend),
                    AVG(ctr), AVG(cpc), AVG(cpm), AVG(conversion_rate), AVG(cost_per_conversion)
                FROM ad_records
                WHERE campaign_id = ? AND date >= date('now', '-{days} days')
            """, (campaign_id,))
            if row and row.get('SUM(impressions)'):
                return {
                    'impressions': row.get('SUM(impressions)', 0) or 0,
                    'clicks': row.get('SUM(clicks)', 0) or 0,
                    'conversions': row.get('SUM(conversions)', 0) or 0,
                    'spend': row.get('SUM(spend)', 0.0) or 0.0,
                    'ctr': row.get('AVG(ctr)', 0.0) or 0.0,
                    'cpc': row.get('AVG(cpc)', 0.0) or 0.0,
                    'cpm': row.get('AVG(cpm)', 0.0) or 0.0,
                    'conversion_rate': row.get('AVG(conversion_rate)', 0.0) or 0.0,
                    'cost_per_conversion': row.get('AVG(cost_per_conversion)', 0.0) or 0.0,
                }
        except Exception as e:
            self._logger.error(f"获取广告统计失败: {e}")
        return empty_stats

    def get_platform_comparison(self, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """获取各平台投放对比"""
        comparison: Dict[str, Dict[str, Any]] = {}
        try:
            if not isinstance(days, int) or days < 0:
                raise ValueError(f"Invalid days parameter: {days}")
            # nosec B608  # parameterized
            rows = self.db.fetchall(f"""
                SELECT c.platform,
                       SUM(r.impressions), SUM(r.clicks), SUM(r.conversions), SUM(r.spend),
                       AVG(r.ctr), AVG(r.cpc)
                FROM ad_campaigns c
                JOIN ad_records r ON c.id = r.campaign_id
                WHERE r.date >= date('now', '-{days} days')
                GROUP BY c.platform
            """)
            for row in rows:
                platform = row.get('platform', '')
                comparison[platform] = {
                    'impressions': row.get('SUM(impressions)', 0) or 0,
                    'clicks': row.get('SUM(clicks)', 0) or 0,
                    'conversions': row.get('SUM(conversions)', 0) or 0,
                    'spend': row.get('SUM(spend)', 0.0) or 0.0,
                    'ctr': row.get('AVG(ctr)', 0.0) or 0.0,
                    'cpc': row.get('AVG(cpc)', 0.0) or 0.0,
                }
        except Exception as e:
            self._logger.error(f"获取平台对比失败: {e}")
        return comparison

    # ==================== 异步方法 (委托给 DatabaseManager async) ====================

    async def add_account_async(self, account: AdAccount) -> bool:
        """添加广告账户 (异步)"""
        try:
            encrypted_token = encrypt_data(account.access_token)
            encrypted_refresh = encrypt_data(account.refresh_token) if account.refresh_token else None
            now = datetime.now().isoformat()
            await self.db.insert_async('ad_accounts', {
                'id': account.id,
                'platform': account.platform.value,
                'account_name': account.account_name,
                'account_id': account.account_id,
                'access_token': encrypted_token,
                'refresh_token': encrypted_refresh,
                'token_expires_at': account.token_expires_at,
                'status': account.status,
                'balance': account.balance,
                'daily_budget_limit': account.daily_budget_limit,
                'created_at': now,
                'updated_at': now,
            })
            self._logger.info(f"广告账户添加成功(异步): {account.account_name}")
            return True
        except Exception as e:
            self._logger.error(f"添加广告账户失败(异步): {e}")
            return False

    async def get_account_async(self, account_id: str) -> Optional[AdAccount]:
        """获取广告账户 (异步)"""
        try:
            row = await self.db.execute_one_async(
                "SELECT * FROM ad_accounts WHERE id = ?", (account_id,)
            )
            if row:
                return _row_to_account(row)
        except Exception as e:
            self._logger.error(f"获取广告账户失败(异步): {e}")
        return None

    async def get_all_accounts_async(self, platform: Optional[AdPlatform] = None) -> List[AdAccount]:
        """获取所有广告账户 (异步)"""
        try:
            if platform:
                rows = await self.db.execute_async(
                    "SELECT * FROM ad_accounts WHERE platform = ?",
                    (platform.value,)
                )
            else:
                rows = await self.db.fetchall_async("SELECT * FROM ad_accounts")
            return [_row_to_account(r) for r in rows]
        except Exception as e:
            self._logger.error(f"获取广告账户列表失败(异步): {e}")
        return []

    async def update_account_balance_async(self, account_id: str, balance: float) -> bool:
        """更新账户余额 (异步)"""
        try:
            await self.db.update_async('ad_accounts',
                                       {'balance': balance, 'updated_at': datetime.now().isoformat()},
                                       {'id': account_id})
            return True
        except Exception as e:
            self._logger.error(f"更新账户余额失败(异步): {e}")
            return False

    async def delete_account_async(self, account_id: str) -> bool:
        """删除广告账户 (异步)"""
        try:
            await self.db.delete_async('ad_accounts', {'id': account_id})
            self._logger.info(f"广告账户已删除(异步): {account_id}")
            return True
        except Exception as e:
            self._logger.error(f"删除广告账户失败(异步): {e}")
            return False

    async def create_campaign_async(self, campaign: AdCampaign) -> bool:
        """创建广告计划 (异步)"""
        try:
            now = datetime.now().isoformat()
            adsets_json = json.dumps([a.to_dict() for a in campaign.adsets])
            await self.db.insert_async('ad_campaigns', {
                'id': campaign.id,
                'name': campaign.name,
                'platform': campaign.platform.value,
                'account_id': campaign.account_id,
                'status': campaign.status.value,
                'objective': campaign.objective,
                'conversion_goal': campaign.conversion_goal,
                'budget_type': campaign.budget_type.value,
                'budget_amount': campaign.budget_amount,
                'start_date': campaign.start_date,
                'end_date': campaign.end_date,
                'adsets_data': adsets_json,
                'total_impressions': campaign.total_impressions,
                'total_clicks': campaign.total_clicks,
                'total_conversions': campaign.total_conversions,
                'total_spend': campaign.total_spend,
                'created_at': now,
                'updated_at': now,
            })
            self._logger.info(f"广告计划创建成功(异步): {campaign.name}")
            return True
        except Exception as e:
            self._logger.error(f"创建广告计划失败(异步): {e}")
            return False

    async def get_campaign_async(self, campaign_id: str) -> Optional[AdCampaign]:
        """获取广告计划 (异步)"""
        try:
            row = await self.db.execute_one_async(
                "SELECT * FROM ad_campaigns WHERE id = ?", (campaign_id,)
            )
            if row:
                return _row_to_campaign(row)
        except Exception as e:
            self._logger.error(f"获取广告计划失败(异步): {e}")
        return None

    async def get_campaigns_async(self, account_id: Optional[str] = None,
                                  status: Optional[CampaignStatus] = None) -> List[AdCampaign]:
        """获取广告计划列表 (异步)"""
        try:
            conditions = []
            params: list = []
            if account_id:
                conditions.append(("account_id", "=", account_id))
                params.append(account_id)
            if status:
                conditions.append(("status", "=", status.value))
                params.append(status.value)

            if conditions:
                where_parts = " AND ".join(f"{col} = ?" for col, _, _ in conditions)
                query = f"SELECT * FROM ad_campaigns WHERE {where_parts}"  # nosec B608  # parameterized
                rows = await self.db.execute_async(query, tuple(params))
            else:
                rows = await self.db.fetchall_async("SELECT * FROM ad_campaigns")

            return [_row_to_campaign(r) for r in rows]
        except Exception as e:
            self._logger.error(f"获取广告计划列表失败(异步): {e}")
        return []

    async def update_campaign_status_async(self, campaign_id: str, status: CampaignStatus) -> bool:
        """更新广告计划状态 (异步)"""
        try:
            await self.db.update_async('ad_campaigns',
                                       {'status': status.value, 'updated_at': datetime.now().isoformat()},
                                       {'id': campaign_id})
            return True
        except Exception as e:
            self._logger.error(f"更新广告计划状态失败(异步): {e}")
            return False

    async def delete_campaign_async(self, campaign_id: str) -> bool:
        """删除广告计划 (异步)"""
        try:
            await self.db.delete_async('ad_campaigns', {'id': campaign_id})
            return True
        except Exception as e:
            self._logger.error(f"删除广告计划失败(异步): {e}")
            return False

    async def record_daily_stats_async(self, campaign_id: str, adset_id: str,
                                       date: str, impressions: int, clicks: int,
                                       conversions: int, spend: float) -> bool:
        """记录每日投放数据 (异步)"""
        try:
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            cpc = (spend / clicks) if clicks > 0 else 0
            cpm = (spend / impressions * 1000) if impressions > 0 else 0
            conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
            cost_per_conversion = (spend / conversions) if conversions > 0 else 0

            await self.db.execute_async("""
                INSERT OR REPLACE INTO ad_records
                (campaign_id, adset_id, date, impressions, clicks, conversions, spend,
                 ctr, cpc, cpm, conversion_rate, cost_per_conversion)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (campaign_id, adset_id, date, impressions, clicks, conversions, spend,
                  ctr, cpc, cpm, conversion_rate, cost_per_conversion))
            return True
        except Exception as e:
            self._logger.error(f"记录投放数据失败(异步): {e}")
            return False

    async def get_campaign_stats_async(self, campaign_id: str, days: int = 30) -> Dict[str, Any]:
        """获取广告计划统计 (异步)"""
        empty_stats = {
            'impressions': 0, 'clicks': 0, 'conversions': 0, 'spend': 0.0,
            'ctr': 0.0, 'cpc': 0.0, 'cpm': 0.0,
            'conversion_rate': 0.0, 'cost_per_conversion': 0.0,
        }
        try:
            if not isinstance(days, int) or days < 0:
                raise ValueError(f"Invalid days parameter: {days}")
            # nosec B608  # parameterized
            row = await self.db.execute_one_async(f"""
                SELECT
                    SUM(impressions), SUM(clicks), SUM(conversions), SUM(spend),
                    AVG(ctr), AVG(cpc), AVG(cpm), AVG(conversion_rate), AVG(cost_per_conversion)
                FROM ad_records
                WHERE campaign_id = ? AND date >= date('now', '-{days} days')
            """, (campaign_id,))
            if row and row.get('SUM(impressions)'):
                return {
                    'impressions': row.get('SUM(impressions)', 0) or 0,
                    'clicks': row.get('SUM(clicks)', 0) or 0,
                    'conversions': row.get('SUM(conversions)', 0) or 0,
                    'spend': row.get('SUM(spend)', 0.0) or 0.0,
                    'ctr': row.get('AVG(ctr)', 0.0) or 0.0,
                    'cpc': row.get('AVG(cpc)', 0.0) or 0.0,
                    'cpm': row.get('AVG(cpm)', 0.0) or 0.0,
                    'conversion_rate': row.get('AVG(conversion_rate)', 0.0) or 0.0,
                    'cost_per_conversion': row.get('AVG(cost_per_conversion)', 0.0) or 0.0,
                }
        except Exception as e:
            self._logger.error(f"获取广告统计失败(异步): {e}")
        return empty_stats

    async def get_platform_comparison_async(self, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """获取各平台投放对比 (异步)"""
        comparison: Dict[str, Dict[str, Any]] = {}
        try:
            if not isinstance(days, int) or days < 0:
                raise ValueError(f"Invalid days parameter: {days}")
            # nosec B608  # parameterized
            rows = await self.db.execute_async(f"""
                SELECT c.platform,
                       SUM(r.impressions), SUM(r.clicks), SUM(r.conversions), SUM(r.spend),
                       AVG(r.ctr), AVG(r.cpc)
                FROM ad_campaigns c
                JOIN ad_records r ON c.id = r.campaign_id
                WHERE r.date >= date('now', '-{days} days')
                GROUP BY c.platform
            """)
            for row in rows:
                platform = row.get('platform', '')
                comparison[platform] = {
                    'impressions': row.get('SUM(impressions)', 0) or 0,
                    'clicks': row.get('SUM(clicks)', 0) or 0,
                    'conversions': row.get('SUM(conversions)', 0) or 0,
                    'spend': row.get('SUM(spend)', 0.0) or 0.0,
                    'ctr': row.get('AVG(ctr)', 0.0) or 0.0,
                    'cpc': row.get('AVG(cpc)', 0.0) or 0.0,
                }
        except Exception as e:
            self._logger.error(f"获取平台对比失败(异步): {e}")
        return comparison

