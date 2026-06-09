#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Data Monitor
基础数据监测系统
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from ..core.logging import get_logger
from ..core.database import DatabaseManager

logger = get_logger(__name__)

# Tables managed by core/schema.py — do not add CREATE TABLE here


class MetricType(Enum):
    """指标类型"""
    VIEWS = "views"           # 播放量
    LIKES = "likes"           # 点赞
    COMMENTS = "comments"     # 评论
    SHARES = "shares"         # 分享
    FOLLOWERS = "followers"   # 粉丝
    ORDERS = "orders"         # 订单
    REVENUE = "revenue"       # 收入
    CTR = "ctr"               # 点击率
    CVR = "cvr"               # 转化率


@dataclass
class MetricData:
    """指标数据点"""
    timestamp: datetime
    metric_type: MetricType
    platform: str
    account_id: str
    value: float
    content_id: Optional[str] = None


@dataclass
class PerformanceReport:
    """绩效报告"""
    period_start: datetime
    period_end: datetime
    platform: Optional[str]
    account_id: Optional[str]
    
    # 内容指标
    total_views: int = 0
    total_likes: int = 0
    total_comments: int = 0
    total_shares: int = 0
    content_count: int = 0
    
    # 粉丝指标
    follower_growth: int = 0
    follower_count: int = 0
    
    # 商业指标
    total_orders: int = 0
    total_revenue: float = 0.0
    avg_order_value: float = 0.0
    
    # 效率指标
    engagement_rate: float = 0.0
    ctr: float = 0.0
    cvr: float = 0.0
    
    # 趋势
    views_trend: float = 0.0  # 环比变化
    revenue_trend: float = 0.0


