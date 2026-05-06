#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Festival Calendar Page
节日营销日历页面
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QGridLayout, QScrollArea,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QTextEdit, QDateEdit,
    QMessageBox, QTabWidget
)
from PySide6.QtCore import Qt, QDate
from PySide6.QtGui import QFont

from ...core.config import config
from ...core.logging import get_logger
from ...analytics.festival_calendar import (
    FestivalCalendar, Festival, FestivalType, MarketType
)

logger = get_logger(__name__)


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


class FestivalCard(QFrame):
    """节日卡片"""
    
    def __init__(self, festival: Festival, days_until: int = None, parent=None):
        super().__init__(parent)
        self.festival = festival
        self.days_until = days_until
        self._setup_ui()
        
    def _setup_ui(self):
        importance_colors = {
            5: COLORS['danger'],
            4: COLORS['warning'],
            3: COLORS['accent'],
            2: COLORS['success'],
            1: COLORS['text2'],
        }
        accent_color = importance_colors.get(self.festival.importance, COLORS['accent'])
        
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border: 2px solid {accent_color};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # 头部
        header = QHBoxLayout()
        
        # 节日名称
        name_layout = QVBoxLayout()
        
        name = QLabel(self.festival.name)
        name.setFont(QFont(config.ui.font_family, 16, QFont.Bold))
        name.setStyleSheet(f"color: {COLORS['text']};")
        name_layout.addWidget(name)
        
        if self.festival.name_en:
            name_en = QLabel(self.festival.name_en)
            name_en.setStyleSheet(f"color: {COLORS['text2']}; font-size: 12px;")
            name_layout.addWidget(name_en)
            
        header.addLayout(name_layout)
        header.addStretch()
        
        # 倒计时
        if self.days_until is not None:
            countdown = QLabel(f"还有 {self.days_until} 天")
            countdown.setFont(QFont(config.ui.font_family, 14, QFont.Bold))
            countdown.setStyleSheet(f"color: {accent_color};")
            header.addWidget(countdown)
            
        layout.addLayout(header)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(line)
        
        # 日期信息
        date_info = QLabel(f"📅 {self.festival.month}月{self.festival.day}日")
        if self.festival.lunar:
            date_info.setText(date_info.text() + " (农历)")
        date_info.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(date_info)
        
        # 持续时间和预热
        duration = QLabel(f"⏱ 持续 {self.festival.duration_days} 天 | 预热 {self.festival.pre_heat_days} 天")
        duration.setStyleSheet(f"color: {COLORS['text2']}; font-size: 12px;")
        layout.addWidget(duration)
        
        # 主题标签
        if self.festival.themes:
            themes_layout = QHBoxLayout()
            themes_layout.setSpacing(8)
            
            for theme in self.festival.themes[:4]:
                theme_label = QLabel(f"#{theme}")
                theme_label.setStyleSheet(f"""
                    background-color: {COLORS['card']};
                    color: {accent_color};
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                """)
                themes_layout.addWidget(theme_label)
                
            themes_layout.addStretch()
            layout.addLayout(themes_layout)
            
        # 内容建议
        if self.festival.content_tips:
            tips = QLabel(f"💡 {self.festival.content_tips}")
            tips.setStyleSheet(f"color: {COLORS['text2']}; font-size: 12px;")
            tips.setWordWrap(True)
            layout.addWidget(tips)
            
        # 操作按钮
        btn_row = QHBoxLayout()
        
        plan_btn = QPushButton("📅 创建营销计划")
        plan_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent_color};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
            }}
        """)
        btn_row.addWidget(plan_btn)
        
        content_btn = QPushButton("✨ 生成内容")
        content_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['card']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 12px;
            }}
        """)
        btn_row.addWidget(content_btn)
        
        btn_row.addStretch()
        layout.addLayout(btn_row)


