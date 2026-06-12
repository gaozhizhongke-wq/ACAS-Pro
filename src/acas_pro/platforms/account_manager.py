#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Account Manager
多平台账号矩阵管理系统
"""

import json
from datetime import datetime, timedelta
from typing import List, Optional
from dataclasses import dataclass
from enum import Enum

from ..core.logging import get_logger
from ..core.database import DatabaseManager
from ..core.security import SessionManager

logger = get_logger(__name__)


class Platform(Enum):
    """支持的平台"""

    DOUYIN = "douyin"  # 抖音
    XIAOHONGSHU = "xiaohongshu"  # 小红书
    KUAISHOU = "kuaishou"  # 快手
    BILIBILI = "bilibili"  # B站
    TIKTOK = "tiktok"  # TikTok
    INSTAGRAM = "instagram"  # Instagram
    YOUTUBE = "youtube"  # YouTube


class AccountStatus(Enum):
    """账号状态"""

    ACTIVE = "active"  # 正常
    INACTIVE = "inactive"  # 未激活
    SUSPENDED = "suspended"  # 被封禁
    RESTRICTED = "restricted"  # 受限
    PENDING = "pending"  # 待审核


class AccountPhase(Enum):
    """账号运营阶段"""

    WARMUP = "warmup"  # 养号期
    GROWTH = "growth"  # 成长期
    MATURE = "mature"  # 成熟期
    DECLINE = "decline"  # 衰退期


@dataclass
class PlatformAccount:
    """平台账号"""

    id: str
    platform: Platform
    account_id: str  # 平台账号ID
    account_name: str  # 账号名称
    nickname: str  # 昵称

    # 认证信息
    access_token: str
    refresh_token: str
    token_expires_at: datetime

    # 账号信息
    avatar_url: Optional[str] = None
    followers: int = 0
    following: int = 0
    total_likes: int = 0
    total_views: int = 0
    content_count: int = 0

    # 状态
    status: AccountStatus = AccountStatus.ACTIVE
    phase: AccountPhase = AccountPhase.WARMUP

    # 分组标签
    tags: Optional[List[str]] = None
    region: Optional[str] = None
    category: Optional[str] = None

    # 风控
    risk_score: float = 0.0
    last_violation_at: Optional[datetime] = None
    violation_count: int = 0

    # 时间戳
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.tags is None:
            self.tags = []
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class AccountStats:
    """账号统计数据"""

    account_id: str
    date: datetime

    # 内容数据
    new_content: int = 0
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0

    # 粉丝数据
    new_followers: int = 0
    unfollows: int = 0
    net_followers: int = 0

    # 商业数据
    orders: int = 0
    revenue: float = 0.0
    commission: float = 0.0


class AccountManager:
    """
    多平台账号矩阵管理系统

    功能：
    1. 多平台账号统一管理
    2. OAuth授权与Token刷新
    3. 账号分组与标签
    4. 风险监控与预警
    5. 数据统计与分析
    """

    # Tables managed by core/schema.py — do not add CREATE TABLE here

    def __init__(self, db: DatabaseManager = None, security: SessionManager = None):
        self.db = db or DatabaseManager()
        self.security = security or SessionManager()

    def add_account(
        self,
        platform: Platform,
        account_id: str,
        account_name: str,
        access_token: str,
        refresh_token: str = None,
        token_expires_in: int = 3600,
        **kwargs,
    ) -> PlatformAccount:
        """
        添加平台账号

        Args:
            platform: 平台类型
            account_id: 平台账号ID
            account_name: 账号名称
            access_token: 访问令牌
            refresh_token: 刷新令牌
            token_expires_in: Token有效期(秒)
            **kwargs: 其他属性
        """
        # 加密Token
        encrypted_token = self.security.encrypt(access_token)
        encrypted_refresh = (
            self.security.encrypt(refresh_token) if refresh_token else None
        )

        expires_at = datetime.now() + timedelta(seconds=token_expires_in)

        account = PlatformAccount(
            id=f"{platform.value}_{account_id}",
            platform=platform,
            account_id=account_id,
            account_name=account_name,
            nickname=kwargs.get("nickname", account_name),
            access_token=encrypted_token,
            refresh_token=encrypted_refresh,
            token_expires_at=expires_at,
            avatar_url=kwargs.get("avatar_url"),
            followers=kwargs.get("followers", 0),
            following=kwargs.get("following", 0),
            tags=kwargs.get("tags", []),
            region=kwargs.get("region"),
            category=kwargs.get("category"),
        )

        # 保存到数据库
        self._save_account(account)

        logger.info(f"Added account: {account.id}")
        return account

    def _save_account(self, account: PlatformAccount) -> None:
        """保存账号到数据库"""
        self.db.execute(
            """
            INSERT OR REPLACE INTO platform_accounts (
                id, platform, account_id, account_name, nickname,
                access_token, refresh_token, token_expires_at,
                avatar_url, followers, following, total_likes, total_views,
                content_count, status, phase, tags, region, category,
                risk_score, last_violation_at, violation_count,
                created_at, updated_at, last_login_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                account.id,
                account.platform.value,
                account.account_id,
                account.account_name,
                account.nickname,
                account.access_token,
                account.refresh_token,
                account.token_expires_at.isoformat(),
                account.avatar_url,
                account.followers,
                account.following,
                account.total_likes,
                account.total_views,
                account.content_count,
                account.status.value,
                account.phase.value,
                json.dumps(account.tags, ensure_ascii=False),
                account.region,
                account.category,
                account.risk_score,
                account.last_violation_at.isoformat()
                if account.last_violation_at
                else None,
                account.violation_count,
                account.created_at.isoformat(),
                account.updated_at.isoformat(),
                account.last_login_at.isoformat() if account.last_login_at else None,
            ),
        )

    def get_account(self, account_id: str) -> Optional[PlatformAccount]:
        """获取账号信息"""
        row = self.db.fetchone(
            "SELECT * FROM platform_accounts WHERE id = ?", (account_id,)
        )

        if not row:
            return None

        return self._row_to_account(row)

    def _row_to_account(self, row: dict) -> PlatformAccount:
        """将数据库行转换为账号对象"""
        return PlatformAccount(
            id=row["id"],
            platform=Platform(row["platform"]),
            account_id=row["account_id"],
            account_name=row["account_name"],
            nickname=row["nickname"],
            access_token=row["access_token"],
            refresh_token=row["refresh_token"],
            token_expires_at=datetime.fromisoformat(row["token_expires_at"])
            if row["token_expires_at"]
            else None,
            avatar_url=row["avatar_url"],
            followers=row["followers"],
            following=row["following"],
            total_likes=row["total_likes"],
            total_views=row["total_views"],
            content_count=row["content_count"],
            status=AccountStatus(row["status"]),
            phase=AccountPhase(row["phase"]),
            tags=json.loads(row["tags"]) if row["tags"] else [],
            region=row["region"],
            category=row["category"],
            risk_score=row["risk_score"],
            last_violation_at=datetime.fromisoformat(row["last_violation_at"])
            if row["last_violation_at"]
            else None,
            violation_count=row["violation_count"],
            created_at=datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else None,
            updated_at=datetime.fromisoformat(row["updated_at"])
            if row["updated_at"]
            else None,
            last_login_at=datetime.fromisoformat(row["last_login_at"])
            if row["last_login_at"]
            else None,
        )

    def list_accounts(
        self,
        platform: Optional[Platform] = None,
        status: Optional[AccountStatus] = None,
        phase: Optional[AccountPhase] = None,
        tags: Optional[List[str]] = None,
        region: Optional[str] = None,
    ) -> List[PlatformAccount]:
        """
        列出账号

        支持按平台、状态、阶段、标签、地区筛选
        """
        query = "SELECT * FROM platform_accounts WHERE 1=1"
        params = []

        if platform:
            query += " AND platform = ?"
            params.append(platform.value)
        if status:
            query += " AND status = ?"
            params.append(status.value)
        if phase:
            query += " AND phase = ?"
            params.append(phase.value)
        if region:
            query += " AND region = ?"
            params.append(region)

        query += " ORDER BY created_at DESC"

        rows = self.db.fetchall(query, params)

        accounts = []
        for row in rows:
            try:
                accounts.append(self._row_to_account(row))
            except (ValueError, KeyError, TypeError):
                continue  # Skip rows with invalid enum values

        # 标签筛选（在内存中处理）
        if tags:
            accounts = [a for a in accounts if any(t in a.tags for t in tags)]

        return accounts

    def update_account_stats(
        self,
        account_id: str,
        followers: Optional[int] = None,
        following: Optional[int] = None,
        total_likes: Optional[int] = None,
        total_views: Optional[int] = None,
        content_count: Optional[int] = None,
    ):
        """更新账号统计数据"""
        updates = []
        params = []

        if followers is not None:
            updates.append("followers = ?")
            params.append(followers)
        if following is not None:
            updates.append("following = ?")
            params.append(following)
        if total_likes is not None:
            updates.append("total_likes = ?")
            params.append(total_likes)
        if total_views is not None:
            updates.append("total_views = ?")
            params.append(total_views)
        if content_count is not None:
            updates.append("content_count = ?")
            params.append(content_count)

        if not updates:
            return

        query = f"UPDATE platform_accounts SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?"  # nosec B608  # parameterized
        params.append(account_id)

        self.db.execute(query, params)
        logger.info(f"Updated stats for account: {account_id}")

    def update_account_status(
        self, account_id: str, status: AccountStatus, reason: Optional[str] = None
    ):
        """更新账号状态"""
        self.db.execute(
            """
            UPDATE platform_accounts 
            SET status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (status.value, account_id),
        )

        if status == AccountStatus.SUSPENDED:
            # 记录违规
            self.db.execute(
                """
                UPDATE platform_accounts 
                SET last_violation_at = CURRENT_TIMESTAMP,
                    violation_count = violation_count + 1
                WHERE id = ?
            """,
                (account_id,),
            )

        logger.info(f"Updated status for {account_id}: {status.value}")

    def refresh_token(
        self, account_id: str, new_token: str, expires_in: int = 3600
    ) -> None:
        """刷新访问令牌"""
        encrypted_token = self.security.encrypt(new_token)
        expires_at = datetime.now() + timedelta(seconds=expires_in)

        self.db.execute(
            """
            UPDATE platform_accounts 
            SET access_token = ?, token_expires_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """,
            (encrypted_token, expires_at.isoformat(), account_id),
        )

        logger.info(f"Refreshed token for account: {account_id}")

    def get_access_token(self, account_id: str) -> Optional[str]:
        """获取解密的访问令牌"""
        row = self.db.fetchone(
            "SELECT access_token FROM platform_accounts WHERE id = ?", (account_id,)
        )

        if not row:
            return None

        encrypted = row["access_token"]
        return self.security.decrypt(encrypted)

    def record_login(
        self,
        account_id: str,
        ip_address: str = None,
        device_info: str = None,
        location: str = None,
        success: bool = True,
        error_message: Optional[str] = None,
    ):
        """记录登录日志"""
        self.db.execute(
            """
            INSERT INTO account_login_logs (
                account_id, ip_address, device_info, location, success, error_message
            ) VALUES (?, ?, ?, ?, ?, ?)
        """,
            (account_id, ip_address, device_info, location, success, error_message),
        )

        if success:
            self.db.execute(
                """
                UPDATE platform_accounts 
                SET last_login_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (account_id,),
            )

    def get_login_logs(self, account_id: str, limit: int = 100) -> List[dict]:
        """获取登录日志"""
        return self.db.fetchall(
            """
            SELECT * FROM account_login_logs 
            WHERE account_id = ?
            ORDER BY created_at DESC
            LIMIT ?
        """,
            (account_id, limit),
        )

    def get_account_summary(self) -> dict:
        """获取账号汇总统计"""
        stats = self.db.fetchone("""
            SELECT 
                COUNT(*) as total_accounts,
                SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_accounts,
                SUM(CASE WHEN status = 'suspended' THEN 1 ELSE 0 END) as suspended_accounts,
                SUM(followers) as total_followers,
                SUM(content_count) as total_content
            FROM platform_accounts
        """)

        platform_dist = self.db.fetchall("""
            SELECT platform, COUNT(*) as count
            FROM platform_accounts
            GROUP BY platform
        """)

        return {
            "total_accounts": stats["total_accounts"],
            "active_accounts": stats["active_accounts"],
            "suspended_accounts": stats["suspended_accounts"],
            "total_followers": stats["total_followers"],
            "total_content": stats["total_content"],
            "platform_distribution": {r["platform"]: r["count"] for r in platform_dist},
        }

    def delete_account(self, account_id: str) -> None:
        """删除账号"""
        self.db.execute("DELETE FROM platform_accounts WHERE id = ?", (account_id,))
        self.db.execute("DELETE FROM account_stats WHERE account_id = ?", (account_id,))
        self.db.execute(
            "DELETE FROM account_login_logs WHERE account_id = ?", (account_id,)
        )

        logger.info(f"Deleted account: {account_id}")
