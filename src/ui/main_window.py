#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Main Window
Enterprise-grade desktop application
"""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QFrame,
    QScrollArea, QMessageBox
)
from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QFont, QIcon

from acas_pro.core.config import config
from acas_pro.core.logging import get_logger
from acas_pro.services.user_service import user_service

logger = get_logger(__name__)


# Color scheme
COLORS = {
    "bg": "#0d1117",
    "card": "#161b22",
    "surface": "#21262d",
    "border": "#30363d",
    "text": "#c9d1d9",
    "text2": "#8b949e",
    "accent": "#58a6ff",
    "accent2": "#a371f7",
    "success": "#3fb950",
    "warning": "#d29922",
    "danger": "#f85149",
}


class SidebarButton(QPushButton):
    """Custom sidebar navigation button"""
    
    def __init__(self, text, icon="●", parent=None):
        super().__init__(parent)
        self.setText(f"  {icon}  {text}")
        self.setCheckable(True)
        self.setMinimumHeight(48)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {COLORS['text2']};
                border: none;
                padding: 12px 16px;
                text-align: left;
                font-size: 14px;
                border-radius: 8px;
            }}
            QPushButton:hover {{
                color: {COLORS['accent']};
                background-color: {COLORS['surface']};
            }}
            QPushButton:checked {{
                color: #fff;
                background-color: {COLORS['accent']};
                font-weight: bold;
            }}
        """)


class MainWindow(QMainWindow):
    """ACAS Pro Main Window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{config.name} v{config.version}")
        self.setMinimumSize(1280, 800)
        self.resize(1440, 900)
        
        self._setup_styles()
        self._setup_ui()
        
        logger.info("Main window initialized")
    
    def _setup_styles(self):
        """Setup application styles"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['bg']};
            }}
            QWidget {{
                background-color: {COLORS['bg']};
                color: {COLORS['text']};
                font-family: "{config.ui.font_family}";
                font-size: {config.ui.font_size}pt;
            }}
            QLabel {{
                color: {COLORS['text']};
            }}
            QScrollArea {{
                border: none;
            }}
        """)
    
    def _setup_ui(self):
        """Setup user interface"""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        
        # Main layout
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Sidebar
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar)
        
        # Content area
        content = self._create_content()
        main_layout.addWidget(content, 1)
    
    def _create_sidebar(self):
        """Create navigation sidebar"""
        sidebar = QFrame()
        sidebar.setMaximumWidth(280)
        sidebar.setMinimumWidth(260)
        sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border-right: 1px solid {COLORS['border']};
            }}
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 24, 20, 24)
        layout.setSpacing(12)
        
        # Logo
        logo = QLabel(config.name)
        logo.setFont(QFont(config.ui.font_family, 24, QFont.Bold))
        logo.setStyleSheet(f"color: {COLORS['accent']}; padding-bottom: 8px;")
        layout.addWidget(logo)
        
        subtitle = QLabel("Enterprise Edition")
        subtitle.setStyleSheet(f"color: {COLORS['text2']}; font-size: 12px; padding-bottom: 16px;")
        layout.addWidget(subtitle)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"background-color: {COLORS['border']}; max-height: 1px;")
        layout.addWidget(separator)
        layout.addSpacing(16)
        
        # Navigation buttons
        self.nav_buttons = []
        nav_items = [
            ("Dashboard", "dashboard"),
            ("Sales Forecast", "forecast"),
            ("Inventory", "inventory"),
            ("Market Intel", "intelligence"),
            ("Analytics", "analytics"),
            ("Settings", "settings"),
        ]
        
        for text, nav_id in nav_items:
            btn = SidebarButton(text)
            btn.clicked.connect(lambda checked, nid=nav_id: self._navigate(nid))
            layout.addWidget(btn)
            self.nav_buttons.append((btn, nav_id))
        
        layout.addStretch()
        
        # User info
        user = user_service.get_current()
        if user:
            user_label = QLabel(f"👤 {user.nickname}")
            user_label.setStyleSheet(f"color: {COLORS['text2']}; font-size: 12px; padding: 8px;")
            layout.addWidget(user_label)
        
        return sidebar
    
    def _create_content(self):
        """Create content area"""
        content = QFrame()
        content.setStyleSheet(f"background-color: {COLORS['bg']};")
        
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Top bar
        top_bar = self._create_top_bar()
        layout.addWidget(top_bar)
        
        # Content stack
        self.content_stack = QStackedWidget()
        
        # Add pages
        from acas_pro.ui.pages.dashboard import DashboardPage
        from acas_pro.ui.pages.forecast import ForecastPage
        from acas_pro.ui.pages.inventory import InventoryPage
        from acas_pro.ui.pages.intelligence import IntelligencePage
        
        self.pages = {
            "dashboard": DashboardPage(),
            "forecast": ForecastPage(),
            "inventory": InventoryPage(),
            "intelligence": IntelligencePage(),
            "analytics": QWidget(),  # Placeholder
            "settings": QWidget(),   # Placeholder
        }
        
        for nav_id, page in self.pages.items():
            self.content_stack.addWidget(page)
        
        layout.addWidget(self.content_stack, 1)
        
        return content
    
    def _create_top_bar(self):
        """Create top navigation bar"""
        top_bar = QFrame()
        top_bar.setMaximumHeight(64)
        top_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        
        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(24, 0, 24, 0)
        
        # Title
        self.page_title = QLabel("Dashboard")
        self.page_title.setFont(QFont(config.ui.font_family, 18, QFont.Bold))
        layout.addWidget(self.page_title)
        
        layout.addStretch()
        
        # Actions
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px 16px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                border-color: {COLORS['accent']};
            }}
        """)
        layout.addWidget(refresh_btn)
        
        return top_bar
    
    def _navigate(self, nav_id):
        """Navigate to page"""
        # Update button states
        for btn, nid in self.nav_buttons:
            btn.setChecked(nid == nav_id)
        
        # Update title
        titles = {
            "dashboard": "Dashboard",
            "forecast": "Sales Forecast",
            "inventory": "Inventory Optimization",
            "intelligence": "Market Intelligence",
            "analytics": "Analytics",
            "settings": "Settings",
        }
        self.page_title.setText(titles.get(nav_id, nav_id.title()))
        
        # Switch page
        page = self.pages.get(nav_id)
        if page:
            self.content_stack.setCurrentWidget(page)
            logger.info(f"Navigated to {nav_id}")
    
    def closeEvent(self, event):
        """Handle window close"""
        logger.info("Application shutting down...")
        event.accept()