class FestivalCalendarPage(QWidget):
    """节日营销日历页面"""
    
    def __init__(self):
        super().__init__()
        self.calendar = FestivalCalendar()
        self._setup_ui()
        self._load_festivals()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        # 标题
        title = QLabel("节日营销日历")
        title.setFont(QFont(config.ui.font_family, 24, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(title)
        
        subtitle = QLabel("智能节日营销规划与内容建议")
        subtitle.setStyleSheet(f"color: {COLORS['text2']}; font-size: 14px;")
        layout.addWidget(subtitle)
        
        layout.addSpacing(16)
        
        # 标签页
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                background-color: {COLORS['bg']};
            }}
            QTabBar::tab {{
                background-color: {COLORS['surface']};
                color: {COLORS['text2']};
                padding: 12px 24px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['accent']};
                color: white;
            }}
        """)
        
        # 即将来袭
        upcoming_widget = self._create_upcoming_tab()
        tabs.addTab(upcoming_widget, "🎯 即将来袭")
        
        # 全部节日
        all_widget = self._create_all_festivals_tab()
        tabs.addTab(all_widget, "📅 全部节日")
        
        # 营销计划
        plans_widget = self._create_plans_tab()
        tabs.addTab(plans_widget, "📋 营销计划")
        
        layout.addWidget(tabs)
        
    def _create_upcoming_tab(self) -> QWidget:
        """创建即将来袭标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # 筛选栏
        filter_row = QHBoxLayout()
        
        market_label = QLabel("目标市场:")
        market_label.setStyleSheet(f"color: {COLORS['text']};")
        filter_row.addWidget(market_label)
        
        self.market_combo = QComboBox()
        self.market_combo.addItems(["全部市场", "国内", "海外", "西北", "中东", "东南亚"])
        self.market_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px;
                border-radius: 6px;
                min-width: 120px;
            }}
        """)
        self.market_combo.currentTextChanged.connect(self._load_upcoming)
        filter_row.addWidget(self.market_combo)
        
        filter_row.addSpacing(20)
        
        days_label = QLabel("时间范围:")
        days_label.setStyleSheet(f"color: {COLORS['text']};")
        filter_row.addWidget(days_label)
        
        self.days_combo = QComboBox()
        self.days_combo.addItems(["30天", "60天", "90天", "半年"])
        self.days_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px;
                border-radius: 6px;
                min-width: 100px;
            }}
        """)
        self.days_combo.currentTextChanged.connect(self._load_upcoming)
        filter_row.addWidget(self.days_combo)
        
        filter_row.addStretch()
        
        layout.addLayout(filter_row)
        
        # 节日列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        
        self.upcoming_container = QWidget()
        self.upcoming_layout = QVBoxLayout(self.upcoming_container)
        self.upcoming_layout.setContentsMargins(0, 0, 0, 0)
        self.upcoming_layout.setSpacing(16)
        self.upcoming_layout.addStretch()
        
        scroll.setWidget(self.upcoming_container)
        layout.addWidget(scroll)
        
        return widget
        
    def _create_all_festivals_tab(self) -> QWidget:
        """创建全部节日标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 筛选
        filter_row = QHBoxLayout()
        
        type_label = QLabel("节日类型:")
        type_label.setStyleSheet(f"color: {COLORS['text']};")
        filter_row.addWidget(type_label)
        
        self.type_filter = QComboBox()
        self.type_filter.addItems(["全部", "传统节日", "西方节日", "购物节", "文化节日", "宗教节日"])
        self.type_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px;
                border-radius: 6px;
            }}
        """)
        self.type_filter.currentTextChanged.connect(self._filter_festivals)
        filter_row.addWidget(self.type_filter)
        
        filter_row.addStretch()
        
        layout.addLayout(filter_row)
        
        # 节日表格
        self.festivals_table = QTableWidget()
        self.festivals_table.setColumnCount(6)
        self.festivals_table.setHorizontalHeaderLabels([
            "节日名称", "日期", "类型", "市场", "重要性", "操作"
        ])
        self.festivals_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.festivals_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                gridline-color: {COLORS['border']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['card']};
                color: {COLORS['text']};
                padding: 10px;
                border: none;
                font-weight: bold;
            }}
        """)
        layout.addWidget(self.festivals_table)
        
        return widget
        
    def _create_plans_tab(self) -> QWidget:
        """创建营销计划标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        toolbar.addStretch()
        
        new_plan_btn = QPushButton("➕ 新建营销计划")
        new_plan_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        toolbar.addWidget(new_plan_btn)
        
        layout.addLayout(toolbar)
        
        # 计划表格
        self.plans_table = QTableWidget()
        self.plans_table.setColumnCount(7)
        self.plans_table.setHorizontalHeaderLabels([
            "计划名称", "节日", "时间", "平台", "内容数", "预算", "状态"
        ])
        self.plans_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.plans_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                gridline-color: {COLORS['border']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['card']};
                color: {COLORS['text']};
                padding: 10px;
                border: none;
                font-weight: bold;
            }}
        """)
        layout.addWidget(self.plans_table)
        
        return widget
        
    def _load_festivals(self):
        """加载节日数据"""
        self._load_upcoming()
        self._load_all_festivals()
        self._load_plans()
        
    def _load_upcoming(self):
        """加载即将到来的节日"""
        # 清空列表
        while self.upcoming_layout.count() > 1:
            item = self.upcoming_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # 获取市场筛选
        market_map = {
            "全部市场": None,
            "国内": MarketType.DOMESTIC,
            "海外": MarketType.OVERSEAS,
            "西北": MarketType.NORTHWEST,
            "中东": MarketType.MIDDLE_EAST,
            "东南亚": MarketType.SOUTHEAST_ASIA,
        }
        market = market_map.get(self.market_combo.currentText())
        
        # 获取时间范围
        days_map = {
            "30天": 30,
            "60天": 60,
            "90天": 90,
            "半年": 180,
        }
        days = days_map.get(self.days_combo.currentText(), 30)
        
        # 获取节日
        from datetime import datetime
        today = datetime.now()
        
        festivals = self.calendar.list_festivals(market=market)
        
        # 计算倒计时并筛选
        upcoming = []
        for festival in festivals:
            festival_date = datetime(today.year, festival.month, festival.day)
            if festival_date < today:
                festival_date = datetime(today.year + 1, festival.month, festival.day)
                
            days_until = (festival_date - today).days
            if days_until <= days:
                upcoming.append((days_until, festival))
                
        upcoming.sort(key=lambda x: x[0])
        
        # 显示卡片
        for days_until, festival in upcoming[:10]:  # 最多显示10个
            card = FestivalCard(festival, days_until)
            self.upcoming_layout.insertWidget(self.upcoming_layout.count() - 1, card)
            
    def _filter_festivals(self):
        """根据类型筛选节日"""
        self._load_all_festivals()
        
    def _load_all_festivals(self):
        """加载全部节日"""
        # 获取筛选条件
        type_map_reverse = {
            "传统节日": FestivalType.TRADITIONAL,
            "西方节日": FestivalType.WESTERN,
            "购物节": FestivalType.SHOPPING,
            "文化节日": FestivalType.CULTURAL,
            "宗教节日": FestivalType.RELIGIOUS,
        }
        selected_type = self.type_filter.currentText()
        
        festivals = self.calendar.list_festivals()
        
        # 应用类型筛选
        if selected_type != "全部":
            filter_type = type_map_reverse.get(selected_type)
            if filter_type:
                festivals = [f for f in festivals if f.festival_type == filter_type]
        
        self.festivals_table.setRowCount(len(festivals))
        
        type_map = {
            FestivalType.TRADITIONAL: "传统节日",
            FestivalType.WESTERN: "西方节日",
            FestivalType.SHOPPING: "购物节",
            FestivalType.CULTURAL: "文化节日",
            FestivalType.RELIGIOUS: "宗教节日",
            FestivalType.CUSTOM: "自定义",
        }
        
        for i, festival in enumerate(festivals):
            self.festivals_table.setItem(i, 0, QTableWidgetItem(festival.name))
            
            date_text = f"{festival.month}月{festival.day}日"
            if festival.lunar:
                date_text += " (农历)"
            self.festivals_table.setItem(i, 1, QTableWidgetItem(date_text))
            
            self.festivals_table.setItem(i, 2, QTableWidgetItem(type_map.get(festival.festival_type, "")))
            
            markets = ", ".join([m.value for m in festival.markets])
            self.festivals_table.setItem(i, 3, QTableWidgetItem(markets))
            
            importance = "⭐" * festival.importance
            self.festivals_table.setItem(i, 4, QTableWidgetItem(importance))
            
            action_btn = QPushButton("创建计划")
            self.festivals_table.setCellWidget(i, 5, action_btn)
            
    def _load_plans(self):
        """加载营销计划"""
        plans = self.calendar.get_marketing_plans()
        
        self.plans_table.setRowCount(len(plans))
        
        for i, plan in enumerate(plans):
            self.plans_table.setItem(i, 0, QTableWidgetItem(plan.name))
            
            festival = self.calendar.get_festival(plan.festival_id)
            festival_name = festival.name if festival else plan.festival_id
            self.plans_table.setItem(i, 1, QTableWidgetItem(festival_name))
            
            date_range = f"{plan.start_date.strftime('%m/%d')} - {plan.end_date.strftime('%m/%d')}"
            self.plans_table.setItem(i, 2, QTableWidgetItem(date_range))
            
            platforms = ", ".join(plan.target_platforms)
            self.plans_table.setItem(i, 3, QTableWidgetItem(platforms))
            
            self.plans_table.setItem(i, 4, QTableWidgetItem(str(plan.content_count)))
            
            budget = f"¥{plan.budget:,.0f}"
            self.plans_table.setItem(i, 5, QTableWidgetItem(budget))
            
            status_map = {
                "draft": "草稿",
                "active": "进行中",
                "completed": "已完成",
                "cancelled": "已取消",
            }
            self.plans_table.setItem(i, 6, QTableWidgetItem(status_map.get(plan.status, plan.status)))
