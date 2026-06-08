"""
高级数据分析页面 - 归因分析与智能决策
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QComboBox,
    QDateEdit, QSpinBox, QTextEdit, QProgressBar, QFrame,
    QGroupBox, QGridLayout, QScrollArea, QCheckBox, QLineEdit,
    QListWidget, QListWidgetItem, QSplitter, QStackedWidget,
    QTableWidget, QHeaderView, QAbstractItemView, QStatusBar,
    QMenu, QMenuBar, QToolBar, QDialog, QDialogButtonBox,
    QFormLayout, QDoubleSpinBox, QSlider, QRadioButton,
    QButtonGroup, QTreeWidget, QTreeWidgetItem, QCalendarWidget
)
from PySide6.QtCore import Qt, QDate, QTimer, Signal, Slot, QSize
from PySide6.QtGui import QFont, QColor, QPalette, QAction, QIcon, QPainter, QPen
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import random

# 颜色配置
COLORS = {
    'primary': '#6366F1',
    'secondary': '#8B5CF6',
    'success': '#10B981',
    'warning': '#F59E0B',
    'danger': '#EF4444',
    'info': '#3B82F6',
    'dark': '#1F2937',
    'light': '#F9FAFB',
    'gray': '#6B7280',
    'bg_dark': '#111827',
    'bg_card': '#1F2937',
    'border': '#374151',
    'text': '#F9FAFB',
    'text_secondary': '#9CA3AF',
}


class AttributionChart(QFrame):
    """归因分析图表组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = []
        self.setMinimumHeight(300)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
    
    def set_data(self, data: Dict[str, float]) -> None:
        """设置图表数据"""
        self.data = data
        self.update()
    
    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if not self.data:
            painter.drawText(self.rect(), Qt.AlignCenter, "暂无数据")
            return
        
        # 绘制柱状图
        channels = list(self.data.keys())
        values = list(self.data.values())
        max_value = max(values) if values else 1
        
        bar_width = (self.width() - 100) / len(channels) - 10
        x = 50
        
        colors = [QColor('#6366F1'), QColor('#8B5CF6'), QColor('#10B981'), 
                  QColor('#F59E0B'), QColor('#EF4444'), QColor('#3B82F6')]
        
        for i, (channel, value) in enumerate(zip(channels, values)):
            bar_height = (value / max_value) * (self.height() - 80)
            
            # 绘制柱子
            painter.setFillRule(Qt.OddEvenFillRule)
            painter.setBrush(colors[i % len(colors)])
            painter.setPen(Qt.NoPen)
            painter.drawRect(int(x), int(self.height() - 40 - bar_height), 
                          int(bar_width), int(bar_height))
            
            # 绘制标签
            painter.setPen(QColor(COLORS['text']))
            font = QFont()
            font.setPointSize(8)
            painter.setFont(font)
            painter.drawText(int(x), self.height() - 25, int(bar_width), 20, 
                           Qt.AlignCenter, channel[:8])
            
            # 绘制数值
            painter.drawText(int(x), int(self.height() - 45 - bar_height), 
                          int(bar_width), 20, Qt.AlignCenter, f"{value:.1f}%")
            
            x += bar_width + 10


