#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Content Creation Page
内容创作页面
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QTextEdit,
    QComboBox,
    QTabWidget,
    QScrollArea,
    QMessageBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ...core.config import config
from ...core.logging import get_logger
from ...content.trend_monitor import TrendMonitor, Platform as TrendPlatform
from ...content.script_generator import ScriptGenerator, ContentStyle, Platform

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


class TrendItemCard(QFrame):
    """热点内容卡片"""

    def __init__(self, trend_item, parent=None):
        super().__init__(parent)
        self.item = trend_item
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 8px;
                padding: 12px;
            }}
            QFrame:hover {{
                border-color: {COLORS["accent"]};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # 标题
        title = QLabel(
            self.item.title[:50] + "..."
            if len(self.item.title) > 50
            else self.item.title
        )
        title.setFont(QFont(config.ui.font_family, 13, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text']};")
        title.setWordWrap(True)
        layout.addWidget(title)

        # 作者和平台
        meta = QLabel(f"@{self.item.author} · {self.item.platform.value}")
        meta.setStyleSheet(f"color: {COLORS['text2']}; font-size: 12px;")
        layout.addWidget(meta)

        # 数据指标
        stats = QHBoxLayout()
        stats.setSpacing(16)

        for label, value, color in [
            ("👁", f"{self.item.views / 10000:.1f}万", COLORS["text"]),
            ("❤️", f"{self.item.likes / 1000:.1f}k", COLORS["danger"]),
            ("💬", str(self.item.comments), COLORS["text2"]),
            ("🔥", f"{self.item.viral_score:.0f}", COLORS["warning"]),
        ]:
            stat = QLabel(f"{label} {value}")
            stat.setStyleSheet(f"color: {color}; font-size: 12px;")
            stats.addWidget(stat)

        stats.addStretch()
        layout.addLayout(stats)

        # 操作按钮
        btn_row = QHBoxLayout()

        analyze_btn = QPushButton("📊 分析")
        analyze_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["card"]};
                color: {COLORS["accent"]};
                border: 1px solid {COLORS["border"]};
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }}
        """)
        btn_row.addWidget(analyze_btn)

        use_btn = QPushButton("✨ 参考创作")
        use_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }}
        """)
        btn_row.addWidget(use_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)


