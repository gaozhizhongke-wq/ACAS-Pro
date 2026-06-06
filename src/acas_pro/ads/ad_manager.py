"""
广告账户管理模块
支持多平台广告账户统一管理
"""

import json
try:
    import aiosqlite
    _HAS_AIOSQLITE = True
except ImportError:
    _HAS_AIOSQLITE = False
import sqlite3
from datetime import datetime, timedelta
import asyncio
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from pathlib import Path

from ..core.config import config
from ..core.logging import logger
from ..core.security import encrypt_data, decrypt_data


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
    adsets: List[AdSet] = None
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


class AdManager:
    """广告账户管理器"""
    
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or config.database.path
        self._conn = None  # explicit single connection to avoid ResourceWarning
        self._init_database()
        self.logger = logger.getChild("ad_manager")

    def close(self):
        """Close the managed database connection."""
        if self._conn is not None:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    def __del__(self):
        self.close()

    def _init_database(self):
        """初始化数据库表"""
        self._conn = sqlite3.connect(self.db_path)
        conn = self._conn
        # 广告账户表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ad_accounts (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                account_name TEXT NOT NULL,
                account_id TEXT NOT NULL,
                access_token TEXT NOT NULL,
                refresh_token TEXT,
                token_expires_at TEXT,
                status TEXT DEFAULT 'active',
                balance REAL DEFAULT 0.0,
                daily_budget_limit REAL DEFAULT 0.0,
                total_spend_7d REAL DEFAULT 0.0,
                total_spend_30d REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 广告计划表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ad_campaigns (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                platform TEXT NOT NULL,
                account_id TEXT NOT NULL,
                status TEXT NOT NULL,
                objective TEXT NOT NULL,
                conversion_goal TEXT,
                budget_type TEXT NOT NULL,
                budget_amount REAL NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT,
                adsets_data TEXT NOT NULL,
                total_impressions INTEGER DEFAULT 0,
                total_clicks INTEGER DEFAULT 0,
                total_conversions INTEGER DEFAULT 0,
                total_spend REAL DEFAULT 0.0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # 投放记录表
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ad_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                campaign_id TEXT NOT NULL,
                adset_id TEXT NOT NULL,
                date TEXT NOT NULL,
                impressions INTEGER DEFAULT 0,
                clicks INTEGER DEFAULT 0,
                conversions INTEGER DEFAULT 0,
                spend REAL DEFAULT 0.0,
                ctr REAL DEFAULT 0.0,
                cpc REAL DEFAULT 0.0,
                cpm REAL DEFAULT 0.0,
                conversion_rate REAL DEFAULT 0.0,
                cost_per_conversion REAL DEFAULT 0.0,
                UNIQUE(campaign_id, adset_id, date)
            )
        """)

        conn.commit()
        conn.close()  # close init connection to avoid ResourceWarning on Python 3.14
        self._conn = None  # mark as closed; will reconnect in next operation

    # ==================== 账户管理 ====================
    
    def add_account(self, account: AdAccount) -> bool:
        """添加广告账户"""
        try:
            # 加密敏感信息
            encrypted_token = encrypt_data(account.access_token)
            encrypted_refresh = encrypt_data(account.refresh_token) if account.refresh_token else None
            
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()
                conn.execute("""
                    INSERT INTO ad_accounts 
                    (id, platform, account_name, account_id, access_token, refresh_token,
                     token_expires_at, status, balance, daily_budget_limit, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    account.id, account.platform.value, account.account_name, account.account_id,
                    encrypted_token, encrypted_refresh, account.token_expires_at,
                    account.status, account.balance, account.daily_budget_limit, now, now
                ))
                conn.commit()
            
            self.logger.info(f"广告账户添加成功: {account.account_name}")
            return True
        except Exception as e:
            self.logger.error(f"添加广告账户失败: {e}")
            return False
    
    def get_account(self, account_id: str) -> Optional[AdAccount]:
        """获取广告账户"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM ad_accounts WHERE id = ?",
                    (account_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    # 解密敏感信息
                    access_token = decrypt_data(row[4])
                    refresh_token = decrypt_data(row[5]) if row[5] else None
                    
                    return AdAccount(
                        id=row[0],
                        platform=AdPlatform(row[1]),
                        account_name=row[2],
                        account_id=row[3],
                        access_token=access_token,
                        refresh_token=refresh_token,
                        token_expires_at=row[6],
                        status=row[7],
                        balance=row[8],
                        daily_budget_limit=row[9],
                        total_spend_7d=row[10],
                        total_spend_30d=row[11],
                        created_at=row[12],
                        updated_at=row[13]
                    )
        except Exception as e:
            self.logger.error(f"获取广告账户失败: {e}")
        
        return None
    
    def get_all_accounts(self, platform: Optional[AdPlatform] = None) -> List[AdAccount]:
        """获取所有广告账户"""
        accounts = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                if platform:
                    cursor = conn.execute(
                        "SELECT * FROM ad_accounts WHERE platform = ?",
                        (platform.value,)
                    )
                else:
                    cursor = conn.execute("SELECT * FROM ad_accounts")
                
                for row in cursor.fetchall():
                    access_token = decrypt_data(row[4])
                    refresh_token = decrypt_data(row[5]) if row[5] else None
                    
                    accounts.append(AdAccount(
                        id=row[0],
                        platform=AdPlatform(row[1]),
                        account_name=row[2],
                        account_id=row[3],
                        access_token=access_token,
                        refresh_token=refresh_token,
                        token_expires_at=row[6],
                        status=row[7],
                        balance=row[8],
                        daily_budget_limit=row[9],
                        total_spend_7d=row[10],
                        total_spend_30d=row[11],
                        created_at=row[12],
                        updated_at=row[13]
                    ))
        except Exception as e:
            self.logger.error(f"获取广告账户列表失败: {e}")
        
        return accounts
    
    def update_account_balance(self, account_id: str, balance: float) -> bool:
        """更新账户余额"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE ad_accounts SET balance = ?, updated_at = ? WHERE id = ?",
                    (balance, datetime.now().isoformat(), account_id)
                )
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"更新账户余额失败: {e}")
            return False
    
    def delete_account(self, account_id: str) -> bool:
        """删除广告账户"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM ad_accounts WHERE id = ?", (account_id,))
                conn.commit()
            self.logger.info(f"广告账户已删除: {account_id}")
            return True
        except Exception as e:
            self.logger.error(f"删除广告账户失败: {e}")
            return False
    
    # ==================== 广告计划管理 ====================
    
    def create_campaign(self, campaign: AdCampaign) -> bool:
        """创建广告计划"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now().isoformat()
                adsets_json = json.dumps([a.to_dict() for a in campaign.adsets])
                
                conn.execute("""
                    INSERT INTO ad_campaigns
                    (id, name, platform, account_id, status, objective, conversion_goal,
                     budget_type, budget_amount, start_date, end_date, adsets_data,
                     total_impressions, total_clicks, total_conversions, total_spend,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    campaign.id, campaign.name, campaign.platform.value, campaign.account_id,
                    campaign.status.value, campaign.objective, campaign.conversion_goal,
                    campaign.budget_type.value, campaign.budget_amount,
                    campaign.start_date, campaign.end_date, adsets_json,
                    campaign.total_impressions, campaign.total_clicks,
                    campaign.total_conversions, campaign.total_spend, now, now
                ))
                conn.commit()
            
            self.logger.info(f"广告计划创建成功: {campaign.name}")
            return True
        except Exception as e:
            self.logger.error(f"创建广告计划失败: {e}")
            return False
    
    def get_campaign(self, campaign_id: str) -> Optional[AdCampaign]:
        """获取广告计划"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM ad_campaigns WHERE id = ?",
                    (campaign_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    adsets_data = json.loads(row[11])
                    return AdCampaign(
                        id=row[0],
                        name=row[1],
                        platform=AdPlatform(row[2]),
                        account_id=row[3],
                        status=CampaignStatus(row[4]),
                        objective=row[5],
                        conversion_goal=row[6],
                        budget_type=BudgetType(row[7]),
                        budget_amount=row[8],
                        start_date=row[9],
                        end_date=row[10],
                        adsets=[AdSet.from_dict(a) for a in adsets_data],
                        total_impressions=row[12],
                        total_clicks=row[13],
                        total_conversions=row[14],
                        total_spend=row[15],
                        created_at=row[16],
                        updated_at=row[17]
                    )
        except Exception as e:
            self.logger.error(f"获取广告计划失败: {e}")
        
        return None
    
    def get_campaigns(self, account_id: Optional[str] = None,
                     status: Optional[CampaignStatus] = None) -> List[AdCampaign]:
        """获取广告计划列表"""
        campaigns = []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                query = "SELECT * FROM ad_campaigns WHERE 1=1"
                params = []
                
                if account_id:
                    query += " AND account_id = ?"
                    params.append(account_id)
                if status:
                    query += " AND status = ?"
                    params.append(status.value)
                
                cursor = conn.execute(query, params)
                
                for row in cursor.fetchall():
                    adsets_data = json.loads(row[11])
                    campaigns.append(AdCampaign(
                        id=row[0],
                        name=row[1],
                        platform=AdPlatform(row[2]),
                        account_id=row[3],
                        status=CampaignStatus(row[4]),
                        objective=row[5],
                        conversion_goal=row[6],
                        budget_type=BudgetType(row[7]),
                        budget_amount=row[8],
                        start_date=row[9],
                        end_date=row[10],
                        adsets=[AdSet.from_dict(a) for a in adsets_data],
                        total_impressions=row[12],
                        total_clicks=row[13],
                        total_conversions=row[14],
                        total_spend=row[15],
                        created_at=row[16],
                        updated_at=row[17]
                    ))
        except Exception as e:
            self.logger.error(f"获取广告计划列表失败: {e}")
        
        return campaigns
    
    def update_campaign_status(self, campaign_id: str, status: CampaignStatus) -> bool:
        """更新广告计划状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """UPDATE ad_campaigns 
                       SET status = ?, updated_at = ? 
                       WHERE id = ?""",
                    (status.value, datetime.now().isoformat(), campaign_id)
                )
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"更新广告计划状态失败: {e}")
            return False
    
    def delete_campaign(self, campaign_id: str) -> bool:
        """删除广告计划"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM ad_campaigns WHERE id = ?", (campaign_id,))
                conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"删除广告计划失败: {e}")
            return False
    
    # ==================== 数据统计 ====================
    
    def record_daily_stats(self, campaign_id: str, adset_id: str, date: str,
                          impressions: int, clicks: int, conversions: int,
                          spend: float) -> bool:
        """记录每日投放数据"""
        try:
            # 计算衍生指标
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            cpc = (spend / clicks) if clicks > 0 else 0
            cpm = (spend / impressions * 1000) if impressions > 0 else 0
            conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
            cost_per_conversion = (spend / conversions) if conversions > 0 else 0
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO ad_records
                    (campaign_id, adset_id, date, impressions, clicks, conversions, spend,
                     ctr, cpc, cpm, conversion_rate, cost_per_conversion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (campaign_id, adset_id, date, impressions, clicks, conversions, spend,
                      ctr, cpc, cpm, conversion_rate, cost_per_conversion))
                conn.commit()
            
            return True
        except Exception as e:
            self.logger.error(f"记录投放数据失败: {e}")
            return False
    
    def get_campaign_stats(self, campaign_id: str, days: int = 30) -> Dict[str, Any]:
        """获取广告计划统计"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT 
                        SUM(impressions), SUM(clicks), SUM(conversions), SUM(spend),
                        AVG(ctr), AVG(cpc), AVG(cpm), AVG(conversion_rate), AVG(cost_per_conversion)
                    FROM ad_records
                    WHERE campaign_id = ? AND date >= date('now', '-{} days')
                """.format(days), (campaign_id,))
                
                row = cursor.fetchone()
                if row and row[0]:
                    return {
                        'impressions': row[0] or 0,
                        'clicks': row[1] or 0,
                        'conversions': row[2] or 0,
                        'spend': row[3] or 0.0,
                        'ctr': row[4] or 0.0,
                        'cpc': row[5] or 0.0,
                        'cpm': row[6] or 0.0,
                        'conversion_rate': row[7] or 0.0,
                        'cost_per_conversion': row[8] or 0.0
                    }
        except Exception as e:
            self.logger.error(f"获取广告统计失败: {e}")
        
        return {
            'impressions': 0, 'clicks': 0, 'conversions': 0, 'spend': 0.0,
            'ctr': 0.0, 'cpc': 0.0, 'cpm': 0.0,
            'conversion_rate': 0.0, 'cost_per_conversion': 0.0
        }
    
    def get_platform_comparison(self, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """获取各平台投放对比"""
        comparison = {}
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT c.platform,
                           SUM(r.impressions), SUM(r.clicks), SUM(r.conversions), SUM(r.spend),
                           AVG(r.ctr), AVG(r.cpc)
                    FROM ad_campaigns c
                    JOIN ad_records r ON c.id = r.campaign_id
                    WHERE r.date >= date('now', '-{} days')
                    GROUP BY c.platform
                """.format(days))
                
                for row in cursor.fetchall():
                    platform = row[0]
                    comparison[platform] = {
                        'impressions': row[1] or 0,
                        'clicks': row[2] or 0,
                        'conversions': row[3] or 0,
                        'spend': row[4] or 0.0,
                        'ctr': row[5] or 0.0,
                        'cpc': row[6] or 0.0
                    }
        except Exception as e:
            self.logger.error(f"获取平台对比失败: {e}")
        
        return comparison
    
    # ==================== 异步方法 (使用 aiosqlite 真正异步化) ====================
    
    async def add_account_async(self, account: AdAccount) -> bool:
        """添加广告账户 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        try:
            encrypted_token = encrypt_data(account.access_token)
            encrypted_refresh = encrypt_data(account.refresh_token) if account.refresh_token else None
            now = datetime.now().isoformat()
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    INSERT INTO ad_accounts 
                    (id, platform, account_name, account_id, access_token, refresh_token,
                     token_expires_at, status, balance, daily_budget_limit, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    account.id, account.platform.value, account.account_name, account.account_id,
                    encrypted_token, encrypted_refresh, account.token_expires_at,
                    account.status, account.balance, account.daily_budget_limit, now, now
                ))
                await conn.commit()
            self.logger.info(f"广告账户添加成功(异步): {account.account_name}")
            return True
        except Exception as e:
            self.logger.error(f"添加广告账户失败(异步): {e}")
            return False
    
    async def get_account_async(self, account_id: str) -> Optional[AdAccount]:
        """获取广告账户 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    "SELECT * FROM ad_accounts WHERE id = ?",
                    (account_id,)
                )
                row = await cursor.fetchone()
                if row:
                    access_token = decrypt_data(row[4])
                    refresh_token = decrypt_data(row[5]) if row[5] else None
                    return AdAccount(
                        id=row[0],
                        platform=AdPlatform(row[1]),
                        account_name=row[2],
                        account_id=row[3],
                        access_token=access_token,
                        refresh_token=refresh_token,
                        token_expires_at=row[6],
                        status=row[7],
                        balance=row[8],
                        daily_budget_limit=row[9],
                        total_spend_7d=row[10],
                        total_spend_30d=row[11],
                        created_at=row[12],
                        updated_at=row[13]
                    )
        except Exception as e:
            self.logger.error(f"获取广告账户失败(异步): {e}")
        return None
    
    async def get_all_accounts_async(self, platform: Optional[AdPlatform] = None) -> List[AdAccount]:
        """获取所有广告账户 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        accounts = []
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                if platform:
                    cursor = await conn.execute(
                        "SELECT * FROM ad_accounts WHERE platform = ?",
                        (platform.value,)
                    )
                else:
                    cursor = await conn.execute("SELECT * FROM ad_accounts")
                rows = await cursor.fetchall()
                for row in rows:
                    access_token = decrypt_data(row[4])
                    refresh_token = decrypt_data(row[5]) if row[5] else None
                    accounts.append(AdAccount(
                        id=row[0],
                        platform=AdPlatform(row[1]),
                        account_name=row[2],
                        account_id=row[3],
                        access_token=access_token,
                        refresh_token=refresh_token,
                        token_expires_at=row[6],
                        status=row[7],
                        balance=row[8],
                        daily_budget_limit=row[9],
                        total_spend_7d=row[10],
                        total_spend_30d=row[11],
                        created_at=row[12],
                        updated_at=row[13]
                    ))
        except Exception as e:
            self.logger.error(f"获取广告账户列表失败(异步): {e}")
        return accounts
    
    async def update_account_balance_async(self, account_id: str, balance: float) -> bool:
        """更新账户余额 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    "UPDATE ad_accounts SET balance = ?, updated_at = ? WHERE id = ?",
                    (balance, datetime.now().isoformat(), account_id)
                )
                await conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"更新账户余额失败(异步): {e}")
            return False
    
    async def delete_account_async(self, account_id: str) -> bool:
        """删除广告账户 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("DELETE FROM ad_accounts WHERE id = ?", (account_id,))
                await conn.commit()
            self.logger.info(f"广告账户已删除(异步): {account_id}")
            return True
        except Exception as e:
            self.logger.error(f"删除广告账户失败(异步): {e}")
            return False
    
    async def create_campaign_async(self, campaign: AdCampaign) -> bool:
        """创建广告计划 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        try:
            now = datetime.now().isoformat()
            adsets_json = json.dumps([a.to_dict() for a in campaign.adsets])
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    INSERT INTO ad_campaigns
                    (id, name, platform, account_id, status, objective, conversion_goal,
                     budget_type, budget_amount, start_date, end_date, adsets_data,
                     total_impressions, total_clicks, total_conversions, total_spend,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    campaign.id, campaign.name, campaign.platform.value, campaign.account_id,
                    campaign.status.value, campaign.objective, campaign.conversion_goal,
                    campaign.budget_type.value, campaign.budget_amount,
                    campaign.start_date, campaign.end_date, adsets_json,
                    campaign.total_impressions, campaign.total_clicks,
                    campaign.total_conversions, campaign.total_spend, now, now
                ))
                await conn.commit()
            self.logger.info(f"广告计划创建成功(异步): {campaign.name}")
            return True
        except Exception as e:
            self.logger.error(f"创建广告计划失败(异步): {e}")
            return False
    
    async def get_campaign_async(self, campaign_id: str) -> Optional[AdCampaign]:
        """获取广告计划 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(
                    "SELECT * FROM ad_campaigns WHERE id = ?",
                    (campaign_id,)
                )
                row = await cursor.fetchone()
                if row:
                    adsets_data = json.loads(row[11])
                    return AdCampaign(
                        id=row[0],
                        name=row[1],
                        platform=AdPlatform(row[2]),
                        account_id=row[3],
                        status=CampaignStatus(row[4]),
                        objective=row[5],
                        conversion_goal=row[6],
                        budget_type=BudgetType(row[7]),
                        budget_amount=row[8],
                        start_date=row[9],
                        end_date=row[10],
                        adsets=[AdSet.from_dict(a) for a in adsets_data],
                        total_impressions=row[12],
                        total_clicks=row[13],
                        total_conversions=row[14],
                        total_spend=row[15],
                        created_at=row[16],
                        updated_at=row[17]
                    )
        except Exception as e:
            self.logger.error(f"获取广告计划失败(异步): {e}")
        return None
    
    async def get_campaigns_async(self, account_id: Optional[str] = None,
                                  status: Optional[CampaignStatus] = None) -> List[AdCampaign]:
        """获取广告计划列表 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        campaigns = []
        try:
            query = "SELECT * FROM ad_campaigns WHERE 1=1"
            params = []
            if account_id:
                query += " AND account_id = ?"
                params.append(account_id)
            if status:
                query += " AND status = ?"
                params.append(status.value)
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute(query, params)
                rows = await cursor.fetchall()
                for row in rows:
                    adsets_data = json.loads(row[11])
                    campaigns.append(AdCampaign(
                        id=row[0],
                        name=row[1],
                        platform=AdPlatform(row[2]),
                        account_id=row[3],
                        status=CampaignStatus(row[4]),
                        objective=row[5],
                        conversion_goal=row[6],
                        budget_type=BudgetType(row[7]),
                        budget_amount=row[8],
                        start_date=row[9],
                        end_date=row[10],
                        adsets=[AdSet.from_dict(a) for a in adsets_data],
                        total_impressions=row[12],
                        total_clicks=row[13],
                        total_conversions=row[14],
                        total_spend=row[15],
                        created_at=row[16],
                        updated_at=row[17]
                    ))
        except Exception as e:
            self.logger.error(f"获取广告计划列表失败(异步): {e}")
        return campaigns
    
    async def update_campaign_status_async(self, campaign_id: str, status: CampaignStatus) -> bool:
        """更新广告计划状态 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""UPDATE ad_campaigns 
                       SET status = ?, updated_at = ? 
                       WHERE id = ?""",
                    (status.value, datetime.now().isoformat(), campaign_id)
                )
                await conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"更新广告计划状态失败(异步): {e}")
            return False
    
    async def delete_campaign_async(self, campaign_id: str) -> bool:
        """删除广告计划 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("DELETE FROM ad_campaigns WHERE id = ?", (campaign_id,))
                await conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"删除广告计划失败(异步): {e}")
            return False
    
    async def record_daily_stats_async(self, campaign_id: str, adset_id: str,
                                       date: str, impressions: int, clicks: int,
                                       conversions: int, spend: float) -> bool:
        """记录每日投放数据 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        try:
            ctr = (clicks / impressions * 100) if impressions > 0 else 0
            cpc = (spend / clicks) if clicks > 0 else 0
            cpm = (spend / impressions * 1000) if impressions > 0 else 0
            conversion_rate = (conversions / clicks * 100) if clicks > 0 else 0
            cost_per_conversion = (spend / conversions) if conversions > 0 else 0
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    INSERT OR REPLACE INTO ad_records
                    (campaign_id, adset_id, date, impressions, clicks, conversions, spend,
                     ctr, cpc, cpm, conversion_rate, cost_per_conversion)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (campaign_id, adset_id, date, impressions, clicks, conversions, spend,
                      ctr, cpc, cpm, conversion_rate, cost_per_conversion))
                await conn.commit()
            return True
        except Exception as e:
            self.logger.error(f"记录投放数据失败(异步): {e}")
            return False
    
    async def get_campaign_stats_async(self, campaign_id: str, days: int = 30) -> Dict[str, Any]:
        """获取广告计划统计 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute("""
                    SELECT 
                        SUM(impressions), SUM(clicks), SUM(conversions), SUM(spend),
                        AVG(ctr), AVG(cpc), AVG(cpm), AVG(conversion_rate), AVG(cost_per_conversion)
                    FROM ad_records
                    WHERE campaign_id = ? AND date >= date('now', '-{} days')
                """.format(days), (campaign_id,))
                row = await cursor.fetchone()
                if row and row[0]:
                    return {
                        'impressions': row[0] or 0,
                        'clicks': row[1] or 0,
                        'conversions': row[2] or 0,
                        'spend': row[3] or 0.0,
                        'ctr': row[4] or 0.0,
                        'cpc': row[5] or 0.0,
                        'cpm': row[6] or 0.0,
                        'conversion_rate': row[7] or 0.0,
                        'cost_per_conversion': row[8] or 0.0
                    }
        except Exception as e:
            self.logger.error(f"获取广告统计失败(异步): {e}")
        return {
            'impressions': 0, 'clicks': 0, 'conversions': 0, 'spend': 0.0,
            'ctr': 0.0, 'cpc': 0.0, 'cpm': 0.0,
            'conversion_rate': 0.0, 'cost_per_conversion': 0.0
        }
    
    async def get_platform_comparison_async(self, days: int = 30) -> Dict[str, Dict[str, Any]]:
        """获取各平台投放对比 (真正异步)"""
        if not _HAS_AIOSQLITE:
            raise RuntimeError("aiosqlite not installed")
        comparison = {}
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                cursor = await conn.execute("""
                    SELECT c.platform,
                           SUM(r.impressions), SUM(r.clicks), SUM(r.conversions), SUM(r.spend),
                           AVG(r.ctr), AVG(r.cpc)
                    FROM ad_campaigns c
                    JOIN ad_records r ON c.id = r.campaign_id
                    WHERE r.date >= date('now', '-{} days')
                    GROUP BY c.platform
                """.format(days))
                rows = await cursor.fetchall()
                for row in rows:
                    platform = row[0]
                    comparison[platform] = {
                        'impressions': row[1] or 0,
                        'clicks': row[2] or 0,
                        'conversions': row[3] or 0,
                        'spend': row[4] or 0.0,
                        'ctr': row[5] or 0.0,
                        'cpc': row[6] or 0.0
                    }
        except Exception as e:
            self.logger.error(f"获取平台对比失败(异步): {e}")
        return comparison