class DecisionCard(QFrame):
    """决策卡片组件"""
    
    def __init__(self, decision: Dict, parent=None):
        super().__init__(parent)
        self.decision = decision
        self._init_ui()
    
    def _init_ui(self) -> None:
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        
        # 标题行
        header_layout = QHBoxLayout()
        
        # 优先级标签
        priority = self.decision.get('priority', 'P2')
        priority_colors = {
            'P0': COLORS['danger'],
            'P1': COLORS['warning'],
            'P2': COLORS['info'],
            'P3': COLORS['gray']
        }
        
        priority_label = QLabel(priority)
        priority_label.setStyleSheet(f"""
            background-color: {priority_colors.get(priority, COLORS['gray'])};
            color: white;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: bold;
        """)
        header_layout.addWidget(priority_label)
        
        # 决策类型
        decision_type = self.decision.get('type', '')
        type_label = QLabel(decision_type)
        type_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        header_layout.addWidget(type_label)
        header_layout.addStretch()
        
        # 状态标签
        status = self.decision.get('status', 'pending')
        status_label = QLabel(f"● {status}")
        status_colors = {
            'pending': COLORS['warning'],
            'approved': COLORS['info'],
            'executing': COLORS['secondary'],
            'completed': COLORS['success'],
            'skipped': COLORS['gray']
        }
        status_label.setStyleSheet(f"color: {status_colors.get(status, COLORS['gray'])};")
        header_layout.addWidget(status_label)
        
        layout.addLayout(header_layout)
        
        # 标题
        title = QLabel(self.decision.get('title', ''))
        title.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        layout.addWidget(title)
        
        # 描述
        desc = QLabel(self.decision.get('description', ''))
        desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # 指标信息
        metrics_layout = QHBoxLayout()
        
        current = self.decision.get('current_value', 0)
        target = self.decision.get('target_value', 0)
        metrics_layout.addWidget(QLabel(f"当前: {current}"))
        metrics_layout.addWidget(QLabel(f"→ 目标: {target}"))
        metrics_layout.addStretch()
        
        impact = self.decision.get('expected_impact', 0)
        impact_label = QLabel(f"预期影响: {impact:+.1%}")
        impact_color = COLORS['success'] if impact > 0 else COLORS['danger']
        impact_label.setStyleSheet(f"color: {impact_color}; font-weight: bold;")
        metrics_layout.addWidget(impact_label)
        
        layout.addLayout(metrics_layout)
        
        # 置信度
        confidence_layout = QHBoxLayout()
        confidence_layout.addWidget(QLabel("置信度:"))
        
        confidence = self.decision.get('confidence', 0.7)
        confidence_bar = QProgressBar()
        confidence_bar.setValue(int(confidence * 100))
        confidence_bar.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                background-color: {COLORS['dark']};
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['primary']};
                border-radius: 4px;
            }}
        """)
        confidence_bar.setMaximumWidth(100)
        confidence_layout.addWidget(confidence_bar)
        confidence_layout.addWidget(QLabel(f"{confidence:.0%}"))
        confidence_layout.addStretch()
        
        layout.addLayout(confidence_layout)
        
        # 关联渠道
        channels = self.decision.get('related_channels', [])
        if channels:
            channels_label = QLabel(f"关联渠道: {', '.join(channels[:3])}")
            channels_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
            layout.addWidget(channels_label)


class AdvancedAnalyticsPage(QWidget):
    """高级数据分析页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.attribution_engine = None
        self.smart_decider = None
        self._init_engines()
        self._init_ui()
    
    def _init_engines(self) -> None:
        """初始化分析引擎"""
        try:
            from .advanced_analytics import AttributionEngine, SmartDecider
            self.attribution_engine = AttributionEngine()
            self.smart_decider = SmartDecider()
        except ImportError:
            pass
    
    def _init_ui(self) -> None:
        """初始化UI"""
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
            }}
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(24, 24, 24, 24)
        
        # 创建标签页
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text_secondary']};
                padding: 12px 24px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['bg_card']};
                color: {COLORS['primary']};
                font-weight: bold;
            }}
            QTabBar::tab:hover {{
                background-color: {COLORS['border']};
            }}
        """)
        
        # 归因分析标签
        self.attribution_tab = self._create_attribution_tab()
        self.tabs.addTab(self.attribution_tab, "📊 归因分析")
        
        # 智能决策标签
        self.decision_tab = self._create_decision_tab()
        self.tabs.addTab(self.decision_tab, "🎯 智能决策")
        
        # 对比分析标签
        self.compare_tab = self._create_compare_tab()
        self.tabs.addTab(self.compare_tab, "📈 模型对比")
        
        # 报告中心标签
        self.report_tab = self._create_report_tab()
        self.tabs.addTab(self.report_tab, "📋 报告中心")
        
        main_layout.addWidget(self.tabs)
    
    def _create_attribution_tab(self) -> QWidget:
        """创建归因分析标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
        # 顶部工具栏
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        
        # 归因模型选择
        toolbar_layout.addWidget(QLabel("归因模型:"))
        self.model_combo = QComboBox()
        self.model_combo.addItems([
            "首次触达（First Touch）",
            "末次触达（Last Touch）",
            "线性归因（Linear）",
            "时间衰减（Time Decay）",
            "位置加权（Position Based）"
        ])
        self.model_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px 12px;
                border-radius: 6px;
                min-width: 200px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
        """)
        toolbar_layout.addWidget(self.model_combo)
        
        # 日期范围
        toolbar_layout.addWidget(QLabel("开始日期:"))
        self.start_date = QDateEdit()
        self.start_date.setDate(QDate.currentDate().addDays(-30))
        self.start_date.setStyleSheet(f"""
            QDateEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px;
                border-radius: 6px;
            }}
        """)
        toolbar_layout.addWidget(self.start_date)
        
        toolbar_layout.addWidget(QLabel("结束日期:"))
        self.end_date = QDateEdit()
        self.end_date.setDate(QDate.currentDate())
        self.end_date.setStyleSheet(f"""
            QDateEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px;
                border-radius: 6px;
            }}
        """)
        toolbar_layout.addWidget(self.end_date)
        
        toolbar_layout.addStretch()
        
        # 分析按钮
        analyze_btn = QPushButton("🔍 执行分析")
        analyze_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #5558E3;
            }}
        """)
        analyze_btn.clicked.connect(self._run_attribution_analysis)
        toolbar_layout.addWidget(analyze_btn)
        
        # 导出按钮
        export_btn = QPushButton("📥 导出报告")
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 10px 24px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                border-color: {COLORS['primary']};
            }}
        """)
        toolbar_layout.addWidget(export_btn)
        
        layout.addWidget(toolbar)
        
        # 内容区域
        content_layout = QHBoxLayout()
        
        # 左侧：渠道贡献度图表
        left_panel = QFrame()
        left_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        left_layout = QVBoxLayout(left_panel)
        
        left_layout.addWidget(QLabel("<b>渠道归因贡献度</b>"))
        
        self.attribution_chart = AttributionChart()
        left_layout.addWidget(self.attribution_chart)
        
        # 摘要统计
        summary_frame = QFrame()
        summary_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_dark']};
                border-radius: 8px;
                padding: 12px;
                margin-top: 12px;
            }}
        """)
        summary_layout = QGridLayout(summary_frame)
        
        self.total_conversions_label = QLabel("总转化: 0")
        self.total_revenue_label = QLabel("总营收: ¥0")
        self.overall_roi_label = QLabel("整体ROI: 0%")
        self.avg_cpa_label = QLabel("平均CPA: ¥0")
        
        summary_layout.addWidget(self.total_conversions_label, 0, 0)
        summary_layout.addWidget(self.total_revenue_label, 0, 1)
        summary_layout.addWidget(self.overall_roi_label, 1, 0)
        summary_layout.addWidget(self.avg_cpa_label, 1, 1)
        
        left_layout.addWidget(summary_frame)
        
        content_layout.addWidget(left_panel, 1)
        
        # 右侧：渠道详情表格
        right_panel = QFrame()
        right_panel.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        right_layout = QVBoxLayout(right_panel)
        
        right_layout.addWidget(QLabel("<b>渠道归因详情</b>"))
        
        self.channel_table = QTableWidget()
        self.channel_table.setColumnCount(8)
        self.channel_table.setHorizontalHeaderLabels([
            "渠道", "类型", "归因转化", "归因营收", "成本", "ROI", "归因权重", "置信度"
        ])
        self.channel_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: none;
                border-radius: 8px;
                gridline-color: {COLORS['border']};
            }}
            QTableWidget::item {{
                padding: 8px;
            }}
            QHeaderView::section {{
                background-color: {COLORS['border']};
                color: {COLORS['text']};
                padding: 8px;
                border: none;
            }}
        """)
        self.channel_table.horizontalHeader().setStretchLastSection(True)
        self.channel_table.setAlternatingRowColors(True)
        self.channel_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        right_layout.addWidget(self.channel_table)
        
        content_layout.addWidget(right_panel, 1)
        
        layout.addLayout(content_layout, 1)
        
        # 优化建议
        suggestion_frame = QFrame()
        suggestion_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        suggestion_layout = QVBoxLayout(suggestion_frame)
        
        suggestion_layout.addWidget(QLabel("<b>💡 优化建议</b>"))
        
        self.suggestion_list = QListWidget()
        self.suggestion_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: none;
                border-radius: 8px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {COLORS['border']};
            }}
        """)
        suggestion_layout.addWidget(self.suggestion_list)
        
        layout.addWidget(suggestion_frame)
        
        return widget
    
    def _create_decision_tab(self) -> QWidget:
        """创建智能决策标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
        # 工具栏
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        
        # 决策类型过滤
        toolbar_layout.addWidget(QLabel("决策类型:"))
        self.decision_type_combo = QComboBox()
        self.decision_type_combo.addItems([
            "全部", "内容优化", "出价调整", "预算分配", 
            "库存决策", "活动启动", "人群扩展"
        ])
        self.decision_type_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px 12px;
                border-radius: 6px;
            }}
        """)
        toolbar_layout.addWidget(self.decision_type_combo)
        
        # 优先级过滤
        toolbar_layout.addWidget(QLabel("优先级:"))
        self.priority_combo = QComboBox()
        self.priority_combo.addItems(["全部", "P0-紧急", "P1-重要", "P2-常规", "P3-优化"])
        self.priority_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px 12px;
                border-radius: 6px;
            }}
        """)
        toolbar_layout.addWidget(self.priority_combo)
        
        toolbar_layout.addStretch()
        
        # 生成决策按钮
        generate_btn = QPushButton("🤖 AI生成决策")
        generate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #5558E3;
            }}
        """)
        generate_btn.clicked.connect(self._generate_decisions)
        toolbar_layout.addWidget(generate_btn)
        
        # 导出按钮
        export_btn = QPushButton("📥 导出")
        export_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 10px 24px;
                border-radius: 6px;
            }}
        """)
        toolbar_layout.addWidget(export_btn)
        
        layout.addWidget(toolbar)
        
        # 决策统计卡片
        stats_layout = QHBoxLayout()
        
        self.pending_card = self._create_stat_card("待执行", "0", COLORS['warning'])
        self.approved_card = self._create_stat_card("已批准", "0", COLORS['info'])
        self.executing_card = self._create_stat_card("执行中", "0", COLORS['secondary'])
        self.completed_card = self._create_stat_card("已完成", "0", COLORS['success'])
        
        stats_layout.addWidget(self.pending_card)
        stats_layout.addWidget(self.approved_card)
        stats_layout.addWidget(self.executing_card)
        stats_layout.addWidget(self.completed_card)
        
        layout.addLayout(stats_layout)
        
        # 决策列表
        content_layout = QHBoxLayout()
        
        # 决策列表
        list_frame = QFrame()
        list_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        list_layout = QVBoxLayout(list_frame)
        
        list_layout.addWidget(QLabel("<b>决策列表</b>"))
        
        self.decision_scroll = QScrollArea()
        self.decision_scroll.setWidgetResizable(True)
        self.decision_scroll.setStyleSheet(f"""
            QScrollArea {{
                background-color: {COLORS['bg_dark']};
                border: none;
                border-radius: 8px;
            }}
        """)
        
        self.decision_list_widget = QWidget()
        self.decision_list_layout = QVBoxLayout(self.decision_list_widget)
        self.decision_list_layout.setSpacing(8)
        self.decision_list_layout.addStretch()
        
        self.decision_scroll.setWidget(self.decision_list_widget)
        list_layout.addWidget(self.decision_scroll)
        
        content_layout.addWidget(list_frame, 2)
        
        # 决策详情
        detail_frame = QFrame()
        detail_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        detail_layout = QVBoxLayout(detail_frame)
        
        detail_layout.addWidget(QLabel("<b>决策详情</b>"))
        
        self.decision_detail = QTextEdit()
        self.decision_detail.setReadOnly(True)
        self.decision_detail.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: none;
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        detail_layout.addWidget(self.decision_detail)
        
        # 操作按钮
        action_layout = QHBoxLayout()
        
        approve_btn = QPushButton("✅ 批准")
        approve_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
            }}
        """)
        action_layout.addWidget(approve_btn)
        
        execute_btn = QPushButton("▶️ 执行")
        execute_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
            }}
        """)
        action_layout.addWidget(execute_btn)
        
        skip_btn = QPushButton("⏭️ 跳过")
        skip_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['gray']};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
            }}
        """)
        action_layout.addWidget(skip_btn)
        
        detail_layout.addLayout(action_layout)
        
        content_layout.addWidget(detail_frame, 1)
        
        layout.addLayout(content_layout, 1)
        
        return widget
    
    def _create_compare_tab(self) -> QWidget:
        """创建模型对比标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
        # 工具栏
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        
        toolbar_layout.addWidget(QLabel("分析时间段:"))
        date_range = QComboBox()
        date_range.addItems(["最近7天", "最近14天", "最近30天", "最近90天"])
        date_range.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px 12px;
                border-radius: 6px;
            }}
        """)
        toolbar_layout.addWidget(date_range)
        
        toolbar_layout.addStretch()
        
        compare_btn = QPushButton("📊 对比所有模型")
        compare_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-weight: bold;
            }}
        """)
        compare_btn.clicked.connect(self._compare_models)
        toolbar_layout.addWidget(compare_btn)
        
        layout.addWidget(toolbar)
        
        # 模型对比表格
        table_frame = QFrame()
        table_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        table_layout = QVBoxLayout(table_frame)
        
        table_layout.addWidget(QLabel("<b>各模型归因结果对比</b>"))
        
        self.compare_table = QTableWidget()
        self.compare_table.setColumnCount(6)
        self.compare_table.setHorizontalHeaderLabels([
            "归因模型", "总转化", "总营收", "总成本", "整体ROI", "建议"
        ])
        self.compare_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: none;
                border-radius: 8px;
                gridline-color: {COLORS['border']};
            }}
            QTableWidget::item {{
                padding: 10px;
            }}
            QHeaderView::section {{
                background-color: {COLORS['border']};
                color: {COLORS['text']};
                padding: 10px;
                border: none;
            }}
        """)
        self.compare_table.horizontalHeader().setStretchLastSection(True)
        self.compare_table.setAlternatingRowColors(True)
        table_layout.addWidget(self.compare_table)
        
        layout.addWidget(table_frame)
        
        # 说明
        note_frame = QFrame()
        note_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        note_layout = QVBoxLayout(note_frame)
        
        note_layout.addWidget(QLabel("<b>📖 模型说明</b>"))
        
        notes = QTextEdit()
        notes.setReadOnly(True)
        notes.setHtml("""
        <p><b>首次触达（First Touch）</b>：将100%转化价值归因给用户首次接触的渠道。适合强调认知漏斗顶端的品牌。</p>
        <p><b>末次触达（Last Touch）</b>：将100%转化价值归因给用户最后一次接触的渠道。适合高意图转化场景。</p>
        <p><b>线性归因（Linear）</b>：平均分配转化价值给所有触点。公平但不够精准。</p>
        <p><b>时间衰减（Time Decay）</b>：越接近转化的触点获得越高权重。适合长周期决策。</p>
        <p><b>位置加权（Position Based）</b>：首尾触点各获40%权重，中间触点均分剩余20%。兼顾认知和转化。</p>
        """)
        notes.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: none;
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        note_layout.addWidget(notes)
        
        layout.addWidget(note_frame)
        
        return widget
    
    def _create_report_tab(self) -> QWidget:
        """创建报告中心标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
        # 工具栏
        toolbar = QFrame()
        toolbar.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        toolbar_layout = QHBoxLayout(toolbar)
        
        toolbar_layout.addWidget(QLabel("报告类型:"))
        report_type = QComboBox()
        report_type.addItems(["归因分析报告", "智能决策报告", "综合分析报告"])
        report_type.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px 12px;
                border-radius: 6px;
            }}
        """)
        toolbar_layout.addWidget(report_type)
        
        toolbar_layout.addWidget(QLabel("时间范围:"))
        time_range = QComboBox()
        time_range.addItems(["本周", "本月", "本季度", "自定义"])
        time_range.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px 12px;
                border-radius: 6px;
            }}
        """)
        toolbar_layout.addWidget(time_range)
        
        toolbar_layout.addStretch()
        
        generate_report_btn = QPushButton("📄 生成报告")
        generate_report_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['primary']};
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-weight: bold;
            }}
        """)
        toolbar_layout.addWidget(generate_report_btn)
        
        export_report_btn = QPushButton("📥 导出PDF")
        export_report_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
            }}
        """)
        toolbar_layout.addWidget(export_report_btn)
        
        layout.addWidget(toolbar)
        
        # 报告预览
        preview_frame = QFrame()
        preview_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        preview_layout = QVBoxLayout(preview_frame)
        
        preview_layout.addWidget(QLabel("<b>报告预览</b>"))
        
        self.report_preview = QTextEdit()
        self.report_preview.setReadOnly(True)
        self.report_preview.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_dark']};
                color: {COLORS['text']};
                border: none;
                border-radius: 8px;
                padding: 16px;
                font-family: 'Consolas', monospace;
            }}
        """)
        self.report_preview.setHtml("""
        <h2>📊 ACAS Pro 高级数据分析报告</h2>
        <p>报告时间: 2026-04-30</p>
        <hr>
        <h3>一、归因分析摘要</h3>
        <p>• 分析周期: 2026-04-01 ~ 2026-04-30</p>
        <p>• 总转化数: 1,234</p>
        <p>• 总营收: ¥456,789</p>
        <p>• 整体ROI: 3.21</p>
        
        <h3>二、渠道贡献度排名</h3>
        <ol>
        <li>抖音付费 - 35.2%</li>
        <li>小红书 - 25.8%</li>
        <li>百度搜索 - 18.5%</li>
        <li>KOL合作 - 12.3%</li>
        <li>其他 - 8.2%</li>
        </ol>
        
        <h3>三、智能决策执行情况</h3>
        <p>• 待执行决策: 5个</p>
        <p>• 已完成决策: 12个</p>
        <p>• 平均完成率: 85%</p>
        <p>• 预期影响达成率: 78%</p>
        
        <h3>四、优化建议</h3>
        <p>1. 建议增加抖音付费广告预算15%，预计提升ROI 8%</p>
        <p>2. 减少百度搜索预算10%，转向小红书内容投放</p>
        <p>3. 关注即将到来的五一假期，提前3天启动预热</p>
        """)
        
        preview_layout.addWidget(self.report_preview)
        
        layout.addWidget(preview_frame)
        
        return widget
    
    def _create_stat_card(self, title: str, value: str, color: str) -> QFrame:
        """创建统计卡片"""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['bg_card']};
                border-radius: 8px;
                padding: 16px;
                border-left: 4px solid {color};
            }}
        """)
        
        layout = QVBoxLayout(card)
        
        title_label = QLabel(title)
        title_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
        layout.addWidget(title_label)
        
        value_label = QLabel(value)
        value_label.setObjectName("statValue")
        value_label.setStyleSheet(f"color: {color}; font-size: 28px; font-weight: bold;")
        layout.addWidget(value_label)
        
        return card
    
    def _update_stat_card(self, card: QFrame, value: str) -> None:
        """更新统计卡片值"""
        value_label = card.findChild(QLabel, "statValue")
        if value_label:
            value_label.setText(value)
    
    def _run_attribution_analysis(self) -> None:
        """执行归因分析"""
        # 模拟数据
        sample_data = {
            '抖音付费': random.uniform(20, 40),
            '小红书': random.uniform(15, 30),
            '百度搜索': random.uniform(10, 25),
            'KOL合作': random.uniform(8, 20),
            'B站': random.uniform(5, 15),
        }
        
        # 更新图表
        self.attribution_chart.set_data(sample_data)
        
        # 更新表格
        self.channel_table.setRowCount(len(sample_data))
        channels = list(sample_data.keys())
        for i, (channel, weight) in enumerate(sample_data.items()):
            self.channel_table.setItem(i, 0, QTableWidgetItem(channel))
            self.channel_table.setItem(i, 1, QTableWidgetItem("付费广告"))
            self.channel_table.setItem(i, 2, QTableWidgetItem(str(random.randint(100, 500))))
            self.channel_table.setItem(i, 3, QTableWidgetItem(f"¥{random.randint(10000, 50000)}"))
            self.channel_table.setItem(i, 4, QTableWidgetItem(f"¥{random.randint(1000, 5000)}"))
            self.channel_table.setItem(i, 5, QTableWidgetItem(f"{random.uniform(2, 5):.2f}"))
            self.channel_table.setItem(i, 6, QTableWidgetItem(f"{weight:.1f}%"))
            self.channel_table.setItem(i, 7, QTableWidgetItem(f"{random.uniform(70, 95):.0f}%"))
        
        # 更新摘要
        self.total_conversions_label.setText(f"总转化: {random.randint(500, 1000)}")
        self.total_revenue_label.setText(f"总营收: ¥{random.randint(100000, 500000)}")
        self.overall_roi_label.setText(f"整体ROI: {random.uniform(2.5, 4.0):.2f}")
        self.avg_cpa_label.setText(f"平均CPA: ¥{random.randint(30, 80)}")
        
        # 更新建议
        self.suggestion_list.clear()
        suggestions = [
            "建议加大对抖音付费渠道的投入，当前贡献度达35%",
            "小红书渠道ROI表现优异，建议增加内容产出",
            "KOL合作效果稳定，可考虑扩大合作规模",
            "百度搜索成本偏高，建议优化关键词策略"
        ]
        for suggestion in suggestions:
            self.suggestion_list.addItem(suggestion)
    
    def _generate_decisions(self) -> None:
        """生成智能决策"""
        # 清空现有决策
        for i in reversed(range(self.decision_list_layout.count() - 1)):
            widget = self.decision_list_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()
        
        # 生成模拟决策
        sample_decisions = [
            {
                'priority': 'P0',
                'type': '出价调整',
                'title': '抖音广告CPA过高需优化',
                'description': '当前CPA 85元，超过目标50元的70%，需立即优化',
                'status': 'pending',
                'current_value': 85,
                'target_value': 50,
                'expected_impact': -0.4,
                'confidence': 0.85,
                'related_channels': ['抖音', '快手']
            },
            {
                'priority': 'P1',
                'type': '内容优化',
                'title': '提升小红书内容互动率',
                'description': '当前互动率2.1%，低于目标3%，需优化内容策略',
                'status': 'pending',
                'current_value': 2.1,
                'target_value': 3.0,
                'expected_impact': 0.02,
                'confidence': 0.78,
                'related_channels': ['小红书']
            },
            {
                'priority': 'P1',
                'type': '预算分配',
                'title': '调整渠道预算分配',
                'description': '百度ROI持续走低，建议减少20%预算转投抖音',
                'status': 'pending',
                'current_value': 1.2,
                'target_value': 2.0,
                'expected_impact': 0.3,
                'confidence': 0.75,
                'related_channels': ['百度', '抖音']
            },
            {
                'priority': 'P2',
                'type': '活动启动',
                'title': '五一促销准备',
                'description': '距离五一还有5天，需启动预热和活动配置',
                'status': 'pending',
                'current_value': 0,
                'target_value': 500000,
                'expected_impact': 0.5,
                'confidence': 0.90,
                'related_channels': ['抖音', '小红书', '淘宝']
            },
            {
                'priority': 'P2',
                'type': '人群扩展',
                'title': '测试新受众群体',
                'description': '发现25-30岁女性群体潜在机会，建议小规模测试',
                'status': 'pending',
                'current_value': 0.6,
                'target_value': 0.8,
                'expected_impact': 0.15,
                'confidence': 0.65,
                'related_channels': ['抖音']
            },
        ]
        
        for decision in sample_decisions:
            card = DecisionCard(decision)
            self.decision_list_layout.insertWidget(
                self.decision_list_layout.count() - 1, card
            )
        
        # 更新统计
        self._update_stat_card(self.pending_card, str(len(sample_decisions)))
        self._update_stat_card(self.approved_card, "0")
        self._update_stat_card(self.executing_card, "0")
        self._update_stat_card(self.completed_card, "0")
    
    def _compare_models(self) -> None:
        """对比归因模型"""
        models = [
            "首次触达（First Touch）",
            "末次触达（Last Touch）",
            "线性归因（Linear）",
            "时间衰减（Time Decay）",
            "位置加权（Position Based）"
        ]
        
        self.compare_table.setRowCount(len(models))
        
        for i, model in enumerate(models):
            self.compare_table.setItem(i, 0, QTableWidgetItem(model))
            self.compare_table.setItem(i, 1, QTableWidgetItem(str(random.randint(400, 600))))
            self.compare_table.setItem(i, 2, QTableWidgetItem(f"¥{random.randint(200000, 400000)}"))
            self.compare_table.setItem(i, 3, QTableWidgetItem(f"¥{random.randint(50000, 100000)}"))
            self.compare_table.setItem(i, 4, QTableWidgetItem(f"{random.uniform(2.5, 4.5):.2f}"))
            
            suggestion = random.choice([
                "推荐使用此模型",
                "适合品牌认知场景",
                "适合效果广告场景",
                "平衡型模型",
                "兼顾首尾触点"
            ])
            self.compare_table.setItem(i, 5, QTableWidgetItem(suggestion))
    
    def refresh_data(self) -> None:
        """刷新数据"""
        pass
