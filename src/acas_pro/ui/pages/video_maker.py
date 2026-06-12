#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Video Maker Page
智能视频制作页面
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QComboBox,
    QLineEdit,
    QTextEdit,
    QListWidget,
    QListWidgetItem,
    QFileDialog,
    QMessageBox,
    QProgressBar,
    QTabWidget,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont

from ...core.config import config
from ...core.logging import get_logger
from ...video.video_maker import VideoMaker, VideoStatus
from ...video.voice_synthesis import VoiceSynthesizer

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


class RenderThread(QThread):
    """渲染线程"""

    progress = Signal(int)
    finished = Signal(str)
    error = Signal(str)

    def __init__(self, video_maker, project_id):
        super().__init__()
        self.video_maker = video_maker
        self.project_id = project_id

    def run(self) -> None:
        try:
            for i in range(0, 101, 10):
                self.progress.emit(i)
                self.msleep(200)

            output_path = self.video_maker.render_project(self.project_id)

            if output_path:
                self.finished.emit(output_path)
            else:
                self.error.emit("渲染失败")

        except Exception as e:
            logger.exception(f"Error in run: {e}")
            self.error.emit(str(e))


class VideoMakerPage(QWidget):
    """视频制作页面"""

    def __init__(self):
        super().__init__()
        self.video_maker = VideoMaker()
        self.voice_synthesizer = VoiceSynthesizer()
        self.current_project = None
        self.materials = []
        self._setup_ui()
        self._load_projects()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # 标题
        title = QLabel("智能视频制作")
        title.setFont(QFont(config.ui.font_family, 24, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(title)

        subtitle = QLabel("AI混剪、配音、字幕一站式视频制作")
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

        # 项目管理
        projects_widget = self._create_projects_tab()
        tabs.addTab(projects_widget, "📁 项目")

        # 素材管理
        materials_widget = self._create_materials_tab()
        tabs.addTab(materials_widget, "🎬 素材")

        # 智能剪辑
        editor_widget = self._create_editor_tab()
        tabs.addTab(editor_widget, "✂️ 剪辑")

        # AI配音
        voice_widget = self._create_voice_tab()
        tabs.addTab(voice_widget, "🎙 配音")

        layout.addWidget(tabs)

    def _create_projects_tab(self) -> QWidget:
        """创建项目标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # 工具栏
        toolbar = QHBoxLayout()

        new_btn = QPushButton("➕ 新建项目")
        new_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                font-weight: bold;
            }}
        """)
        new_btn.clicked.connect(self._create_new_project)
        toolbar.addWidget(new_btn)

        toolbar.addStretch()

        # 平台筛选
        platform_label = QLabel("平台:")
        platform_label.setStyleSheet(f"color: {COLORS['text']};")
        toolbar.addWidget(platform_label)

        self.platform_filter = QComboBox()
        self.platform_filter.addItems(
            ["全部", "抖音", "小红书", "快手", "B站", "TikTok"]
        )
        self.platform_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 8px;
                border-radius: 6px;
            }}
        """)
        toolbar.addWidget(self.platform_filter)

        layout.addLayout(toolbar)

        # 项目列表
        self.projects_list = QListWidget()
        self.projects_list.setStyleSheet(f"""
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
        layout.addWidget(self.projects_list)

        return widget

    def _create_materials_tab(self) -> QWidget:
        """创建素材标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # 工具栏
        toolbar = QHBoxLayout()

        import_btn = QPushButton("📥 导入素材")
        import_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
            }}
        """)
        import_btn.clicked.connect(self._import_materials)
        toolbar.addWidget(import_btn)

        toolbar.addStretch()

        layout.addLayout(toolbar)

        # 素材列表
        self.materials_list = QListWidget()
        self.materials_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 8px;
                padding: 8px;
            }}
        """)
        layout.addWidget(self.materials_list)

        return widget

    def _create_editor_tab(self) -> QWidget:
        """创建剪辑标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # 项目信息
        info_card = QFrame()
        info_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 12px;
                padding: 16px;
            }}
        """)
        info_layout = QVBoxLayout(info_card)

        self.project_name_label = QLabel("未选择项目")
        self.project_name_label.setFont(QFont(config.ui.font_family, 16, QFont.Bold))
        self.project_name_label.setStyleSheet(f"color: {COLORS['text']};")
        info_layout.addWidget(self.project_name_label)

        self.project_info_label = QLabel("请先在项目标签页选择一个项目")
        self.project_info_label.setStyleSheet(f"color: {COLORS['text2']};")
        info_layout.addWidget(self.project_info_label)

        layout.addWidget(info_card)

        # 自动剪辑按钮
        auto_edit_btn = QPushButton("🤖 智能自动剪辑")
        auto_edit_btn.setStyleSheet(f"""
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
        auto_edit_btn.clicked.connect(self._auto_edit)
        layout.addWidget(auto_edit_btn)

        # 渲染按钮
        render_btn = QPushButton("🎬 渲染视频")
        render_btn.setStyleSheet(f"""
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
        render_btn.clicked.connect(self._render_video)
        layout.addWidget(render_btn)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 8px;
                padding: 4px;
                text-align: center;
            }}
            QProgressBar::chunk {{
                background-color: {COLORS["accent"]};
                border-radius: 4px;
            }}
        """)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        layout.addStretch()

        return widget

    def _create_voice_tab(self) -> QWidget:
        """创建配音标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 20, 20, 20)

        # 文本输入
        text_label = QLabel("文案内容")
        text_label.setStyleSheet(f"color: {COLORS['text']}; font-weight: bold;")
        layout.addWidget(text_label)

        self.voice_text = QTextEdit()
        self.voice_text.setPlaceholderText("输入要转换为语音的文案...")
        self.voice_text.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }}
        """)
        self.voice_text.setMinimumHeight(150)
        layout.addWidget(self.voice_text)

        # 声音选择
        voice_layout = QHBoxLayout()

        voice_label = QLabel("选择声音:")
        voice_label.setStyleSheet(f"color: {COLORS['text']};")
        voice_layout.addWidget(voice_label)

        self.voice_selector = QComboBox()
        voices = self.voice_synthesizer.list_voices()
        for voice in voices:
            self.voice_selector.addItem(f"{voice.name} - {voice.description}", voice.id)
        self.voice_selector.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 8px;
                border-radius: 6px;
                min-width: 200px;
            }}
        """)
        voice_layout.addWidget(self.voice_selector)

        voice_layout.addStretch()
        layout.addLayout(voice_layout)

        # 生成按钮
        generate_btn = QPushButton("🎙 生成配音")
        generate_btn.setStyleSheet(f"""
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
        generate_btn.clicked.connect(self._generate_voice)
        layout.addWidget(generate_btn)

        layout.addStretch()

        return widget

    def _load_projects(self) -> None:
        """加载项目列表"""
        self.projects_list.clear()
        projects = self.video_maker.list_projects(limit=20)

        for project in projects:
            item = QListWidgetItem()

            platform_names = {
                "douyin": "抖音",
                "xiaohongshu": "小红书",
                "kuaishou": "快手",
                "bilibili": "B站",
                "tiktok": "TikTok",
            }
            platform_name = platform_names.get(
                project.target_platform, project.target_platform
            )

            status_icons = {
                VideoStatus.DRAFT: "📝",
                VideoStatus.RENDERING: "⏳",
                VideoStatus.COMPLETED: "✅",
                VideoStatus.FAILED: "❌",
            }
            status_icon = status_icons.get(project.status, "📝")

            item.setText(
                f"{status_icon} {project.name}\n   平台: {platform_name} | 时长: {project.duration:.1f}s | 片段: {len(project.clips)}"
            )
            item.setData(Qt.UserRole, project.id)
            self.projects_list.addItem(item)

    def _create_new_project(self) -> None:
        """创建新项目"""
        from PySide6.QtWidgets import QDialog, QFormLayout

        dialog = QDialog(self)
        dialog.setWindowTitle("新建视频项目")
        dialog.setMinimumWidth(400)

        layout = QFormLayout(dialog)

        name_input = QLineEdit()
        name_input.setPlaceholderText("项目名称")
        layout.addRow("名称:", name_input)

        platform_input = QComboBox()
        platform_input.addItems(["抖音", "小红书", "快手", "B站", "TikTok"])
        layout.addRow("平台:", platform_input)

        title_input = QLineEdit()
        title_input.setPlaceholderText("视频标题")
        layout.addRow("标题:", title_input)

        script_input = QTextEdit()
        script_input.setPlaceholderText("视频文案脚本...")
        script_input.setMaximumHeight(100)
        layout.addRow("脚本:", script_input)

        buttons = QHBoxLayout()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        buttons.addWidget(cancel_btn)

        ok_btn = QPushButton("创建")
        ok_btn.setStyleSheet(
            f"background-color: {COLORS['accent']}; color: white; padding: 8px 16px;"
        )
        ok_btn.clicked.connect(dialog.accept)
        buttons.addWidget(ok_btn)

        layout.addRow(buttons)

        if dialog.exec() == QDialog.Accepted:
            platform_map = {
                "抖音": "douyin",
                "小红书": "xiaohongshu",
                "快手": "kuaishou",
                "B站": "bilibili",
                "TikTok": "tiktok",
            }

            project = self.video_maker.create_project(
                name=name_input.text() or "未命名项目",
                target_platform=platform_map.get(
                    platform_input.currentText(), "douyin"
                ),
                title=title_input.text(),
                script=script_input.toPlainText(),
            )

            self.current_project = project
            self._load_projects()

            QMessageBox.information(self, "成功", f"项目 '{project.name}' 创建成功！")

    def _import_materials(self) -> None:
        """导入素材"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择素材文件",
            "",
            "视频/图片文件 (*.mp4 *.mov *.avi *.jpg *.jpeg *.png *.webp)",
        )

        if files:
            self.materials.extend(files)
            self._update_materials_list()
            QMessageBox.information(self, "成功", f"已导入 {len(files)} 个素材文件")

    def _update_materials_list(self) -> None:
        """更新素材列表显示"""
        self.materials_list.clear()
        for material in self.materials:
            item = QListWidgetItem(material)
            self.materials_list.addItem(item)

    def _auto_edit(self) -> None:
        """智能自动剪辑"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择一个项目")
            return

        if not self.materials:
            QMessageBox.warning(self, "提示", "请先导入素材")
            return

        success = self.video_maker.auto_edit(
            self.current_project.id, self.materials, target_duration=30.0
        )

        if success:
            QMessageBox.information(self, "成功", "智能剪辑完成！")
        else:
            QMessageBox.critical(self, "错误", "剪辑失败")

    def _render_video(self) -> None:
        """渲染视频"""
        if not self.current_project:
            QMessageBox.warning(self, "提示", "请先选择一个项目")
            return

        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.render_thread = RenderThread(self.video_maker, self.current_project.id)
        self.render_thread.progress.connect(self.progress_bar.setValue)
        self.render_thread.finished.connect(self._on_render_finished)
        self.render_thread.error.connect(self._on_render_error)
        self.render_thread.start()

    def _on_render_finished(self, output_path) -> None:
        """渲染完成回调"""
        self.progress_bar.setVisible(False)
        QMessageBox.information(
            self, "成功", f"视频渲染完成！\n保存位置: {output_path}"
        )
        self._load_projects()

    def _on_render_error(self, error_msg) -> None:
        """渲染错误回调"""
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "错误", f"渲染失败: {error_msg}")

    def _generate_voice(self) -> None:
        """生成配音"""
        text = self.voice_text.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "提示", "请输入文案内容")
            return

        voice_id = self.voice_selector.currentData()

        output_path = self.voice_synthesizer.synthesize(text, voice_id)

        if output_path:
            QMessageBox.information(
                self, "成功", f"配音生成完成！\n保存位置: {output_path}"
            )
        else:
            QMessageBox.critical(self, "错误", "配音生成失败")