class DataMonitor:
    """
    基础数据监测系统
    
    功能：
    1. 多平台数据采集
    2. 实时数据监控
    3. 异常预警
    4. 趋势分析
    5. 绩效报告生成
    """
    
    def __init__(self, db: 'DatabaseManager' = None):
        self.db = db or DatabaseManager()
        
    def record_metric(
        self,
        metric_type: MetricType,
        platform: str,
        account_id: str,
        value: float,
        content_id: str = None,
        timestamp: datetime = None
    ):
        """记录指标数据"""
        if timestamp is None:
            timestamp = datetime.now()
            
        self.db.execute("""
            INSERT INTO metrics_data (timestamp, metric_type, platform, account_id, content_id, value)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (timestamp.isoformat(), metric_type.value, platform, account_id, content_id, value))
        
    def get_metrics(
        self,
        metric_type: MetricType,
        platform: str = None,
        account_id: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        limit: int = 1000
    ) -> List[MetricData]:
        """获取指标数据"""
        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(days=7)
            
        query = """
            SELECT * FROM metrics_data 
            WHERE metric_type = ? AND timestamp BETWEEN ? AND ?
        """
        params = [metric_type.value, start_time.isoformat(), end_time.isoformat()]
        
        if platform:
            query += " AND platform = ?"
            params.append(platform)
        if account_id:
            query += " AND account_id = ?"
            params.append(account_id)
            
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        rows = self.db.fetchall(query, params)
        
        return [
            MetricData(
                timestamp=datetime.fromisoformat(row['timestamp']),
                metric_type=MetricType(row['metric_type']),
                platform=row['platform'],
                account_id=row['account_id'],
                value=row['value'],
                content_id=row['content_id']
            )
            for row in rows
        ]
        
    def aggregate_daily(
        self,
        platform: str,
        account_id: str,
        date: datetime
    ):
        """聚合每日数据"""
        start = date.replace(hour=0, minute=0, second=0)
        end = start + timedelta(days=1)
        
        # 获取当日所有指标
        metrics = self.db.fetchone("""
            SELECT 
                SUM(CASE WHEN metric_type = 'views' THEN value ELSE 0 END) as views,
                SUM(CASE WHEN metric_type = 'likes' THEN value ELSE 0 END) as likes,
                SUM(CASE WHEN metric_type = 'comments' THEN value ELSE 0 END) as comments,
                SUM(CASE WHEN metric_type = 'shares' THEN value ELSE 0 END) as shares,
                SUM(CASE WHEN metric_type = 'followers' THEN value ELSE 0 END) as new_followers,
                SUM(CASE WHEN metric_type = 'orders' THEN value ELSE 0 END) as orders,
                SUM(CASE WHEN metric_type = 'revenue' THEN value ELSE 0 END) as revenue
            FROM metrics_data
            WHERE platform = ? AND account_id = ? 
            AND timestamp BETWEEN ? AND ?
        """, (platform, account_id, start.isoformat(), end.isoformat()))
        
        # 保存或更新每日汇总
        self.db.execute("""
            INSERT OR REPLACE INTO daily_metrics 
            (date, platform, account_id, views, likes, comments, shares, new_followers, orders, revenue)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date.date().isoformat(), platform, account_id,
            int(metrics['views'] or 0),
            int(metrics['likes'] or 0),
            int(metrics['comments'] or 0),
            int(metrics['shares'] or 0),
            int(metrics['new_followers'] or 0),
            int(metrics['orders'] or 0),
            float(metrics['revenue'] or 0)
        ))
        
    def generate_report(
        self,
        period_start: datetime,
        period_end: datetime,
        platform: str = None,
        account_id: str = None
    ) -> PerformanceReport:
        """生成绩效报告"""
        report = PerformanceReport(
            period_start=period_start,
            period_end=period_end,
            platform=platform,
            account_id=account_id
        )
        
        # 构建查询条件（纯参数化，防止SQL注入）
        conditions = ["date BETWEEN ? AND ?"]
        params = [period_start.date().isoformat(), period_end.date().isoformat()]
        
        if platform:
            conditions.append("platform = ?")
            params.append(platform)
        if account_id:
            conditions.append("account_id = ?")
            params.append(account_id)
        
        # 使用固定模板而非动态拼接，确保SQL结构安全
        if len(conditions) == 2:  # 只有日期条件
            where_clause = "date BETWEEN ? AND ?"
        elif len(conditions) == 3:  # 日期 + 一个条件
            if platform:
                where_clause = "date BETWEEN ? AND ? AND platform = ?"
            else:
                where_clause = "date BETWEEN ? AND ? AND account_id = ?"
        else:  # 日期 + 两个条件
            where_clause = "date BETWEEN ? AND ? AND platform = ? AND account_id = ?"
            
        # 汇总数据
        result = self.db.fetchone(f"""
            SELECT 
                SUM(views) as total_views,
                SUM(likes) as total_likes,
                SUM(comments) as total_comments,
                SUM(shares) as total_shares,
                SUM(new_followers) as follower_growth,
                SUM(orders) as total_orders,
                SUM(revenue) as total_revenue,
                COUNT(DISTINCT date) as days
            FROM daily_metrics
            WHERE {where_clause}
        """, params)
        
        if result:
            report.total_views = int(result['total_views'] or 0)
            report.total_likes = int(result['total_likes'] or 0)
            report.total_comments = int(result['total_comments'] or 0)
            report.total_shares = int(result['total_shares'] or 0)
            report.follower_growth = int(result['follower_growth'] or 0)
            report.total_orders = int(result['total_orders'] or 0)
            report.total_revenue = float(result['total_revenue'] or 0)
            
        # 计算效率指标
        if report.total_views > 0:
            report.engagement_rate = (report.total_likes + report.total_comments + report.total_shares) / report.total_views
        if report.total_orders > 0:
            report.avg_order_value = report.total_revenue / report.total_orders
            
        # 计算趋势（与上一周期对比）
        prev_start = period_start - (period_end - period_start)
        prev_end = period_start
        
        # 构建上一周期的查询条件（纯参数化，防止SQL注入）
        prev_params = [prev_start.date().isoformat(), prev_end.date().isoformat()]
        if platform and account_id:
            prev_where = "date BETWEEN ? AND ? AND platform = ? AND account_id = ?"
            prev_params.extend([platform, account_id])
        elif platform:
            prev_where = "date BETWEEN ? AND ? AND platform = ?"
            prev_params.append(platform)
        elif account_id:
            prev_where = "date BETWEEN ? AND ? AND account_id = ?"
            prev_params.append(account_id)
        else:
            prev_where = "date BETWEEN ? AND ?"
        
        prev_result = self.db.fetchone(f"""
            SELECT SUM(views) as views, SUM(revenue) as revenue
            FROM daily_metrics
            WHERE {prev_where}
        """, prev_params)
        
        if prev_result and prev_result.get('views'):
            report.views_trend = (report.total_views - prev_result['views']) / prev_result['views']
        if prev_result and prev_result.get('revenue'):
            report.revenue_trend = (report.total_revenue - prev_result['revenue']) / prev_result['revenue']
            
        return report
        
    def check_anomalies(self, platform: str, account_id: str) -> List[dict]:
        """检查数据异常"""
        alerts = []
        
        # 获取最近7天数据
        end = datetime.now()
        start = end - timedelta(days=7)
        
        daily_data = self.db.fetchall("""
            SELECT date, views, likes, comments, shares
            FROM daily_metrics
            WHERE platform = ? AND account_id = ? AND date BETWEEN ? AND ?
            ORDER BY date
        """, (platform, account_id, start.date().isoformat(), end.date().isoformat()))
        
        if len(daily_data) < 3:
            return alerts
            
        # 计算平均值和标准差
        views_values = [d['views'] for d in daily_data if d['views']]
        if views_values:
            avg_views = sum(views_values) / len(views_values)
            
            # 检查最近一天是否异常
            latest = daily_data[-1]
            if latest['views'] < avg_views * 0.5:
                alerts.append({
                    'type': 'views_drop',
                    'severity': 'warning',
                    'message': f'播放量较平均值下降超过50% ({latest["views"]:,} vs {avg_views:,.0f})',
                    'date': latest['date']
                })
            elif latest['views'] > avg_views * 3:
                alerts.append({
                    'type': 'views_spike',
                    'severity': 'info',
                    'message': f'播放量异常增长 ({latest["views"]:,} vs {avg_views:,.0f})',
                    'date': latest['date']
                })
                
        return alerts
        
    def create_alert(
        self,
        alert_type: str,
        message: str,
        severity: str = "warning",
        platform: str = None,
        account_id: str = None,
        content_id: str = None
    ):
        """创建预警"""
        self.db.execute("""
            INSERT INTO data_alerts (alert_type, platform, account_id, content_id, message, severity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (alert_type, platform, account_id, content_id, message, severity))
        
        logger.warning(f"Data alert created: {alert_type} - {message}")
        
    def get_alerts(
        self,
        acknowledged: bool = False,
        severity: str = None,
        limit: int = 100
    ) -> List[dict]:
        """获取预警列表"""
        query = "SELECT * FROM data_alerts WHERE acknowledged = ?"
        params = [acknowledged]
        
        if severity:
            query += " AND severity = ?"
            params.append(severity)
            
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        return self.db.fetchall(query, params)
        
    def acknowledge_alert(self, alert_id: int, user: str) -> None:
        """确认预警"""
        self.db.execute("""
            UPDATE data_alerts 
            SET acknowledged = 1, acknowledged_at = CURRENT_TIMESTAMP, acknowledged_by = ?
            WHERE id = ?
        """, (user, alert_id))