class ContentCreationPage(QWidget):
    """内容创作页面"""

    def __init__(self):
        super().__init__()
        self.trend_monitor = TrendMonitor()
        self.script_generator = ScriptGenerator()
        self._setup_ui()

        # 启动趋势监测
        self.trend_monitor.start_monitoring()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # 标题
        title = QLabel("内容创作中心")
        title.setFont(QFont(config.ui.font_family, 24, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(title)

        subtitle = QLabel("AI驱动的智能内容创作与热点追踪")
        subtitle.setStyleSheet(f"color: {COLORS['text2']}; font-size: 14px;")
        layout.addWidget(subtitle)

        layout.addSpacing(16)

        # 标签页
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS["border"]};
                border-radius: 8px;
                background-color: {COLORS["bg"]};
            }}
            QTabBar::tab {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text2"]};
                padding: 12px 24px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS["accent"]};
                color: white;
            }}
        """)

        # 热点监测标签
        trend_widget = self._create_trend_tab()
        tabs.addTab(trend_widget, "🔥 热点监测")

        # AI文案生成标签
        script_widget = self._create_script_tab()
        tabs.addTab(script_widget, "✍️ AI文案生成")

        # 视频制作标签
        video_widget = self._create_video_tab()
        tabs.addTab(video_widget, "🎬 视频制作")

        layout.addWidget(tabs)

    def _create_trend_tab(self) -> QWidget:
        """创建热点监测标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 筛选栏
        filter_row = QHBoxLayout()

        platform_label = QLabel("平台:")
        platform_label.setStyleSheet(f"color: {COLORS['text']};")
        filter_row.addWidget(platform_label)

        self.platform_combo = QComboBox()
        self.platform_combo.addItems(["全部", "抖音", "小红书", "快手", "B站"])
        self.platform_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 8px;
                border-radius: 6px;
                min-width: 120px;
            }}
        """)
        filter_row.addWidget(self.platform_combo)

        filter_row.addSpacing(20)

        score_label = QLabel("爆款指数:")
        score_label.setStyleSheet(f"color: {COLORS['text']};")
        filter_row.addWidget(score_label)

        self.score_combo = QComboBox()
        self.score_combo.addItems(["全部", "≥50", "≥70", "≥90"])
        self.score_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 8px;
                border-radius: 6px;
                min-width: 100px;
            }}
        """)
        filter_row.addWidget(self.score_combo)

        filter_row.addStretch()

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 6px;
            }}
        """)
        refresh_btn.clicked.connect(self._refresh_trends)
        filter_row.addWidget(refresh_btn)

        layout.addLayout(filter_row)

        # 热点列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        self.trend_container = QWidget()
        self.trend_layout = QVBoxLayout(self.trend_container)
        self.trend_layout.setContentsMargins(0, 0, 0, 0)
        self.trend_layout.setSpacing(12)
        self.trend_layout.addStretch()

        scroll.setWidget(self.trend_container)
        layout.addWidget(scroll)

        # 初始加载
        self._refresh_trends()

        return widget

    def _create_script_tab(self) -> QWidget:
        """创建AI文案生成标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 输入区域
        input_frame = QFrame()
        input_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        input_layout = QVBoxLayout(input_frame)

        input_label = QLabel("输入产品信息或创意方向:")
        input_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px;")
        input_layout.addWidget(input_label)

        self.script_input = QTextEdit()
        self.script_input.setPlaceholderText(
            "例如: 黑茶，降脂养胃，适合西北及中东市场..."
        )
        self.script_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS["bg"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                min-height: 100px;
            }}
        """)
        input_layout.addWidget(self.script_input)

        # 选项行
        options_row = QHBoxLayout()

        # 平台选择
        platform_label = QLabel("目标平台:")
        platform_label.setStyleSheet(f"color: {COLORS['text']};")
        options_row.addWidget(platform_label)

        self.script_platform = QComboBox()
        self.script_platform.addItems(["抖音", "小红书", "快手", "B站"])
        self.script_platform.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS["bg"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 6px;
                border-radius: 6px;
            }}
        """)
        options_row.addWidget(self.script_platform)

        options_row.addSpacing(20)

        # 风格选择
        style_label = QLabel("内容风格:")
        style_label.setStyleSheet(f"color: {COLORS['text']};")
        options_row.addWidget(style_label)

        self.script_style = QComboBox()
        self.script_style.addItems(["口播", "种草", "知识", "剧情", "情感", "促销"])
        self.script_style.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS["bg"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 6px;
                border-radius: 6px;
            }}
        """)
        options_row.addWidget(self.script_style)

        options_row.addStretch()

        # 生成按钮
        generate_btn = QPushButton("✨ 生成文案")
        generate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #79b8ff;
            }}
        """)
        generate_btn.clicked.connect(self._generate_script)
        options_row.addWidget(generate_btn)

        input_layout.addLayout(options_row)
        layout.addWidget(input_frame)

        # 输出区域
        output_label = QLabel("生成结果:")
        output_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px;")
        layout.addWidget(output_label)

        self.script_output = QTextEdit()
        self.script_output.setReadOnly(True)
        self.script_output.setPlaceholderText("生成的文案将显示在这里...")
        self.script_output.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }}
        """)
        layout.addWidget(self.script_output)

        # 操作按钮
        btn_row = QHBoxLayout()

        copy_btn = QPushButton("📋 复制")
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["card"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 8px 16px;
                border-radius: 6px;
            }}
        """)
        copy_btn.clicked.connect(self._copy_script)
        btn_row.addWidget(copy_btn)

        save_btn = QPushButton("💾 保存")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["card"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 8px 16px;
                border-radius: 6px;
            }}
        """)
        btn_row.addWidget(save_btn)

        btn_row.addStretch()

        layout.addLayout(btn_row)
        layout.addStretch()

        return widget

    def _create_video_tab(self) -> QWidget:
        """创建视频制作标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        placeholder = QLabel("🎬 智能视频制作功能开发中...")
        placeholder.setStyleSheet(f"color: {COLORS['text2']}; font-size: 16px;")
        placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(placeholder)

        layout.addStretch()
        return widget

    def _refresh_trends(self) -> None:
        """刷新热点列表"""
        # 清空现有列表
        while self.trend_layout.count() > 1:
            item = self.trend_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 获取热点数据
        platform_map = {
            "全部": None,
            "抖音": TrendPlatform.DOUYIN,
            "小红书": TrendPlatform.XIAOHONGSHU,
            "快手": TrendPlatform.KUAISHOU,
            "B站": TrendPlatform.BILIBILI,
        }

        platform = platform_map.get(self.platform_combo.currentText())

        score_map = {
            "全部": 0,
            "≥50": 50,
            "≥70": 70,
            "≥90": 90,
        }
        min_score = score_map.get(self.score_combo.currentText(), 0)

        try:
            items = self.trend_monitor.get_trending_items(
                platform=platform, min_viral_score=min_score, limit=20
            )

            for item in items:
                card = TrendItemCard(item)
                self.trend_layout.insertWidget(self.trend_layout.count() - 1, card)

        except Exception as e:
            logger.error(f"Failed to load trends: {e}")
            error_label = QLabel("加载热点数据失败，请稍后重试")
            error_label.setStyleSheet(f"color: {COLORS['danger']};")
            self.trend_layout.insertWidget(0, error_label)

    def _generate_script(self) -> None:
        """生成文案"""
        input_text = self.script_input.toPlainText().strip()
        if not input_text:
            QMessageBox.warning(self, "输入错误", "请输入产品信息或创意方向")
            return

        # 映射选择
        platform_map = {
            "抖音": Platform.DOUYIN,
            "小红书": Platform.XIAOHONGSHU,
            "快手": Platform.KUAISHOU,
            "B站": Platform.BILIBILI,
        }

        style_map = {
            "口播": ContentStyle.BROADCAST,
            "种草": ContentStyle.SEEDING,
            "知识": ContentStyle.KNOWLEDGE,
            "剧情": ContentStyle.DRAMA,
            "情感": ContentStyle.EMOTIONAL,
            "促销": ContentStyle.PROMOTION,
        }

        platform = platform_map.get(self.script_platform.currentText(), Platform.DOUYIN)
        style = style_map.get(self.script_style.currentText(), ContentStyle.BROADCAST)

        try:
            script = self.script_generator.generate(
                input_text=input_text, platform=platform, style=style
            )

            # 显示结果
            result = f"""
【标题】
{script.title}

【正文】
{script.content}

【标签】
{" ".join(script.hashtags)}

【行动号召】
{script.cta}

【字数】{script.word_count} 字
            """.strip()

            self.script_output.setText(result)

        except Exception as e:
            logger.error(f"Failed to generate script: {e}")
            QMessageBox.critical(self, "生成失败", f"文案生成失败: {e}")

    def _copy_script(self) -> None:
        """复制文案到剪贴板"""
        from PySide6.QtWidgets import QApplication

        text = self.script_output.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            QMessageBox.information(self, "复制成功", "文案已复制到剪贴板")
