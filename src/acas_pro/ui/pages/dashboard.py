#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Dashboard Page
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGridLayout,
)
from PySide6.QtGui import QFont

from ...core.config import config
from ...services.user_service import user_service

COLORS = {
    "bg": "#0d1117",
    "card": "#161b22",
    "surface": "#21262d",
    "border": "#30363d",
    "text": "#c9d1d9",
    "text2": "#8b949e",
    "accent": "#58a6ff",
    "success": "#3fb950",
    "warning": "#d29922",
    "danger": "#f85149",
}


class KPICard(QFrame):
    """KPI metric card"""

    def __init__(self, title, value, subtitle="", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["card"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 12px;
                padding: 20px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {COLORS['text2']}; font-size: 13px;")
        layout.addWidget(title_label)

        value_label = QLabel(value)
        value_label.setFont(QFont(config.ui.font_family, 32, QFont.Bold))
        value_label.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(value_label)

        if subtitle:
            sub_label = QLabel(subtitle)
            sub_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 12px;")
            layout.addWidget(sub_label)

        layout.addStretch()


class DashboardPage(QWidget):
    """Main dashboard page"""

    def __init__(self):
        super().__init__()
        self.welcome_label = None
        self._setup_ui()

    def update_welcome(self, nickname) -> None:
        """更新欢迎信息"""
        if self.welcome_label:
            self.welcome_label.setText(f"欢迎回来, {nickname}! 👋")

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(24)

        # Welcome section
        user = user_service.get_current()
        self.welcome_label = QLabel(
            f"欢迎回来, {user.nickname if user else '用户'}! 👋"
        )
        self.welcome_label.setFont(QFont(config.ui.font_family, 24, QFont.Bold))
        self.welcome_label.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(self.welcome_label)

        subtitle = QLabel("以下是您今日的业务概览")
        subtitle.setStyleSheet(f"color: {COLORS['text2']}; font-size: 14px;")
        layout.addWidget(subtitle)

        layout.addSpacing(16)

        # KPI Grid
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(16)

        kpis = [
            ("总营收", "¥128,450", "较上月 +12.5%", COLORS["success"]),
            ("活跃订单", "1,284", "较上月 +8.2%", COLORS["accent"]),
            ("库存商品", "5,240", "23项需补货", COLORS["warning"]),
            ("风险预警", "3", "2个紧急, 1个高", COLORS["danger"]),
        ]

        for i, (title, value, subtitle, color) in enumerate(kpis):
            card = KPICard(title, value, subtitle)
            kpi_grid.addWidget(card, i // 2, i % 2)

        layout.addLayout(kpi_grid)

        # Quick actions
        layout.addSpacing(24)
        actions_title = QLabel("快速操作")
        actions_title.setFont(QFont(config.ui.font_family, 16, QFont.Bold))
        layout.addWidget(actions_title)

        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)

        actions = [
            ("📊 查看预测", self._view_forecast),
            ("📦 库存检查", self._check_inventory),
            ("🌍 市场情报", self._market_intel),
            ("⚙️ 系统设置", self._open_settings),
        ]

        for text, callback in actions:
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS["surface"]};
                    color: {COLORS["text"]};
                    border: 1px solid {COLORS["border"]};
                    padding: 12px 24px;
                    border-radius: 8px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS["accent"]};
                    color: #fff;
                    border-color: {COLORS["accent"]};
                }}
            """)
            btn.clicked.connect(callback)
            actions_layout.addWidget(btn)

        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        layout.addStretch()

    def _view_forecast(self) -> None:
        pass

    def _check_inventory(self) -> None:
        pass

    def _market_intel(self) -> None:
        pass

    def _open_settings(self) -> None:
        pass
