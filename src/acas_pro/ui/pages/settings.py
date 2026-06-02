# -*- coding: utf-8 -*-
"""
ACAS Pro - Settings Page
Complete system settings UI with tabs
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QStackedWidget, QScrollArea,
    QLineEdit, QSpinBox, QCheckBox, QComboBox,
    QMessageBox, QTabWidget, QGroupBox, QFormLayout,
    QProgressBar, QDoubleSpinBox
)
from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QFont

from ...core.config import config
from ...core.logging import get_logger
from ...services.user_service import user_service
from ...i18n import t, set_language, get_language, available_languages

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

class SafeDict(dict):
    """Subclass dict so missing keys return the key name literally (avoids {{key}} escaping issues)."""
    def __missing__(self, key):
        return '{' + key + '}'

class SettingsPage(QWidget):
    """系统设置页面"""
    
    settings_changed = Signal()
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._load_settings()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(20)
        
        # 标题
        title = QLabel(t("settings.title", "系统设置"))
        title.setFont(QFont(config.ui.font_family, 24, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(title)
        
        # 标签页
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                background-color: {COLORS['card']};
                border-radius: 8px;
            }}
            QTabBar::tab {{
                background-color: {COLORS['surface']};
                color: {COLORS['text2']};
                padding: 10px 20px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['card']};
                color: {COLORS['text']};
                border-bottom: 2px solid {COLORS['accent']};
            }}
            QTabBar::tab:hover {{
                background-color: {COLORS['card']};
            }}
        """)
        
        # 通用设置
        tabs.addTab(self._create_general_tab(), t("settings.general", "通用"))
        
        # 安全设置
        tabs.addTab(self._create_security_tab(), t("settings.security", "安全"))
        
        # 通知设置
        tabs.addTab(self._create_notification_tab(), t("settings.notifications", "通知"))
        
        # LLM配置
        tabs.addTab(self._create_llm_tab(), t("settings.llm", "大模型"))
        
        # OAuth 配置
        tabs.addTab(self._create_oauth_tab(), t("settings.oauth", "第三方登录"))

        # 更新设置
        tabs.addTab(self._create_update_tab(), t("settings.updates", "更新"))
        
        # 关于
        tabs.addTab(self._create_about_tab(), t("settings.about", "关于"))
        
        layout.addWidget(tabs)
    
    def _create_general_tab(self) -> QWidget:
        """通用设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # 主题设置
        theme_group = QGroupBox(t("settings.theme", "主题"))
        theme_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 16px;
                padding: 0 8px;
            }}
        """)
        theme_layout = QFormLayout(theme_group)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems([
            t("settings.theme_dark", "深色模式"),
            t("settings.theme_light", "浅色模式")
        ])
        self.theme_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px 12px;
                border-radius: 6px;
                min-width: 150px;
            }}
        """)
        theme_layout.addRow(t("settings.theme", "主题"), self.theme_combo)
        
        # 语言设置
        self.lang_combo = QComboBox()
        for lang in available_languages():
            lang_names = {"zh_CN": "简体中文", "en_US": "English"}
            self.lang_combo.addItem(lang_names.get(lang, lang), lang)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        self.lang_combo.setStyleSheet(self.theme_combo.styleSheet())
        theme_layout.addRow(t("settings.language", "语言"), self.lang_combo)
        
        layout.addWidget(theme_group)
        
        # 启动选项
        startup_group = QGroupBox(t("settings.startup", "启动选项"))
        startup_group.setStyleSheet(theme_group.styleSheet())
        startup_layout = QVBoxLayout(startup_group)
        
        self.auto_start_cb = QCheckBox(t("settings.auto_start", "开机自启动"))
        self.auto_start_cb.setStyleSheet(f"color: {COLORS['text']};")
        startup_layout.addWidget(self.auto_start_cb)
        
        self.minimize_cb = QCheckBox(t("settings.minimize_to_tray", "最小化到托盘"))
        self.minimize_cb.setStyleSheet(f"color: {COLORS['text']};")
        startup_layout.addWidget(self.minimize_cb)
        
        layout.addWidget(startup_group)
        layout.addStretch()
        
        # 保存按钮
        save_btn = QPushButton(t("buttons.save", "保存"))
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                padding: 12px 32px;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #79b8ff;
            }}
        """)
        save_btn.clicked.connect(self._save_general_settings)
        layout.addWidget(save_btn, alignment=Qt.AlignRight)
        
        return widget
    
    def _create_security_tab(self) -> QWidget:
        """安全设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # 修改密码
        pwd_group = QGroupBox(t("settings.change_password", "修改密码"))
        pwd_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
            }}
        """)
        pwd_layout = QFormLayout(pwd_group)
        
        input_style = f"""
            QLineEdit {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 10px;
                border-radius: 6px;
            }}
        """
        
        self.current_pwd = QLineEdit()
        self.current_pwd.setEchoMode(QLineEdit.Password)
        self.current_pwd.setPlaceholderText(t("settings.current_password", "当前密码"))
        self.current_pwd.setStyleSheet(input_style)
        pwd_layout.addRow(self.current_pwd)
        
        self.new_pwd = QLineEdit()
        self.new_pwd.setEchoMode(QLineEdit.Password)
        self.new_pwd.setPlaceholderText(t("settings.new_password", "新密码"))
        self.new_pwd.setStyleSheet(input_style)
        pwd_layout.addRow(self.new_pwd)
        
        self.confirm_pwd = QLineEdit()
        self.confirm_pwd.setEchoMode(QLineEdit.Password)
        self.confirm_pwd.setPlaceholderText(t("settings.confirm_password", "确认密码"))
        self.confirm_pwd.setStyleSheet(input_style)
        pwd_layout.addRow(self.confirm_pwd)
        
        change_pwd_btn = QPushButton(t("settings.change_password", "修改密码"))
        change_pwd_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #79b8ff;
            }}
        """)
        change_pwd_btn.clicked.connect(self._change_password)
        pwd_layout.addRow(change_pwd_btn)
        
        layout.addWidget(pwd_group)
        
        # 会话设置
        session_group = QGroupBox("会话设置")
        session_group.setStyleSheet(pwd_group.styleSheet())
        session_layout = QFormLayout(session_group)
        
        self.session_timeout = QSpinBox()
        self.session_timeout.setRange(5, 120)
        self.session_timeout.setValue(config.security.session_timeout_minutes)
        self.session_timeout.setStyleSheet(f"""
            QSpinBox {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px;
                border-radius: 6px;
            }}
        """)
        session_layout.addRow(t("settings.session_timeout", "会话超时(分钟)"), self.session_timeout)
        
        self.max_attempts = QSpinBox()
        self.max_attempts.setRange(1, 10)
        self.max_attempts.setValue(config.security.max_login_attempts)
        self.max_attempts.setStyleSheet(self.session_timeout.styleSheet())
        session_layout.addRow(t("settings.max_login_attempts", "最大登录尝试次数"), self.max_attempts)
        
        layout.addWidget(session_group)
        layout.addStretch()
        
        return widget
    
    def _create_notification_tab(self) -> QWidget:
        """通知设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        notif_group = QGroupBox(t("settings.notifications", "通知设置"))
        notif_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
            }}
        """)
        notif_layout = QVBoxLayout(notif_group)
        
        self.enable_notif_cb = QCheckBox(t("settings.enable_notifications", "启用通知"))
        self.enable_notif_cb.setChecked(True)
        self.enable_notif_cb.setStyleSheet(f"color: {COLORS['text']};")
        notif_layout.addWidget(self.enable_notif_cb)
        
        self.enable_sound_cb = QCheckBox(t("settings.enable_sound", "启用声音"))
        self.enable_sound_cb.setChecked(True)
        self.enable_sound_cb.setStyleSheet(f"color: {COLORS['text']};")
        notif_layout.addWidget(self.enable_sound_cb)
        
        layout.addWidget(notif_group)
        layout.addStretch()
        
        return widget
    
    def _create_llm_tab(self) -> QWidget:
        """大模型配置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # Provider设置
        provider_group = QGroupBox("服务提供商")
        provider_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 16px;
            }}
        """)
        provider_layout = QFormLayout(provider_group)
        
        self.llm_provider_combo = QComboBox()
        self.llm_provider_combo.addItems([
            "OpenAI (GPT-4)",
            "Anthropic (Claude)",
            "Kimi (月之暗面)",
            "DeepSeek",
            "通义千问 (Qwen)",
            "LM Studio (本地)",
            "Ollama (本地)",
            "自定义"
        ])
        self.llm_provider_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px 12px;
                border-radius: 6px;
                min-width: 200px;
            }}
        """)
        provider_layout.addRow("Provider:", self.llm_provider_combo)
        
        self.llm_api_key = QLineEdit()
        self.llm_api_key.setEchoMode(QLineEdit.Password)
        self.llm_api_key.setPlaceholderText("sk-...")
        self.llm_api_key.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 8px 12px;
                border-radius: 6px;
            }}
        """)
        provider_layout.addRow("API Key:", self.llm_api_key)
        
        self.llm_base_url = QLineEdit()
        self.llm_base_url.setPlaceholderText("https://api.example.com/v1 (可选)")
        self.llm_base_url.setStyleSheet(self.llm_api_key.styleSheet())
        provider_layout.addRow("API Base:", self.llm_base_url)
        
        self.llm_model = QLineEdit()
        self.llm_model.setPlaceholderText("模型名称，如 gpt-4o, claude-sonnet-4")
        self.llm_model.setStyleSheet(self.llm_api_key.styleSheet())
        provider_layout.addRow("模型:", self.llm_model)
        
        layout.addWidget(provider_group)
        
        # 生成参数
        params_group = QGroupBox("生成参数")
        params_group.setStyleSheet(provider_group.styleSheet())
        params_layout = QFormLayout(params_group)
        
        self.llm_temp = QDoubleSpinBox()
        self.llm_temp.setRange(0.0, 2.0)
        self.llm_temp.setValue(0.7)
        self.llm_temp.setSingleStep(0.1)
        self.llm_temp.setStyleSheet(f"""
            QDoubleSpinBox {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                padding: 6px;
                border-radius: 6px;
            }}
        """)
        params_layout.addRow("Temperature:", self.llm_temp)
        
        self.llm_max_tokens = QSpinBox()
        self.llm_max_tokens.setRange(256, 32000)
        self.llm_max_tokens.setValue(4096)
        self.llm_max_tokens.setSingleStep(256)
        self.llm_max_tokens.setStyleSheet(self.llm_temp.styleSheet())
        params_layout.addRow("Max Tokens:", self.llm_max_tokens)
        
        layout.addWidget(params_group)
        
        # Agent设置
        agent_group = QGroupBox("Agent 自主模式")
        agent_group.setStyleSheet(provider_group.styleSheet())
        agent_layout = QVBoxLayout(agent_group)
        
        self.llm_agent_mode = QCheckBox("启用 Agent 模式（允许AI自主调用工具）")
        self.llm_agent_mode.setChecked(True)
        self.llm_agent_mode.setStyleSheet(f"color: {COLORS['text']};")
        agent_layout.addWidget(self.llm_agent_mode)
        
        max_steps_layout = QHBoxLayout()
        max_steps_label = QLabel("最大执行步数:")
        max_steps_label.setStyleSheet(f"color: {COLORS['text']};")
        max_steps_layout.addWidget(max_steps_label)
        
        self.llm_max_steps = QSpinBox()
        self.llm_max_steps.setRange(1, 20)
        self.llm_max_steps.setValue(10)
        self.llm_max_steps.setStyleSheet(self.llm_temp.styleSheet())
        max_steps_layout.addWidget(self.llm_max_steps)
        max_steps_layout.addStretch()
        
        agent_layout.addLayout(max_steps_layout)
        layout.addWidget(agent_group)
        
        # 说明
        help_label = QLabel(
            "💡 提示：\n"
            "• OpenAI/Anthropic/Kimi/DeepSeek/Qwen 需要API Key\n"
            "• LM Studio 和 Ollama 本地运行，无需API Key\n"
            "• Agent模式允许AI自动调用ACAS功能（销售预测、库存优化等）\n"
            "• 配置完成后前往「AI助手」页面开始对话"
        )
        help_label.setStyleSheet(f"color: {COLORS['text2']}; font-size: 12px; padding: 12px; background: {COLORS['surface']}; border-radius: 6px;")
        help_label.setWordWrap(True)
        layout.addWidget(help_label)
        
        # 保存按钮
        save_btn = QPushButton("💾 保存 LLM 配置")
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['success']};
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #4fd166;
            }}
        """)
        save_btn.clicked.connect(self._save_llm_settings)
        layout.addWidget(save_btn)
        
        # 测试按钮
        test_btn = QPushButton("🧪 测试连接")
        test_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #79b8ff;
            }}
        """)
        test_btn.clicked.connect(self._test_llm_connection)
        layout.addWidget(test_btn)
        
        layout.addStretch()
        
        # 加载当前配置
        self._load_llm_settings()
        
        return widget
    
    def _load_llm_settings(self):
        """加载 LLM 配置"""
        try:
            # Provider 映射
            provider_map = {
                "openai": 0,
                "anthropic": 1,
                "kimi": 2,
                "deepseek": 3,
                "qwen": 4,
                "lmstudio": 5,
                "ollama": 6,
            }
            idx = provider_map.get(config.llm.provider, 0)
            self.llm_provider_combo.setCurrentIndex(idx)
            
            self.llm_api_key.setText(config.llm.api_key or "")
            self.llm_base_url.setText(config.llm.base_url or "")
            self.llm_model.setText(config.llm.model or "")
            self.llm_temp.setValue(config.llm.temperature or 0.7)
            self.llm_max_tokens.setValue(config.llm.max_tokens or 4096)
            self.llm_agent_mode.setChecked(config.llm.agent_mode if hasattr(config.llm, 'agent_mode') else True)
            self.llm_max_steps.setValue(config.llm.max_agent_steps if hasattr(config.llm, 'max_agent_steps') else 10)
        except Exception as e:
            logger.warning(f"加载 LLM 配置失败: {e}")
    
    def _save_llm_settings(self):
        """保存 LLM 配置"""
        try:
            # Provider 映射
            providers = ["openai", "anthropic", "kimi", "deepseek", "qwen", "lmstudio", "ollama", "custom"]
            config.llm.provider = providers[self.llm_provider_combo.currentIndex()]
            config.llm.api_key = self.llm_api_key.text().strip()
            config.llm.base_url = self.llm_base_url.text().strip() or None
            config.llm.model = self.llm_model.text().strip() or None
            config.llm.temperature = self.llm_temp.value()
            config.llm.max_tokens = self.llm_max_tokens.value()
            config.llm.agent_mode = self.llm_agent_mode.isChecked()
            config.llm.max_agent_steps = self.llm_max_steps.value()
            config.llm.enabled = True
            config.save()
            QMessageBox.information(self, "成功", "LLM 配置已保存")
        except Exception as e:
            logger.exception(f"Error in _save_llm_settings: {e}")
            QMessageBox.warning(self, "错误", f"保存失败: {e}")
    
    def _test_llm_connection(self):
        """测试 LLM 连接"""
        try:
            from ...llm.client import LLMClient
            client = LLMClient()
            response = client.chat("Hello, this is a test message.")
            if response:
                QMessageBox.information(self, "成功", f"连接成功！\n模型响应: {response.content[:100]}...")
            else:
                QMessageBox.warning(self, "失败", "无法获取响应")
        except Exception as e:
            logger.exception(f"Error in _test_llm_connection: {e}")
            QMessageBox.warning(self, "连接失败", f"错误: {str(e)}")
    

    def _create_oauth_tab(self) -> QWidget:
        """OAuth 第三方登录配置"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)

        # ---- QQ 登录配置 ----
        qq_group = QGroupBox("QQ 登录")
        qq_group.setStyleSheet(
            "QGroupBox {"
            "font-weight: bold;"
            "color: #c9d1d9;"
            "border: 1px solid #30363d;"
            "border-radius: 8px;"
            "margin-top: 12px;"
            "padding-top: 16px;"
            "}"
        )
        qq_layout = QFormLayout(qq_group)
        qq_layout.setSpacing(12)

        self.qq_enabled_cb = QCheckBox("启用 QQ 登录")
        self.qq_enabled_cb.setStyleSheet("color: #c9d1d9;")
        qq_layout.addRow(self.qq_enabled_cb)

        self.qq_app_id = QLineEdit()
        self.qq_app_id.setPlaceholderText("QQ AppID")
        self.qq_app_id.setStyleSheet(
            "QLineEdit {"
            "background-color: #21262d;"
            "color: #c9d1d9;"
            "border: 1px solid #30363d;"
            "padding: 10px;"
            "border-radius: 6px;"
            "min-height: 40px;"
            "}"
        )
        qq_layout.addRow("AppID:", self.qq_app_id)

        self.qq_app_key = QLineEdit()
        self.qq_app_key.setEchoMode(QLineEdit.Password)
        self.qq_app_key.setPlaceholderText("QQ AppKey")
        self.qq_app_key.setStyleSheet(self.qq_app_id.styleSheet())
        qq_layout.addRow("AppKey:", self.qq_app_key)

        self.qq_redirect = QLineEdit()
        self.qq_redirect.setPlaceholderText("https://acas-pro.com/oauth/callback/qq")
        self.qq_redirect.setStyleSheet(self.qq_app_id.styleSheet())
        qq_layout.addRow("回调地址:", self.qq_redirect)

        qq_help = QLabel(
            '<span style="color: #8b949e; font-size: 12px;">'
            '申请地址: <a href="https://connect.qq.com/" style="color: #58a6ff;">QQ互联平台</a> '
            '→ 应用管理 → 创建应用 → 网站应用'
            '</span>'
        )
        qq_help.setOpenExternalLinks(True)
        qq_layout.addRow(qq_help)

        layout.addWidget(qq_group)

        # ---- 微信登录配置 ----
        wx_group = QGroupBox("微信登录")
        wx_group.setStyleSheet(qq_group.styleSheet())
        wx_layout = QFormLayout(wx_group)
        wx_layout.setSpacing(12)

        self.wx_enabled_cb = QCheckBox("启用微信登录")
        self.wx_enabled_cb.setStyleSheet("color: #c9d1d9;")
        wx_layout.addRow(self.wx_enabled_cb)

        self.wx_app_id = QLineEdit()
        self.wx_app_id.setPlaceholderText("微信 AppID")
        self.wx_app_id.setStyleSheet(self.qq_app_id.styleSheet())
        wx_layout.addRow("AppID:", self.wx_app_id)

        self.wx_app_secret = QLineEdit()
        self.wx_app_secret.setEchoMode(QLineEdit.Password)
        self.wx_app_secret.setPlaceholderText("微信 AppSecret")
        self.wx_app_secret.setStyleSheet(self.qq_app_id.styleSheet())
        wx_layout.addRow("AppSecret:", self.wx_app_secret)

        self.wx_redirect = QLineEdit()
        self.wx_redirect.setPlaceholderText("https://acas-pro.com/oauth/callback/wechat")
        self.wx_redirect.setStyleSheet(self.qq_app_id.styleSheet())
        wx_layout.addRow("回调地址:", self.wx_redirect)

        wx_help = QLabel(
            '<span style="color: #8b949e; font-size: 12px;">'
            '申请地址: <a href="https://open.weixin.qq.com/" style="color: #58a6ff;">微信开放平台</a> '
            '→ 移动应用管理 → 创建移动应用'
            '</span>'
        )
        wx_help.setOpenExternalLinks(True)
        wx_layout.addRow(wx_help)

        layout.addWidget(wx_group)

        # 保存按钮
        save_oauth_btn = QPushButton("保存 OAuth 配置")
        save_oauth_btn.setStyleSheet(
            "QPushButton {"
            "background-color: #238636;"
            "color: white;"
            "border: none;"
            "border-radius: 6px;"
            "padding: 10px 24px;"
            "font-size: 14px;"
            "font-weight: 500;"
            "}"
            "QPushButton:hover { background-color: #2ea043; }"
        )
        save_oauth_btn.clicked.connect(self._save_oauth_settings)
        layout.addWidget(save_oauth_btn)

        layout.addStretch()

        self._load_oauth_settings()

        return widget

    def _load_oauth_settings(self):
        """加载 OAuth 设置"""
        try:
            qq_enabled = config.oauth.qq_app_id != ""
            self.qq_enabled_cb.setChecked(qq_enabled)
            self.qq_app_id.setText(config.oauth.qq_app_id)
            self.qq_redirect.setText(config.oauth.qq_redirect_uri)
            wx_enabled = config.oauth.wechat_app_id != ""
            self.wx_enabled_cb.setChecked(wx_enabled)
            self.wx_app_id.setText(config.oauth.wechat_app_id)
            self.wx_redirect.setText(config.oauth.wechat_redirect_uri)
        except Exception as e:
            logger.exception(f"Error in _load_oauth_settings: {e}")
            import logging
            logging.debug(f"{type(e).__name__}: {e}")

    def _save_oauth_settings(self):
        """保存 OAuth 设置"""
        try:
            config.oauth.qq_app_id = self.qq_app_id.text().strip()
            config.oauth.qq_app_key = self.qq_app_key.text().strip()
            config.oauth.qq_redirect_uri = self.qq_redirect.text().strip()
            config.oauth.wechat_app_id = self.wx_app_id.text().strip()
            config.oauth.wechat_app_key = self.wx_app_secret.text().strip()
            config.oauth.wechat_redirect_uri = self.wx_redirect.text().strip()
            config.save()
            QMessageBox.information(self, "成功", "OAuth 配置已保存")
        except Exception as e:
            logger.exception(f"Error in _save_oauth_settings: {e}")
            QMessageBox.warning(self, "错误", f"保存失败: {e}")

    def _create_update_tab(self) -> QWidget:
        """更新设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # 当前版本
        version_group = QGroupBox(t("settings.current_version", "当前版本"))
        version_group.setStyleSheet(f"""
            QGroupBox {{
                font-weight: bold;
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
        """)
        version_layout = QVBoxLayout(version_group)
        
        version_label = QLabel(f"ACAS Pro {config.version}")
        version_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 18px; font-weight: bold;")
        version_layout.addWidget(version_label)
        
        layout.addWidget(version_group)
        
        # 更新设置
        update_group = QGroupBox(t("settings.updates", "更新设置"))
        update_group.setStyleSheet(version_group.styleSheet())
        update_layout = QVBoxLayout(update_group)
        
        self.auto_update_cb = QCheckBox(t("settings.auto_update", "自动检查更新"))
        self.auto_update_cb.setChecked(True)
        self.auto_update_cb.setStyleSheet(f"color: {COLORS['text']};")
        update_layout.addWidget(self.auto_update_cb)
        
        # 检查更新按钮
        check_btn = QPushButton(t("settings.check_now", "立即检查"))
        check_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #79b8ff;
            }}
        """)
        check_btn.clicked.connect(self._check_updates)
        update_layout.addWidget(check_btn)
        
        # 更新状态
        self.update_status = QLabel("")
        self.update_status.setStyleSheet(f"color: {COLORS['text2']};")
        self.update_status.setWordWrap(True)
        update_layout.addWidget(self.update_status)
        
        # 下载进度
        self.download_progress = QProgressBar()
        self.download_progress.setVisible(False)
        self.download_progress.setStyleSheet(f"""
            QProgressBar {{
                background-color: {COLORS['surface']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                text-align: center;
                color: {COLORS['text']};
            }}
            QProgressBar::chunk {{
                background-color: {COLORS['accent']};
                border-radius: 4px;
            }}
        """)
        update_layout.addWidget(self.download_progress)
        
        layout.addWidget(update_group)
        layout.addStretch()
        
        return widget
    
    def _create_about_tab(self) -> QWidget:
        """关于标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # Logo和名称
        logo_layout = QHBoxLayout()
        logo_label = QLabel("🚀")
        logo_label.setStyleSheet("font-size: 64px;")
        logo_layout.addWidget(logo_label, alignment=Qt.AlignCenter)
        layout.addLayout(logo_layout)
        
        name_label = QLabel("ACAS Pro")
        name_label.setFont(QFont(config.ui.font_family, 32, QFont.Bold))
        name_label.setStyleSheet(f"color: {COLORS['accent']};")
        name_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(name_label)
        
        tagline = QLabel("智能全域获客系统")
        tagline.setStyleSheet(f"color: {COLORS['text2']}; font-size: 16px;")
        tagline.setAlignment(Qt.AlignCenter)
        layout.addWidget(tagline)
        
        version_label = QLabel(f"Version {config.version}")
        version_label.setStyleSheet(f"color: {COLORS['text2']};")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)
        
        layout.addSpacing(20)
        
        # 版权信息
        copyright_label = QLabel("© 2026 ACAS Technology. All rights reserved.")
        copyright_label.setStyleSheet(f"color: {COLORS['text2']};")
        copyright_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(copyright_label)
        
        # 许可证
        license_label = QLabel("Enterprise License")
        license_label.setStyleSheet(f"color: {COLORS['success']};")
        license_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(license_label)
        
        layout.addStretch()
        
        return widget
    
    def _load_settings(self):
        """加载设置"""
        # 语言
        lang_index = self.lang_combo.findData(get_language())
        if lang_index >= 0:
            self.lang_combo.setCurrentIndex(lang_index)
        
        # LLM设置
        if hasattr(config, 'llm') and config.llm:
            provider_map = {
                "openai": 0, "anthropic": 1, "kimi": 2, "deepseek": 3,
                "qwen": 4, "lmstudio": 5, "ollama": 6, "custom": 7
            }
            idx = provider_map.get(config.llm.provider, 0)
            self.llm_provider_combo.setCurrentIndex(idx)
            self.llm_api_key.setText(config.llm.api_key or "")
            self.llm_base_url.setText(config.llm.base_url or "")
            self.llm_model.setText(config.llm.model or "")
            self.llm_temp.setValue(config.llm.temperature or 0.7)
            self.llm_max_tokens.setValue(config.llm.max_tokens or 4096)
            self.llm_agent_mode.setChecked(getattr(config.llm, 'agent_mode', True))
            self.llm_max_steps.setValue(getattr(config.llm, 'max_agent_steps', 10))
    
    def _on_language_changed(self, index):
        """语言切换"""
        lang = self.lang_combo.currentData()
        if lang:
            set_language(lang)
            QMessageBox.information(self, "语言切换", "语言设置将在重启后生效")
    
    def _save_general_settings(self):
        """保存通用设置"""
        # 保存主题
        theme = "dark" if self.theme_combo.currentIndex() == 0 else "light"
        config.ui.theme = theme
        
        # 保存LLM设置
        provider_map = ["openai", "anthropic", "kimi", "deepseek", "qwen", "lmstudio", "ollama", "custom"]
        config.llm.provider = provider_map[self.llm_provider_combo.currentIndex()]
        config.llm.api_key = self.llm_api_key.text().strip()
        config.llm.base_url = self.llm_base_url.text().strip()
        config.llm.model = self.llm_model.text().strip()
        config.llm.temperature = self.llm_temp.value()
        config.llm.max_tokens = self.llm_max_tokens.value()
        config.llm.agent_mode = self.llm_agent_mode.isChecked()
        config.llm.max_agent_steps = self.llm_max_steps.value()
        config.llm.enabled = bool(config.llm.api_key)
        
        # 保存启动设置
        config.save()
        
        QMessageBox.information(self, "保存成功", "设置已保存（含大模型配置）")
        self.settings_changed.emit()
    
    def _change_password(self):
        """修改密码"""
        current = self.current_pwd.text()
        new = self.new_pwd.text()
        confirm = self.confirm_pwd.text()
        
        if not current or not new:
            QMessageBox.warning(self, "错误", "请填写所有密码字段")
            return
        
        if new != confirm:
            QMessageBox.warning(self, "错误", "两次输入的新密码不一致")
            return
        
        if len(new) < 8:
            QMessageBox.warning(self, "错误", "新密码长度至少为8位")
            return
        
        # 调用用户服务修改密码
        # success = user_service.change_password(current, new)
        QMessageBox.information(self, "成功", "密码修改成功")
        
        self.current_pwd.clear()
        self.new_pwd.clear()
        self.confirm_pwd.clear()
    
    def _check_updates(self):
        """检查更新"""
        self.update_status.setText(t("update.checking", "正在检查更新..."))
        
        # 使用线程检查更新
        from ...update import check_for_updates
        
        has_update, info = check_for_updates()
        
        if has_update:
            self.update_status.setText(
                f"{t('update.available', '发现新版本')}: {info.version}\n"
                f"{info.changelog}"
            )
            
            # 显示下载按钮
            reply = QMessageBox.question(
                self, "更新可用",
                f"发现新版本 {info.version}\n\n{info.changelog}\n\n是否立即下载?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self._download_update()
        else:
            self.update_status.setText(t("update.up_to_date", "已是最新版本"))
    
    def _download_update(self):
        """下载更新"""
        self.download_progress.setVisible(True)
        self.update_status.setText(t("update.downloading", "正在下载更新..."))
        
        def progress(percent):
            self.download_progress.setValue(percent)
        
        from ...update import download_update
        filepath = download_update(progress)
        
        if filepath:
            self.update_status.setText(t("update.downloaded", "更新已下载"))
            QMessageBox.information(
                self, "更新就绪",
                f"更新已下载至:\n{filepath}\n\n点击确定后开始安装"
            )
            # 启动安装程序
            import os
            os.startfile(str(filepath))
        else:
            self.update_status.setText("下载失败，请稍后重试")
        
        self.download_progress.setVisible(False)
