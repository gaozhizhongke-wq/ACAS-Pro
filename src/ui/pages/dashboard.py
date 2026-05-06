#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Dashboard Page
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from acas_pro.core.config import config
from acas_pro.services.user_service import user_service


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
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
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
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(24)
        
        # Welcome section
        user = user_service.get_current()
        welcome = QLabel(f"Welcome back, {user.nickname if user else 'User'}! 👋")
        welcome.setFont(QFont(config.ui.font_family, 24, QFont.Bold))
        welcome.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(welcome)
        
        subtitle = QLabel("Here's what's happening with your business today")
        subtitle.setStyleSheet(f"color: {COLORS['text2']}; font-size: 14px;")
        layout.addWidget(subtitle)
        
        layout.addSpacing(16)
        
        # KPI Grid
        kpi_grid = QGridLayout()
        kpi_grid.setSpacing(16)
        
        kpis = [
            ("Total Revenue", "$128,450", "+12.5% from last month", COLORS['success']),
            ("Active Orders", "1,284", "+8.2% from last month", COLORS['accent']),
            ("Inventory Items", "5,240", "23 items need reorder", COLORS['warning']),
            ("Risk Alerts", "3", "2 critical, 1 high", COLORS['danger']),
        ]
        
        for i, (title, value, subtitle, color) in enumerate(kpis):
            card = KPICard(title, value, subtitle)
            kpi_grid.addWidget(card, i // 2, i % 2)
        
        layout.addLayout(kpi_grid)
        
        # Quick actions
        layout.addSpacing(24)
        actions_title = QLabel("Quick Actions")
        actions_title.setFont(QFont(config.ui.font_family, 16, QFont.Bold))
        layout.addWidget(actions_title)
        
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)
        
        actions = [
            ("📊 View Forecast", self._view_forecast),
            ("📦 Check Inventory", self._check_inventory),
            ("🌍 Market Intel", self._market_intel),
            ("⚙️ Settings", self._open_settings),
        ]
        
        for text, callback in actions:
            btn = QPushButton(text)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['surface']};
                    color: {COLORS['text']};
                    border: 1px solid {COLORS['border']};
                    padding: 12px 24px;
                    border-radius: 8px;
                    font-size: 13px;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['accent']};
                    color: #fff;
                    border-color: {COLORS['accent']};
                }}
            """)
            btn.clicked.connect(callback)
            actions_layout.addWidget(btn)
        
        actions_layout.addStretch()
        layout.addLayout(actions_layout)
        
        layout.addStretch()
    
    def _view_forecast(self):
        pass
    
    def _check_inventory(self):
        pass
    
    def _market_intel(self):
        pass
    
    def _open_settings(self):
        pass
