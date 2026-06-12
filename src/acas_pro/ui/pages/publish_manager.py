#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Publish Manager Page
多平台发布管理页面
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGridLayout,
    QScrollArea,
    QComboBox,
    QLineEdit,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QMessageBox,
    QCheckBox,
    QDateTimeEdit,
    QTabWidget,
)
from PySide6.QtCore import Qt, QDateTime
from PySide6.QtGui import QFont

from ...core.config import config
from ...core.logging import get_logger
from ...publisher.publish_manager import PublishManager, PublishStatus, ContentType
from ...publisher.scheduler import PublishScheduler

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


class PublishManagerPage(QWidget):
    """发布管理页面"""

    def __init__(self):
        super().__init__()
        self.publish_manager = PublishManager()
        self.scheduler = PublishScheduler(self.publish_manager)
        self.scheduler.start()
        self._setup_ui()
        self._load_tasks()

    def __del__(self) -> None:
        self.scheduler.stop()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # 标题
        title = QLabel("多平台发布管理")
        title.setFont(QFont(config.ui.font_family, 24, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(title)

        subtitle = QLabel("一键分发到多个平台，智能排期优化")
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

        # 发布任务
        tasks_widget = self._create_tasks_tab()
        tabs.addTab(tasks_widget, "📋 发布任务")

        # 新建发布
        new_widget = self._create_new_tab()
        tabs.addTab(new_widget, "➕ 新建发布")

        # 排期管理
        schedule_widget = self._create_schedule_tab()
        tabs.addTab(schedule_widget, "📅 排期管理")

        layout.addWidget(tabs)

    def _create_tasks_tab(self) -> QWidget:
        """创建任务列表标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # 工具栏
        toolbar = QHBoxLayout()

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 8px 16px;
                border-radius: 6px;
            }}
        """)
        refresh_btn.clicked.connect(self._load_tasks)
        toolbar.addWidget(refresh_btn)

        toolbar.addStretch()

        # 状态筛选
        status_label = QLabel("状态:")
        status_label.setStyleSheet(f"color: {COLORS['text']};")
        toolbar.addWidget(status_label)

        self.status_filter = QComboBox()
        self.status_filter.addItems(
            ["全部", "待发布", "已排期", "发布中", "已发布", "失败"]
        )
        self.status_filter.currentTextChanged.connect(self._filter_tasks)
        self.status_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 8px;
                border-radius: 6px;
            }}
        """)
        toolbar.addWidget(self.status_filter)

        layout.addLayout(toolbar)

        # 任务列表
        self.tasks_list = QListWidget()
        self.tasks_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 8px;
                padding: 8px;
            }}
            QListWidget::item {{
                background-color: {COLORS["card"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 8px;
                padding: 12px;
                margin: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {COLORS["accent"]};
                border-color: {COLORS["accent"]};
            }}
        """)
        layout.addWidget(self.tasks_list)

        return widget

    def _create_new_tab(self) -> QWidget:
        """创建新建发布标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)

        # 内容文件
        file_layout = QHBoxLayout()
        self.file_path = QLineEdit()
        self.file_path.setPlaceholderText("选择要发布的视频或图片...")
        self.file_path.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 10px;
                border-radius: 6px;
            }}
        """)
        file_layout.addWidget(self.file_path)

        browse_btn = QPushButton("浏览...")
        browse_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 10px 16px;
                border-radius: 6px;
            }}
        """)
        browse_btn.clicked.connect(self._browse_file)
        file_layout.addWidget(browse_btn)

        content_layout.addLayout(file_layout)

        # 标题
        title_label = QLabel("标题")
        title_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold;")
        content_layout.addWidget(title_label)

        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("输入内容标题...")
        self.title_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 10px;
                border-radius: 6px;
            }}
        """)
        content_layout.addWidget(self.title_input)

        # 描述
        desc_label = QLabel("描述")
        desc_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold;")
        content_layout.addWidget(desc_label)

        self.desc_input = QTextEdit()
        self.desc_input.setPlaceholderText("输入内容描述...")
        self.desc_input.setMaximumHeight(100)
        self.desc_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 6px;
                padding: 10px;
            }}
        """)
        content_layout.addWidget(self.desc_input)

        # 标签
        tags_label = QLabel("标签 (用空格分隔)")
        tags_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold;")
        content_layout.addWidget(tags_label)

        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("例如: 美食 探店 推荐")
        self.tags_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 10px;
                border-radius: 6px;
            }}
        """)
        content_layout.addWidget(self.tags_input)

        # 平台选择
        platforms_label = QLabel("选择发布平台")
        platforms_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold;")
        content_layout.addWidget(platforms_label)

        platforms_grid = QGridLayout()
        self.platform_checks = {}
        platforms = [
            ("douyin", "抖音"),
            ("xiaohongshu", "小红书"),
            ("kuaishou", "快手"),
            ("bilibili", "B站"),
            ("tiktok", "TikTok"),
            ("instagram", "Instagram"),
            ("youtube", "YouTube"),
        ]

        for i, (key, name) in enumerate(platforms):
            checkbox = QCheckBox(name)
            checkbox.setStyleSheet(f"color: {COLORS['text']}; padding: 8px;")
            platforms_grid.addWidget(checkbox, i // 3, i % 3)
            self.platform_checks[key] = checkbox

        content_layout.addLayout(platforms_grid)

        # 发布时间
        time_layout = QHBoxLayout()

        immediate_checkbox = QCheckBox("立即发布")
        immediate_checkbox.setChecked(True)
        immediate_checkbox.setStyleSheet(f"color: {COLORS['text']}; padding: 8px;")
        time_layout.addWidget(immediate_checkbox)

        time_layout.addStretch()

        time_label = QLabel("或选择时间:")
        time_label.setStyleSheet(f"color: {COLORS['text2']};")
        time_layout.addWidget(time_label)

        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.datetime_edit.setEnabled(False)
        self.datetime_edit.setStyleSheet(f"""
            QDateTimeEdit {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 8px;
                border-radius: 6px;
            }}
        """)
        time_layout.addWidget(self.datetime_edit)

        immediate_checkbox.toggled.connect(
            lambda checked: self.datetime_edit.setEnabled(not checked)
        )

        content_layout.addLayout(time_layout)

        content_layout.addStretch()

        # 提交按钮
        submit_btn = QPushButton("🚀 创建发布任务")
        submit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        submit_btn.clicked.connect(self._create_task)
        content_layout.addWidget(submit_btn)

        scroll.setWidget(content)
        layout.addWidget(scroll)

        return widget

    def _create_schedule_tab(self) -> QWidget:
        """创建排期管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # 状态卡片
        status_card = QFrame()
        status_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        status_layout = QHBoxLayout(status_card)

        status = self.scheduler.get_queue_status()

        pending_label = QLabel(f"⏳ 待发布: {status['pending']}")
        pending_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px;")
        status_layout.addWidget(pending_label)

        scheduled_label = QLabel(f"📅 已排期: {status['scheduled']}")
        scheduled_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 16px;")
        status_layout.addWidget(scheduled_label)

        status_layout.addStretch()

        layout.addWidget(status_card)

        # 批量排期按钮
        batch_btn = QPushButton("📅 批量智能排期")
        batch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["success"]};
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        batch_btn.clicked.connect(self._batch_schedule)
        layout.addWidget(batch_btn)

        layout.addStretch()

        return widget

    def _load_tasks(self) -> None:
        """加载任务列表"""
        self.tasks_list.clear()
        tasks = self.publish_manager.list_tasks(limit=50)

        status_icons = {
            PublishStatus.PENDING: "⏳",
            PublishStatus.SCHEDULED: "📅",
            PublishStatus.PUBLISHING: "🚀",
            PublishStatus.PUBLISHED: "✅",
            PublishStatus.FAILED: "❌",
            PublishStatus.CANCELLED: "🚫",
        }

        platform_names = {
            "douyin": "抖音",
            "xiaohongshu": "小红书",
            "kuaishou": "快手",
            "bilibili": "B站",
            "tiktok": "TikTok",
            "instagram": "Instagram",
            "youtube": "YouTube",
        }

        for task in tasks:
            item = QListWidgetItem()

            icon = status_icons.get(task.status, "⏳")
            platforms_str = ", ".join(
                [platform_names.get(p.platform, p.platform) for p in task.platforms[:3]]
            )
            if len(task.platforms) > 3:
                platforms_str += f" 等{len(task.platforms)}个平台"

            text = f"{icon} {task.title}\n   平台: {platforms_str} | 状态: {task.status.value}"
            if task.scheduled_time:
                text += (
                    f"\n   计划时间: {task.scheduled_time.strftime('%Y-%m-%d %H:%M')}"
                )

            item.setText(text)
            item.setData(Qt.UserRole, task.id)
            self.tasks_list.addItem(item)

    def _filter_tasks(self) -> None:
        """筛选任务"""
        status_map = {
            "全部": None,
            "待发布": PublishStatus.PENDING,
            "已排期": PublishStatus.SCHEDULED,
            "发布中": PublishStatus.PUBLISHING,
            "已发布": PublishStatus.PUBLISHED,
            "失败": PublishStatus.FAILED,
        }

        status_text = self.status_filter.currentText()
        status = status_map.get(status_text)

        self.tasks_list.clear()
        tasks = self.publish_manager.list_tasks(status=status, limit=50)

        # 复用_load_tasks中的显示逻辑
        self._display_tasks(tasks)

    def _display_tasks(self, tasks) -> None:
        """显示任务列表"""
        status_icons = {
            PublishStatus.PENDING: "⏳",
            PublishStatus.SCHEDULED: "📅",
            PublishStatus.PUBLISHING: "🚀",
            PublishStatus.PUBLISHED: "✅",
            PublishStatus.FAILED: "❌",
            PublishStatus.CANCELLED: "🚫",
        }

        platform_names = {
            "douyin": "抖音",
            "xiaohongshu": "小红书",
            "kuaishou": "快手",
            "bilibili": "B站",
            "tiktok": "TikTok",
            "instagram": "Instagram",
            "youtube": "YouTube",
        }

        for task in tasks:
            item = QListWidgetItem()

            icon = status_icons.get(task.status, "⏳")
            platforms_str = ", ".join(
                [platform_names.get(p.platform, p.platform) for p in task.platforms[:3]]
            )
            if len(task.platforms) > 3:
                platforms_str += f" 等{len(task.platforms)}个平台"

            text = f"{icon} {task.title}\n   平台: {platforms_str} | 状态: {task.status.value}"
            if task.scheduled_time:
                text += (
                    f"\n   计划时间: {task.scheduled_time.strftime('%Y-%m-%d %H:%M')}"
                )

            item.setText(text)
            item.setData(Qt.UserRole, task.id)
            self.tasks_list.addItem(item)

    def _browse_file(self) -> None:
        """浏览文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择要发布的文件",
            "",
            "视频/图片文件 (*.mp4 *.mov *.avi *.jpg *.jpeg *.png *.webp)",
        )
        if file_path:
            self.file_path.setText(file_path)

    def _create_task(self) -> None:
        """创建发布任务"""
        file_path = self.file_path.text().strip()
        title = self.title_input.text().strip()
        description = self.desc_input.toPlainText().strip()
        tags_text = self.tags_input.text().strip()

        if not file_path:
            QMessageBox.warning(self, "提示", "请选择要发布的文件")
            return

        if not title:
            QMessageBox.warning(self, "提示", "请输入标题")
            return

        # 获取选中的平台
        platforms = []
        for key, checkbox in self.platform_checks.items():
            if checkbox.isChecked():
                platforms.append(key)

        if not platforms:
            QMessageBox.warning(self, "提示", "请至少选择一个发布平台")
            return

        # 解析标签
        tags = [t.strip() for t in tags_text.split() if t.strip()]

        # 获取发布时间
        scheduled_time = None
        if self.datetime_edit.isEnabled():
            scheduled_time = self.datetime_edit.dateTime().toPython()

        # 创建任务
        task = self.publish_manager.create_task(
            content_path=file_path,
            content_type=ContentType.VIDEO,
            title=title,
            description=description,
            tags=tags,
            platforms=platforms,
            scheduled_time=scheduled_time,
        )

        # 立即发布或排期
        if scheduled_time is None:
            self.publish_manager.publish(task.id, immediate=True)
            QMessageBox.information(self, "成功", "发布任务已创建并执行！")
        else:
            QMessageBox.information(
                self,
                "成功",
                f"发布任务已排期: {scheduled_time.strftime('%Y-%m-%d %H:%M')}",
            )

        self._load_tasks()

    def _batch_schedule(self) -> None:
        """批量智能排期"""
        QMessageBox.information(self, "提示", "批量排期功能开发中...")
