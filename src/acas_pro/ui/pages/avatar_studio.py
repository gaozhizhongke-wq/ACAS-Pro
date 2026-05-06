"""
AI数字人工作室页面
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QGridLayout, QScrollArea, QFrame, QComboBox,
    QLineEdit, QTextEdit, QSlider, QSpinBox, QDoubleSpinBox,
    QFileDialog, QMessageBox, QProgressBar, QGroupBox,
    QListWidget, QListWidgetItem, QSplitter, QDialog,
    QDialogButtonBox, QFormLayout, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QPixmap, QColor

from typing import Optional, List

from ...avatar.avatar_engine import (
    AvatarEngine, DigitalAvatar, AvatarType, AvatarStyle,
    AvatarGender, AvatarAgeGroup, AvatarAppearance
)
from ...avatar.scene_adapter import (
    SceneAdapter, SceneType, BackgroundType, LightingPreset, CameraAngle
)
from ...avatar.lip_sync import LipSyncEngine
from ...avatar.gesture_generator import GestureGenerator


class AvatarCard(QFrame):
    """数字人卡片"""
    
    clicked = Signal(str)  # avatar_id
    
    def __init__(self, avatar: DigitalAvatar, parent=None):
        super().__init__(parent)
        self.avatar = avatar
        self.setup_ui()
    
    def setup_ui(self):
        self.setFixedSize(200, 280)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            AvatarCard {
                background-color: #161b22;
                border: 2px solid #30363d;
                border-radius: 12px;
            }
            AvatarCard:hover {
                border-color: #58a6ff;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 预览图占位
        preview = QFrame()
        preview.setFixedSize(176, 150)
        preview.setStyleSheet("""
            background-color: #21262d;
            border-radius: 8px;
        """)
        preview_layout = QVBoxLayout(preview)
        preview_layout.setAlignment(Qt.AlignCenter)
        
        avatar_icon = QLabel("👤")
        avatar_icon.setStyleSheet("font-size: 48px;")
        preview_layout.addWidget(avatar_icon, alignment=Qt.AlignCenter)
        
        layout.addWidget(preview)
        
        # 名称
        name = QLabel(self.avatar.name)
        name.setStyleSheet("font-size: 14px; font-weight: bold; color: #c9d1d9;")
        layout.addWidget(name)
        
        # 类型标签
        type_labels = {
            AvatarType.BRAND_EXCLUSIVE: "品牌专属",
            AvatarType.SCENE_ADAPTIVE: "场景适配",
            AvatarType.TEMPLATE_BASED: "模板",
            AvatarType.CUSTOM_TRAINED: "定制训练",
        }
        type_label = QLabel(type_labels.get(self.avatar.type, "未知"))
        type_label.setStyleSheet("""
            color: #8b949e;
            font-size: 12px;
            background-color: #21262d;
            padding: 2px 8px;
            border-radius: 4px;
        """)
        layout.addWidget(type_label)
        
        # 风格
        style_labels = {
            AvatarStyle.REALISTIC: "写实",
            AvatarStyle.CARTOON: "卡通",
            AvatarStyle.ANIME: "动漫",
            AvatarStyle.LOW_POLY: "低多边形",
            AvatarStyle.HAND_DRAWN: "手绘",
        }
        style_text = f"{style_labels.get(self.avatar.style, '未知')} | {self.avatar.gender.value}"
        style_label = QLabel(style_text)
        style_label.setStyleSheet("color: #8b949e; font-size: 11px;")
        layout.addWidget(style_label)
        
        # 使用次数
        usage = QLabel(f"使用 {self.avatar.usage_count} 次")
        usage.setStyleSheet("color: #58a6ff; font-size: 11px;")
        layout.addWidget(usage)
    
    def mousePressEvent(self, event):
        self.clicked.emit(self.avatar.id)


class CreateAvatarDialog(QDialog):
    """创建数字人对话框"""
    
    def __init__(self, engine: AvatarEngine, parent=None):
        super().__init__(parent)
        self.engine = engine
        self.setWindowTitle("创建AI数字人")
        self.setMinimumSize(600, 700)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 创建方式选择
        method_group = QGroupBox("创建方式")
        method_layout = QHBoxLayout(method_group)
        
        self.method_template = QRadioButton("使用模板")
        self.method_template.setChecked(True)
        self.method_custom = QRadioButton("自定义创建")
        
        method_layout.addWidget(self.method_template)
        method_layout.addWidget(self.method_custom)
        method_layout.addStretch()
        
        layout.addWidget(method_group)
        
        # 模板选择
        self.template_group = QGroupBox("选择模板")
        template_layout = QGridLayout(self.template_group)
        
        templates = self.engine.get_public_templates()
        for i, template in enumerate(templates[:6]):
            card = AvatarCard(template)
            card.clicked.connect(self.on_template_selected)
            template_layout.addWidget(card, i // 3, i % 3)
        
        layout.addWidget(self.template_group)
        
        # 自定义配置（默认隐藏）
        self.custom_group = QGroupBox("自定义配置")
        self.custom_group.setVisible(False)
        custom_layout = QFormLayout(self.custom_group)
        
        self.name_input = QLineEdit()
        custom_layout.addRow("名称:", self.name_input)
        
        self.style_combo = QComboBox()
        self.style_combo.addItems(["写实", "卡通", "动漫", "低多边形", "手绘"])
        custom_layout.addRow("风格:", self.style_combo)
        
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["男性", "女性", "中性"])
        custom_layout.addRow("性别:", self.gender_combo)
        
        self.age_combo = QComboBox()
        self.age_combo.addItems(["年轻(18-25)", "中年(26-35)", "成熟(36-45)", "资深(46+)"])
        custom_layout.addRow("年龄段:", self.age_combo)
        
        layout.addWidget(self.custom_group)
        
        # 切换显示
        self.method_template.toggled.connect(self.template_group.setVisible)
        self.method_custom.toggled.connect(self.custom_group.setVisible)
        
        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.selected_template = None
    
    def on_template_selected(self, template_id: str):
        """选择模板"""
        self.selected_template = template_id
        self.accept()
    
    def get_config(self) -> dict:
        """获取配置"""
        if self.method_template.isChecked() and self.selected_template:
            return {
                'method': 'template',
                'template_id': self.selected_template,
            }
        else:
            return {
                'method': 'custom',
                'name': self.name_input.text(),
                'style': self.style_combo.currentText(),
                'gender': self.gender_combo.currentText(),
                'age': self.age_combo.currentText(),
            }


class AvatarStudioPage(QWidget):
    """AI数字人工作室页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = AvatarEngine()
        self.scene_adapter = SceneAdapter()
        self.lip_sync = LipSyncEngine()
        self.gesture_gen = GestureGenerator()
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("AI数字人工作室")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #c9d1d9;")
        layout.addWidget(title)
        
        # 标签页
        self.tabs = QTabWidget()
        
        # 我的数字人
        self.avatars_tab = self._create_avatars_tab()
        self.tabs.addTab(self.avatars_tab, "我的数字人")
        
        # 场景管理
        self.scenes_tab = self._create_scenes_tab()
        self.tabs.addTab(self.scenes_tab, "场景管理")
        
        # 视频制作
        self.video_tab = self._create_video_tab()
        self.tabs.addTab(self.video_tab, "视频制作")
        
        layout.addWidget(self.tabs)
    
    def _create_avatars_tab(self) -> QWidget:
        """创建数字人标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        create_btn = QPushButton("+ 创建数字人")
        create_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
        """)
        create_btn.clicked.connect(self.on_create_avatar)
        toolbar.addWidget(create_btn)
        
        toolbar.addStretch()
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.load_avatars)
        toolbar.addWidget(refresh_btn)
        
        layout.addLayout(toolbar)
        
        # 数字人网格
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        
        self.avatars_container = QWidget()
        self.avatars_grid = QGridLayout(self.avatars_container)
        self.avatars_grid.setSpacing(15)
        
        scroll.setWidget(self.avatars_container)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_scenes_tab(self) -> QWidget:
        """创建场景标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        create_scene_btn = QPushButton("+ 创建场景")
        create_scene_btn.clicked.connect(self.on_create_scene)
        toolbar.addWidget(create_scene_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 场景列表
        self.scene_list = QListWidget()
        self.scene_list.setStyleSheet("""
            QListWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
            QListWidget::item {
                padding: 16px;
                border-bottom: 1px solid #21262d;
            }
            QListWidget::item:selected {
                background-color: #1f6feb;
            }
        """)
        layout.addWidget(self.scene_list)
        
        return widget
    
    def _create_video_tab(self) -> QWidget:
        """创建视频制作标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：配置
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 选择数字人
        avatar_group = QGroupBox("选择数字人")
        avatar_layout = QVBoxLayout(avatar_group)
        
        self.avatar_combo = QComboBox()
        avatar_layout.addWidget(self.avatar_combo)
        
        left_layout.addWidget(avatar_group)
        
        # 选择场景
        scene_group = QGroupBox("选择场景")
        scene_layout = QVBoxLayout(scene_group)
        
        self.scene_combo = QComboBox()
        scene_layout.addWidget(self.scene_combo)
        
        left_layout.addWidget(scene_group)
        
        # 输入文案
        script_group = QGroupBox("输入文案")
        script_layout = QVBoxLayout(script_group)
        
        self.script_input = QTextEdit()
        self.script_input.setPlaceholderText("输入数字人要说的文案...")
        self.script_input.setMaximumHeight(150)
        script_layout.addWidget(self.script_input)
        
        left_layout.addWidget(script_group)
        
        # 高级选项
        advanced_group = QGroupBox("高级选项")
        advanced_layout = QFormLayout(advanced_group)
        
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems(["720p", "1080p", "2K", "4K"])
        advanced_layout.addRow("分辨率:", self.resolution_combo)
        
        self.fps_spin = QSpinBox()
        self.fps_spin.setRange(24, 60)
        self.fps_spin.setValue(30)
        advanced_layout.addRow("帧率:", self.fps_spin)
        
        self.gesture_check = QPushButton("☑ 启用AI手势")
        self.gesture_check.setCheckable(True)
        self.gesture_check.setChecked(True)
        advanced_layout.addRow("手势:", self.gesture_check)
        
        left_layout.addWidget(advanced_group)
        
        # 生成按钮
        generate_btn = QPushButton("🎬 生成视频")
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: white;
                padding: 16px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #388bfd;
            }
        """)
        generate_btn.clicked.connect(self.on_generate_video)
        left_layout.addWidget(generate_btn)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)
        
        left_layout.addStretch()
        
        splitter.addWidget(left_widget)
        
        # 右侧：预览
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        preview_label = QLabel("视频预览")
        preview_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        right_layout.addWidget(preview_label)
        
        self.preview_frame = QFrame()
        self.preview_frame.setMinimumSize(400, 300)
        self.preview_frame.setStyleSheet("""
            background-color: #0d1117;
            border: 2px dashed #30363d;
            border-radius: 12px;
        """)
        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setAlignment(Qt.AlignCenter)
        
        preview_hint = QLabel("预览区域\n(生成后显示)")
        preview_hint.setAlignment(Qt.AlignCenter)
        preview_hint.setStyleSheet("color: #8b949e; border: none;")
        preview_layout.addWidget(preview_hint)
        
        right_layout.addWidget(self.preview_frame)
        
        # 最近生成
        recent_label = QLabel("最近生成")
        recent_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 20px;")
        right_layout.addWidget(recent_label)
        
        self.recent_list = QListWidget()
        self.recent_list.setMaximumHeight(150)
        right_layout.addWidget(self.recent_list)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 500])
        
        layout.addWidget(splitter)
        
        return widget
    
    def load_data(self):
        """加载数据"""
        self.load_avatars()
        self.load_scenes()
        self.load_combos()
    
    def load_avatars(self):
        """加载数字人列表"""
        # 清除现有
        while self.avatars_grid.count():
            item = self.avatars_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # 加载模板
        templates = self.engine.get_public_templates()
        for i, avatar in enumerate(templates):
            card = AvatarCard(avatar)
            card.clicked.connect(self.on_avatar_clicked)
            self.avatars_grid.addWidget(card, i // 4, i % 4)
    
    def load_scenes(self):
        """加载场景列表"""
        self.scene_list.clear()
        
        scenes = self.scene_adapter.get_all_scenes()
        for scene in scenes:
            item = QListWidgetItem(f"{scene.name} ({scene.scene_type.value})")
            item.setData(Qt.UserRole, scene.id)
            self.scene_list.addItem(item)
    
    def load_combos(self):
        """加载下拉框"""
        # 数字人
        self.avatar_combo.clear()
        templates = self.engine.get_public_templates()
        for avatar in templates:
            self.avatar_combo.addItem(avatar.name, avatar.id)
        
        # 场景
        self.scene_combo.clear()
        scenes = self.scene_adapter.get_all_scenes()
        if not scenes:
            # 创建默认场景
            for scene_type in [SceneType.LIVE_STREAMING, SceneType.PRODUCT_SHOWCASE]:
                scene = self.scene_adapter.create_scene_from_template(scene_type)
                scenes.append(scene)
        
        for scene in scenes:
            self.scene_combo.addItem(scene.name, scene.id)
    
    def on_create_avatar(self):
        """创建数字人"""
        dialog = CreateAvatarDialog(self.engine, self)
        if dialog.exec() == QDialog.Accepted:
            config = dialog.get_config()
            
            if config['method'] == 'template':
                avatar = self.engine.create_avatar_from_template(
                    config['template_id'],
                    name="我的数字人"
                )
                if avatar:
                    QMessageBox.information(self, "成功", f"数字人 '{avatar.name}' 创建成功！")
                    self.load_avatars()
            else:
                QMessageBox.information(self, "提示", "自定义创建功能开发中...")
    
    def on_avatar_clicked(self, avatar_id: str):
        """点击数字人"""
        avatar = self.engine.get_avatar(avatar_id)
        if avatar:
            QMessageBox.information(
                self, "数字人详情",
                f"名称: {avatar.name}\n"
                f"类型: {avatar.type.value}\n"
                f"风格: {avatar.style.value}\n"
                f"使用次数: {avatar.usage_count}"
            )
    
    def on_create_scene(self):
        """创建场景"""
        QMessageBox.information(self, "提示", "场景创建功能开发中...")
    
    def on_generate_video(self):
        """生成视频"""
        avatar_id = self.avatar_combo.currentData()
        scene_id = self.scene_combo.currentData()
        script = self.script_input.toPlainText()
        
        if not script.strip():
            QMessageBox.warning(self, "提示", "请输入文案")
            return
        
        # 显示进度
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        
        # 模拟生成进度
        self.current_progress = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_progress)
        self.timer.start(100)
        
        # 创建渲染任务
        task_id = self.engine.generate_video(
            avatar_id=avatar_id,
            script=script,
            scene_id=scene_id,
        )
        
        QMessageBox.information(
            self, "任务已创建",
            f"视频生成任务已创建\n任务ID: {task_id}\n\n"
            f"生成过程可能需要几分钟，请稍后查看。"
        )
    
    def _update_progress(self):
        """更新进度"""
        self.current_progress += 2
        self.progress_bar.setValue(min(self.current_progress, 100))
        
        if self.current_progress >= 100:
            self.timer.stop()
            self.progress_bar.setVisible(False)
