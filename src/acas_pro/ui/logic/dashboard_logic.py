#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-


"""


ACAS Pro - Dashboard Business Logic


Extracted from DashboardPage for testability


"""

from dataclasses import dataclass


from typing import List, Optional, Callable, Any


from datetime import datetime, timedelta


@dataclass
class KPIData:
    """KPI data structure"""

    title: str

    value: str

    subtitle: str

    color: str

    trend: float = 0.0  # 趋势百分比


@dataclass
class QuickAction:
    """Quick action button"""

    id: str

    label: str

    icon: str

    callback: Optional[Callable] = None


@dataclass
class AlertItem:
    """Alert/warning item"""

    level: str  # critical, high, medium, low

    message: str

    timestamp: datetime

    action_required: bool = False


class DashboardLogic:
    """


    Dashboard business logic - testable without Qt





    Responsibilities:


    - Calculate KPIs from data


    - Generate quick actions


    - Manage alerts and notifications


    - Format display data


    """

    # Color scheme

    COLORS = {
        "success": "#3fb950",
        "accent": "#58a6ff",
        "warning": "#d29922",
        "danger": "#f85149",
        "text": "#c9d1d9",
        "text2": "#8b949e",
    }

    def __init__(self, user_service=None, analytics_service=None) -> Any:

        self.user_service = user_service

        self.analytics_service = analytics_service

        self._user = None

        self._kpis: List[KPIData] = []

        self._alerts: List[AlertItem] = []

        self._quick_actions: List[QuickAction] = []

    def load_user(self) -> Optional[dict]:
        """Load current user info"""

        if self.user_service:
            self._user = self.user_service.get_current()

            return self._user

        return None

    def get_welcome_message(self) -> str:
        """Generate welcome message"""

        nickname = self._user.get("nickname", "用户") if self._user else "用户"

        return f"欢迎回来, {nickname}! 👋"

    def get_subtitle(self) -> str:
        """Get dashboard subtitle"""

        return "以下是您今日的业务概览"

    def calculate_kpis(self, data: Optional[dict] = None) -> List[KPIData]:
        """


        Calculate KPIs from business data





        Args:


            data: Raw business data (revenue, orders, inventory, alerts)





        Returns:


            List of KPIData objects


        """

        if data is None:
            data = self._fetch_default_data()

        kpis = []

        # Revenue KPI

        revenue = data.get("revenue", 0)

        revenue_prev = data.get("revenue_prev", revenue)

        revenue_trend = (
            ((revenue - revenue_prev) / revenue_prev * 100) if revenue_prev else 0
        )

        kpis.append(
            KPIData(
                title="总营收",
                value=self._format_currency(revenue),
                subtitle=f"较上月{self._format_trend(revenue_trend)}",
                color=self.COLORS["success"],
                trend=revenue_trend,
            )
        )

        # Active orders KPI

        orders = data.get("active_orders", 0)

        orders_prev = data.get("orders_prev", orders)

        orders_trend = (
            ((orders - orders_prev) / orders_prev * 100) if orders_prev else 0
        )

        kpis.append(
            KPIData(
                title="活跃订单",
                value=self._format_number(orders),
                subtitle=f"较上月{self._format_trend(orders_trend)}",
                color=self.COLORS["accent"],
                trend=orders_trend,
            )
        )

        # Inventory KPI

        inventory = data.get("inventory_count", 0)

        low_stock = data.get("low_stock_count", 0)

        kpis.append(
            KPIData(
                title="库存商品",
                value=self._format_number(inventory),
                subtitle=f"{low_stock}项需补货" if low_stock > 0 else "库存充足",
                color=self.COLORS["warning"]
                if low_stock > 0
                else self.COLORS["success"],
                trend=0,
            )
        )

        # Alerts KPI

        critical = data.get("critical_alerts", 0)

        high = data.get("high_alerts", 0)

        medium = data.get("medium_alerts", 0)

        total_alerts = critical + high + medium

        if total_alerts > 0:
            alert_text = f"{critical}个紧急 {high}个高"

            alert_color = (
                self.COLORS["danger"] if critical > 0 else self.COLORS["warning"]
            )

        else:
            alert_text = "无风险"

            alert_color = self.COLORS["success"]

        kpis.append(
            KPIData(
                title="风险预警",
                value=str(total_alerts),
                subtitle=alert_text,
                color=alert_color,
                trend=0,
            )
        )

        self._kpis = kpis

        return kpis

    def get_quick_actions(self) -> List[QuickAction]:
        """Get available quick actions"""

        return [
            QuickAction(id="forecast", label="查看预测", icon="📊"),
            QuickAction(id="inventory", label="库存检查", icon="📦"),
            QuickAction(id="market", label="市场情报", icon="🌍"),
            QuickAction(id="settings", label="系统设置", icon="⚙️"),
        ]

    def get_alerts(self, limit: int = 10) -> List[AlertItem]:
        """Get recent alerts"""

        # This would fetch from alert service

        return self._alerts[:limit]

    def refresh_data(self) -> dict:
        """Refresh all dashboard data"""

        self.load_user()

        data = self._fetch_default_data()

        self.calculate_kpis(data)

        self._alerts = self._fetch_alerts()

        return {"user": self._user, "kpis": self._kpis, "alerts": self._alerts}

    def _fetch_default_data(self) -> dict:
        """Fetch default/mock data"""

        # In production, this would call analytics service

        return {
            "revenue": 128450,
            "revenue_prev": 114200,
            "active_orders": 1284,
            "orders_prev": 1186,
            "inventory_count": 5240,
            "low_stock_count": 23,
            "critical_alerts": 2,
            "high_alerts": 1,
            "medium_alerts": 0,
        }

    def _fetch_alerts(self) -> List[AlertItem]:
        """Fetch alerts from alert service"""

        # Mock alerts for testing

        return [
            AlertItem(
                level="critical",
                message="库存不足: 产品 SKU-12345",
                timestamp=datetime.now(),
                action_required=True,
            ),
            AlertItem(
                level="high",
                message="订单处理延迟超过 2 小时",
                timestamp=datetime.now() - timedelta(hours=1),
                action_required=True,
            ),
        ]

    @staticmethod
    def _format_currency(value: float) -> str:
        """Format as currency"""

        if value >= 10000:
            return f"¥{value / 10000:.1f}万"

        return f"¥{value:,.0f}"

    @staticmethod
    def _format_number(value: int) -> str:
        """Format large numbers"""

        if value >= 10000:
            return f"{value / 10000:.1f}万"

        return f"{value:,}"

    @staticmethod
    def _format_trend(percent: float) -> str:
        """Format trend percentage"""

        arrow = "↑" if percent > 0 else "↓" if percent < 0 else "→"
        return f"{arrow}{abs(percent):.1f}%"
