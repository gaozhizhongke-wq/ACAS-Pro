#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - 登录/注册对话框
"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QStackedWidget, QWidget,
    QCheckBox, QMessageBox, QFrame, QSpacerItem,
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QPixmap

from ...core.config import config

# Get config object (config is a function)
_cfg = config()
from ...core.security import JWTManager, SessionManager, PasswordHasher
from ...services.user_service import user_service


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


class StyledInput(QLineEdit):
    """统一风格的输入框"""
    
    def __init__(self, placeholder="", password=False, parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        if password:
            self.setEchoMode(QLineEdit.Password)
        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: {COLORS['surface']};
                border: 1.5px solid {COLORS['border']};
                border-radius: 10px;
                padding: 14px 16px;
                color: {COLORS['text']};
                font-size: 14px;
                min-height: 20px;
            }}
            QLineEdit:focus {{
                border: 2px solid {COLORS['accent']};
                background-color: {COLORS['card']};
            }}
            QLineEdit::placeholder {{
                color: {COLORS['text2']};
            }}
        """)
        self.setMinimumHeight(50)


class StyledButton(QPushButton):
    """统一风格的按钮"""
    
    def __init__(self, text, primary=True, parent=None):
        super().__init__(text, parent)
        self.primary = primary
        self._update_style()
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(50)
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        
    def _update_style(self):
        if self.primary:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['accent']};
                    border: none;
                    border-radius: 10px;
                    padding: 14px 24px;
                    color: white;
                    font-size: 15px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: #79b8ff;
                }}
                QPushButton:pressed {{
                    background-color: #4a90d9;
                }}
                QPushButton:disabled {{
                    background-color: {COLORS['border']};
                    color: {COLORS['text2']};
                }}
            """)
        else:
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: 1.5px solid {COLORS['border']};
                    border-radius: 10px;
                    padding: 14px 24px;
                    color: {COLORS['text']};
                    font-size: 15px;
                    font-weight: 500;
                }}
                QPushButton:hover {{
                    background-color: {COLORS['surface']};
                    border-color: {COLORS['accent']};
                }}
            """)


class LoginPage(QWidget):
    """登录页面"""
    
    login_success = Signal(dict)
    switch_to_register = Signal()
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 56, 48, 48)
        layout.setSpacing(0)  # 手动控制每个间距
        
        # === 标题区域 ===
        title = QLabel("欢迎回来")
        title.setFont(QFont(_cfg.ui.font_family, 32, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text']};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(8)
        
        subtitle = QLabel("登录您的 ACAS Pro 账户")
        subtitle.setStyleSheet(f"color: {COLORS['text2']}; font-size: 15px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(40)
        
        # === 用户名 ===
        user_label = QLabel("用户名 / 邮箱")
        user_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500;")
        layout.addWidget(user_label)
        
        layout.addSpacing(8)
        
        self.username_input = StyledInput("请输入用户名或邮箱")
        layout.addWidget(self.username_input)
        
        layout.addSpacing(20)
        
        # === 密码 ===
        pwd_label = QLabel("密码")
        pwd_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500;")
        layout.addWidget(pwd_label)
        
        layout.addSpacing(8)
        
        self.password_input = StyledInput("请输入密码", password=True)
        layout.addWidget(self.password_input)
        
        layout.addSpacing(16)
        
        # === 记住我 + 忘记密码 ===
        row = QHBoxLayout()
        row.setSpacing(0)
        
        self.remember_cb = QCheckBox("记住登录状态")
        self.remember_cb.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text2']};
                font-size: 13px;
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 5px;
                border: 2px solid {COLORS['border']};
                background-color: {COLORS['surface']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {COLORS['accent']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['accent']};
                border-color: {COLORS['accent']};
            }}
        """)
        row.addWidget(self.remember_cb)
        
        row.addStretch()
        
        forgot_btn = QPushButton("忘记密码？")
        forgot_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {COLORS['accent']};
                font-size: 13px;
                padding: 0;
            }}
            QPushButton:hover {{
                text-decoration: underline;
            }}
        """)
        forgot_btn.setCursor(Qt.PointingHandCursor)
        forgot_btn.clicked.connect(self._on_forgot_password)
        row.addWidget(forgot_btn)
        
        layout.addLayout(row)
        
        layout.addSpacing(32)
        
        # === 登录按钮 ===
        self.login_btn = StyledButton("登 录", primary=True)
        self.login_btn.clicked.connect(self._on_login)
        layout.addWidget(self.login_btn)
        
        layout.addSpacing(24)
        
        # === 分隔线 ===
        separator_layout = QHBoxLayout()
        separator_layout.setSpacing(16)
        
        left_line = QFrame()
        left_line.setFrameShape(QFrame.HLine)
        left_line.setStyleSheet(f"background-color: {COLORS['border']}; border: none;")
        left_line.setFixedHeight(1)
        separator_layout.addWidget(left_line, 1)
        
        or_label = QLabel("或使用以下方式登录")
        or_label.setStyleSheet(f"color: {COLORS['text2']}; font-size: 12px;")
        separator_layout.addWidget(or_label)
        
        right_line = QFrame()
        right_line.setFrameShape(QFrame.HLine)
        right_line.setStyleSheet(f"background-color: {COLORS['border']}; border: none;")
        right_line.setFixedHeight(1)
        separator_layout.addWidget(right_line, 1)
        
        layout.addLayout(separator_layout)
        
        layout.addSpacing(24)
        
        # === 第三方登录 ===
        oauth_layout = QHBoxLayout()
        oauth_layout.setSpacing(12)
        
        self.qq_login_btn = QPushButton("QQ 登录")
        self.qq_login_btn.setMinimumHeight(50)
        self.qq_login_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #12B7F5;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px 20px;
                font-size: 15px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #0099CC;
            }}
        """)
        self.qq_login_btn.setCursor(Qt.PointingHandCursor)
        self.qq_login_btn.clicked.connect(self._on_qq_login)
        oauth_layout.addWidget(self.qq_login_btn)
        
        self.wechat_login_btn = QPushButton("微信登录")
        self.wechat_login_btn.setMinimumHeight(50)
        self.wechat_login_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #07C160;
                color: white;
                border: none;
                border-radius: 10px;
                padding: 12px 20px;
                font-size: 15px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #06AD56;
            }}
        """)
        self.wechat_login_btn.setCursor(Qt.PointingHandCursor)
        self.wechat_login_btn.clicked.connect(self._on_wechat_login)
        oauth_layout.addWidget(self.wechat_login_btn)
        
        layout.addLayout(oauth_layout)
        
        layout.addStretch()
        
        # === 底部切换 ===
        switch_row = QHBoxLayout()
        switch_row.setAlignment(Qt.AlignCenter)
        switch_row.setSpacing(4)
        
        switch_text = QLabel("还没有账户？")
        switch_text.setStyleSheet(f"color: {COLORS['text2']}; font-size: 14px;")
        switch_row.addWidget(switch_text)
        
        switch_btn = QPushButton("立即注册")
        switch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {COLORS['accent']};
                font-size: 14px;
                font-weight: 600;
                padding: 0;
                padding-left: 4px;
            }}
            QPushButton:hover {{
                text-decoration: underline;
            }}
        """)
        switch_btn.setCursor(Qt.PointingHandCursor)
        switch_btn.clicked.connect(self.switch_to_register.emit)
        switch_row.addWidget(switch_btn)
        
        layout.addLayout(switch_row)
        
    def _on_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "输入错误", "请输入用户名和密码")
            return
            
        # 验证登录
        user = user_service.authenticate(username, password)
        if user:
            self.login_success.emit(user.to_dict())
        else:
            QMessageBox.warning(self, "登录失败", "用户名或密码错误")
            
    def _on_forgot_password(self):
        QMessageBox.information(self, "忘记密码", "请联系管理员重置密码")
    
    def _on_qq_login(self):
        """QQ登录"""
        # 使用OAuth服务
        from ...services.oauth import OAuthService
        from ....core.config import config
        
        # Get config object (config is a function)
        _cfg = config()
        
        oauth = OAuthService(_cfg.oauth)
        url, state = oauth.get_authorization_url("qq")
        
        # 打开浏览器进行授权
        import webbrowser
        QMessageBox.information(self, "QQ登录", "即将打开浏览器进行QQ授权...\n授权完成后请返回本窗口")
        webbrowser.open(url)
        
        # 实际应用中需要启动本地HTTP服务监听回调
        # 这里是简化版本，仅作演示
        reply = QMessageBox.question(
            self, "QQ登录",
            "如果已在浏览器完成授权，请点击“是”继续\n或点击“否”取消",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 实际需要处理回调获取用户信息
            QMessageBox.information(self, "开发者提示", "QQ OAuth功能需要配置有效的AppID和回调地址\n请联系管理员完成配置")
            # 模拟登录成功
            # self.login_success.emit({"username": "qq_user", "nickname": "QQ用户"})
    
    def _on_wechat_login(self):
        """微信登录"""
        from ...services.oauth import OAuthService
        from ....core.config import config
        
        # Get config object (config is a function)
        _cfg = config()
        
        oauth = OAuthService(_cfg.oauth)
        url, state = oauth.get_authorization_url("wechat")
        
        import webbrowser
        QMessageBox.information(self, "微信登录", "即将打开浏览器进行微信授权...\n授权完成后请返回本窗口")
        webbrowser.open(url)
        
        reply = QMessageBox.question(
            self, "微信登录",
            "如果已在浏览器完成授权，请点击“是”继续\n或点击“否”取消",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            QMessageBox.information(self, "开发者提示", "微信 OAuth功能需要配置有效的AppID和回调地址\n请联系管理员完成配置")
            # self.login_success.emit({"username": "wechat_user", "nickname": "微信用户"})


class RegisterPage(QWidget):
    """注册页面"""
    
    register_success = Signal(dict)
    switch_to_login = Signal()
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 56, 48, 48)
        layout.setSpacing(0)
        
        # === 标题区域 ===
        title = QLabel("创建账户")
        title.setFont(QFont(_cfg.ui.font_family, 32, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text']};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(8)
        
        subtitle = QLabel("开始您的智能获客之旅")
        subtitle.setStyleSheet(f"color: {COLORS['text2']}; font-size: 15px;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(40)
        
        # === 用户名 ===
        user_label = QLabel("用户名")
        user_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500;")
        layout.addWidget(user_label)
        layout.addSpacing(8)
        self.username_input = StyledInput("请输入用户名（3-20个字符）")
        layout.addWidget(self.username_input)
        
        layout.addSpacing(20)
        
        # === 昵称 ===
        nick_label = QLabel("昵称")
        nick_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500;")
        layout.addWidget(nick_label)
        layout.addSpacing(8)
        self.nickname_input = StyledInput("请输入昵称")
        layout.addWidget(self.nickname_input)
        
        layout.addSpacing(20)
        
        # === 邮箱 ===
        email_label = QLabel("邮箱")
        email_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500;")
        layout.addWidget(email_label)
        layout.addSpacing(8)
        self.email_input = StyledInput("请输入邮箱地址")
        layout.addWidget(self.email_input)
        
        layout.addSpacing(20)
        
        # === 密码 ===
        pwd_label = QLabel("密码")
        pwd_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500;")
        layout.addWidget(pwd_label)
        layout.addSpacing(8)
        self.password_input = StyledInput("请输入密码（至少8位）", password=True)
        layout.addWidget(self.password_input)
        
        layout.addSpacing(20)
        
        # === 确认密码 ===
        pwd2_label = QLabel("确认密码")
        pwd2_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 14px; font-weight: 500;")
        layout.addWidget(pwd2_label)
        layout.addSpacing(8)
        self.password2_input = StyledInput("请再次输入密码", password=True)
        layout.addWidget(self.password2_input)
        
        layout.addSpacing(20)
        
        # === 用户协议 ===
        self.agree_cb = QCheckBox("我已阅读并同意《用户协议》和《隐私政策》")
        self.agree_cb.setStyleSheet(f"""
            QCheckBox {{
                color: {COLORS['text2']};
                font-size: 13px;
                spacing: 10px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 5px;
                border: 2px solid {COLORS['border']};
                background-color: {COLORS['surface']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {COLORS['accent']};
                border-color: {COLORS['accent']};
            }}
        """)
        layout.addWidget(self.agree_cb)
        
        layout.addSpacing(32)
        
        # === 注册按钮 ===
        self.register_btn = StyledButton("注  册", primary=True)
        self.register_btn.clicked.connect(self._on_register)
        layout.addWidget(self.register_btn)
        
        layout.addSpacing(24)
        
        # === 底部切换 ===
        switch_row = QHBoxLayout()
        switch_row.setAlignment(Qt.AlignCenter)
        switch_row.setSpacing(4)
        
        switch_text = QLabel("已有账户？")
        switch_text.setStyleSheet(f"color: {COLORS['text2']}; font-size: 14px;")
        switch_row.addWidget(switch_text)
        
        switch_btn = QPushButton("立即登录")
        switch_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                color: {COLORS['accent']};
                font-size: 14px;
                font-weight: 600;
                padding: 0;
                padding-left: 4px;
            }}
            QPushButton:hover {{
                text-decoration: underline;
            }}
        """)
        switch_btn.setCursor(Qt.PointingHandCursor)
        switch_btn.clicked.connect(self.switch_to_login.emit)
        switch_row.addWidget(switch_btn)
        
        layout.addLayout(switch_row)
        layout.addStretch()
        
    def _on_register(self):
        username = self.username_input.text().strip()
        nickname = self.nickname_input.text().strip()
        email = self.email_input.text().strip()
        password = self.password_input.text()
        password2 = self.password2_input.text()
        
        # 验证输入
        if not username or not email or not password:
            QMessageBox.warning(self, "输入错误", "请填写所有必填项")
            return
            
        if len(username) < 3 or len(username) > 20:
            QMessageBox.warning(self, "输入错误", "用户名长度应为3-20个字符")
            return
            
        if len(password) < 8:
            QMessageBox.warning(self, "输入错误", "密码长度至少为8位")
            return
            
        if password != password2:
            QMessageBox.warning(self, "输入错误", "两次输入的密码不一致")
            return
            
        if not self.agree_cb.isChecked():
            QMessageBox.warning(self, "输入错误", "请阅读并同意用户协议")
            return
            
        # 创建用户
        user = user_service.create_user(
            username=username,
            email=email,
            password=password,
            nickname=nickname or username
        )
        
        if user:
            QMessageBox.information(self, "注册成功", "账户创建成功，请登录")
            self.register_success.emit(user.to_dict())
        else:
            QMessageBox.warning(self, "注册失败", "用户名或邮箱已存在")


class LoginDialog(QDialog):
    """登录/注册对话框"""
    
    login_success = Signal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ACAS Pro - 登录")
        self.setMinimumSize(520, 720)
        self.resize(520, 720)
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['bg']};
            }}
        """)
        
        self._setup_ui()
        
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 创建堆叠窗口
        self.stack = QStackedWidget()
        
        # 登录页面
        self.login_page = LoginPage()
        self.login_page.login_success.connect(self._on_login_success)
        self.login_page.switch_to_register.connect(self._show_register)
        
        # 注册页面
        self.register_page = RegisterPage()
        self.register_page.register_success.connect(self._on_register_success)
        self.register_page.switch_to_login.connect(self._show_login)
        
        self.stack.addWidget(self.login_page)
        self.stack.addWidget(self.register_page)
        
        layout.addWidget(self.stack)
        
    def _show_login(self):
        self.stack.setCurrentIndex(0)
        self.setWindowTitle("ACAS Pro - 登录")
        
    def _show_register(self):
        self.stack.setCurrentIndex(1)
        self.setWindowTitle("ACAS Pro - 注册")
        
    def _on_login_success(self, user_data):
        self.login_success.emit(user_data)
        self.accept()
        
    def _on_register_success(self, user_data):
        self._show_login()
