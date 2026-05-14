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

from ..core.config import config
from ..core.logging import get_logger
from ..services.user_service import user_service
from .auth.login_dialog import LoginDialog

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
        self.current_user = None
        
        self._setup_styles()
        self._setup_ui()
        
        # Show login dialog
        self._show_login_dialog()
        
        logger.info("Main window initialized")
    
    def _show_login_dialog(self):
        """显示登录对话框"""
        login_dialog = LoginDialog(self)
        login_dialog.login_success.connect(self._on_login_success)
        
        if login_dialog.exec() != LoginDialog.Accepted:
            # 用户取消登录，退出应用
            self.close()
            return False
        return True
    
    def _on_login_success(self, user_data):
        """登录成功回调"""
        self.current_user = user_data
        self.setWindowTitle(f"{config().name} v{config().version} - {user_data.get('nickname', user_data.get('username', ''))}")
        
        # 更新仪表盘欢迎信息
        if hasattr(self, 'dashboard_page'):
            self.dashboard_page.update_welcome(user_data.get('nickname', user_data.get('username', '')))
        
        logger.info(f"User logged in: {user_data.get('username')}")
    
    def _setup_styles(self):
        """Setup application styles"""
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {COLORS['bg']};
            }}
            QWidget {{
                background-color: {COLORS['bg']};
                color: {COLORS['text']};
                font-family: "{config().ui.font_family}";
                font-size: {config().ui.font_size}pt;
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
        """Create navigation sidebar with scrollable nav area"""
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
        logo = QLabel(config().name)
        logo.setFont(QFont(config().ui.font_family, 24, QFont.Bold))
        logo.setStyleSheet(f"color: {COLORS['accent']}; padding-bottom: 8px;")
        layout.addWidget(logo)
        
        subtitle = QLabel("企业版")
        subtitle.setStyleSheet(f"color: {COLORS['text2']}; font-size: 12px; padding-bottom: 16px;")
        layout.addWidget(subtitle)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet(f"background-color: {COLORS['border']}; max-height: 1px;")
        layout.addWidget(separator)
        layout.addSpacing(8)
        
        # Scrollable navigation area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: transparent;
            }}
            QScrollBar:vertical {{
                background-color: {COLORS['surface']};
                width: 8px;
                border-radius: 4px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {COLORS['border']};
                border-radius: 4px;
                min-height: 32px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {COLORS['accent']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        # Navigation container
        nav_container = QWidget()
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 8, 0, 8)
        nav_layout.setSpacing(4)
        
        # Navigation buttons
        self.nav_buttons = []
        nav_items = [
            ("仪表盘", "dashboard"),
            ("AI助手", "llm"),
            ("内容创作", "content"),
            ("账号矩阵", "accounts"),
            ("节日营销", "festival"),
            ("视频制作", "video"),
            ("发布管理", "publish"),
            ("广告投放", "ads"),
            ("AI数字人", "avatar"),
            ("电商管理", "ecommerce"),
            ("区块链结算", "blockchain"),
            ("销售预测", "forecast"),
            ("库存管理", "inventory"),
            ("市场情报", "intelligence"),
            ("高级分析", "analytics"),
            ("系统设置", "settings"),
        ]
        
        for text, nav_id in nav_items:
            btn = SidebarButton(text)
            btn.clicked.connect(lambda checked, nid=nav_id: self._navigate(nid))
            nav_layout.addWidget(btn)
            self.nav_buttons.append((btn, nav_id))
        
        nav_layout.addStretch()
        
        scroll_area.setWidget(nav_container)
        layout.addWidget(scroll_area, 1)
        
        # User info (fixed at bottom)
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
        
        # Store dashboard page reference for updates
        self.dashboard_page = None
        
        # Content stack
        self.content_stack = QStackedWidget()
        
        # Add pages
        from .pages.dashboard import DashboardPage
        from .pages.content_creation import ContentCreationPage
        from .pages.account_management import AccountManagementPage
        from .pages.festival_calendar import FestivalCalendarPage
        from .pages.forecast import ForecastPage
        from .pages.inventory import InventoryPage
        from .pages.intelligence import IntelligencePage
        from .pages.video_maker import VideoMakerPage
        from .pages.publish_manager import PublishManagerPage
        from .pages.ad_manager import AdManagerPage
        from .pages.avatar_studio import AvatarStudioPage
        from .pages.ecommerce_manager import EcommerceManagerPage
        from .pages.blockchain_settlement import BlockchainSettlementPage
        from .pages.advanced_analytics import AdvancedAnalyticsPage
        from .pages.settings import SettingsPage
        from .pages.llm_chat import LLMChatPage
        
        # Create pages
        dashboard_page = DashboardPage()
        self.dashboard_page = dashboard_page
        
        self.pages = {
            "dashboard": dashboard_page,
            "llm": LLMChatPage(),
            "content": ContentCreationPage(),
            "accounts": AccountManagementPage(),
            "festival": FestivalCalendarPage(),
            "video": VideoMakerPage(),
            "publish": PublishManagerPage(),
            "ads": AdManagerPage(),
            "avatar": AvatarStudioPage(),
            "ecommerce": EcommerceManagerPage(),
            "blockchain": BlockchainSettlementPage(),
            "forecast": ForecastPage(),
            "inventory": InventoryPage(),
            "intelligence": IntelligencePage(),
            "analytics": AdvancedAnalyticsPage(),
            "settings": SettingsPage(),
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
        self.page_title = QLabel("仪表盘")
        self.page_title.setFont(QFont(config().ui.font_family, 18, QFont.Bold))
        layout.addWidget(self.page_title)
        
        layout.addStretch()
        
        # Actions
        refresh_btn = QPushButton("🔄 刷新")
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
            "dashboard": "仪表盘",
            "llm": "AI 助手",
            "content": "内容创作中心",
            "accounts": "账号矩阵管理",
            "festival": "节日营销日历",
            "video": "智能视频制作",
            "publish": "多平台发布管理",
            "ads": "智能广告投放",
            "avatar": "AI数字人工作室",
            "ecommerce": "电商管理中心",
            "blockchain": "区块链结算中心",
            "forecast": "销售预测",
            "inventory": "库存优化",
            "intelligence": "市场情报",
            "analytics": "高级数据分析",
            "settings": "系统设置",
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
