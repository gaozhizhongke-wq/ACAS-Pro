#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Account Management Page
账号管理页面
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGridLayout,
    QComboBox,
    QLineEdit,
    QDialog,
    QFormLayout,
    QMessageBox,
    QScrollArea,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from ...core.config import config
from ...core.logging import get_logger
from ...platforms.account_manager import (
    AccountManager,
    PlatformAccount,
    Platform,
    AccountStatus,
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


class AddAccountDialog(QDialog):
    """添加账号对话框"""

    account_added = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加平台账号")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QFormLayout(self)
        layout.setSpacing(12)

        # 平台选择
        self.platform_combo = QComboBox()
        self.platform_combo.addItems(
            ["抖音", "小红书", "快手", "B站", "TikTok", "Instagram", "YouTube"]
        )
        layout.addRow("平台:", self.platform_combo)

        # 账号名称
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("账号名称")
        layout.addRow("账号名称:", self.name_input)

        # 昵称
        self.nickname_input = QLineEdit()
        self.nickname_input.setPlaceholderText("显示昵称")
        layout.addRow("昵称:", self.nickname_input)

        # Access Token
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("Access Token")
        layout.addRow("Access Token:", self.token_input)

        # Refresh Token
        self.refresh_input = QLineEdit()
        self.refresh_input.setPlaceholderText("Refresh Token (可选)")
        layout.addRow("Refresh Token:", self.refresh_input)

        # 地区
        self.region_input = QLineEdit()
        self.region_input.setPlaceholderText("例如: 中国西北、中东")
        layout.addRow("地区:", self.region_input)

        # 分类
        self.category_input = QLineEdit()
        self.category_input.setPlaceholderText("例如: 美食、旅游")
        layout.addRow("内容分类:", self.category_input)

        # 标签
        self.tags_input = QLineEdit()
        self.tags_input.setPlaceholderText("用逗号分隔，例如: 主账号,测试号")
        layout.addRow("标签:", self.tags_input)

        # 按钮
        btn_layout = QHBoxLayout()

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        add_btn = QPushButton("添加")
        add_btn.setStyleSheet(f"background-color: {COLORS['accent']}; color: white;")
        add_btn.clicked.connect(self._on_add)
        btn_layout.addWidget(add_btn)

        layout.addRow(btn_layout)

    def _on_add(self) -> None:
        """添加账号"""
        platform_map = {
            "抖音": Platform.DOUYIN,
            "小红书": Platform.XIAOHONGSHU,
            "快手": Platform.KUAISHOU,
            "B站": Platform.BILIBILI,
            "TikTok": Platform.TIKTOK,
            "Instagram": Platform.INSTAGRAM,
            "YouTube": Platform.YOUTUBE,
        }

        data = {
            "platform": platform_map[self.platform_combo.currentText()],
            "account_name": self.name_input.text(),
            "nickname": self.nickname_input.text() or self.name_input.text(),
            "access_token": self.token_input.text(),
            "refresh_token": self.refresh_input.text() or None,
            "region": self.region_input.text() or None,
            "category": self.category_input.text() or None,
            "tags": [t.strip() for t in self.tags_input.text().split(",") if t.strip()],
        }

        if not data["account_name"] or not data["access_token"]:
            QMessageBox.warning(self, "输入错误", "请填写账号名称和Access Token")
            return

        self.account_added.emit(data)
        self.accept()


class AccountCard(QFrame):
    """账号卡片"""

    def __init__(self, account: PlatformAccount, parent=None):
        super().__init__(parent)
        self.account = account
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS["surface"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 12px;
                padding: 16px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # 头部：平台图标 + 名称
        header = QHBoxLayout()

        platform_icon = QLabel(self._get_platform_icon())
        platform_icon.setFont(QFont("Segoe UI Emoji", 20))
        header.addWidget(platform_icon)

        name_layout = QVBoxLayout()

        name = QLabel(self.account.nickname)
        name.setFont(QFont(config.ui.font_family, 14, QFont.Bold))
        name.setStyleSheet(f"color: {COLORS['text']};")
        name_layout.addWidget(name)

        account_id = QLabel(f"@{self.account.account_name}")
        account_id.setStyleSheet(f"color: {COLORS['text2']}; font-size: 12px;")
        name_layout.addWidget(account_id)

        header.addLayout(name_layout)
        header.addStretch()

        # 状态标签
        status_color = {
            AccountStatus.ACTIVE: COLORS["success"],
            AccountStatus.INACTIVE: COLORS["text2"],
            AccountStatus.SUSPENDED: COLORS["danger"],
            AccountStatus.RESTRICTED: COLORS["warning"],
            AccountStatus.PENDING: COLORS["accent"],
        }.get(self.account.status, COLORS["text2"])

        status_label = QLabel(f"● {self._get_status_text()}")
        status_label.setStyleSheet(f"color: {status_color}; font-size: 12px;")
        header.addWidget(status_label)

        layout.addLayout(header)

        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setStyleSheet(f"background-color: {COLORS['border']};")
        layout.addWidget(line)

        # 数据指标
        stats = QGridLayout()
        stats.setSpacing(16)

        metrics = [
            ("粉丝", f"{self.account.followers:,}"),
            ("关注", f"{self.account.following:,}"),
            ("获赞", f"{self.account.total_likes:,}"),
            ("内容", str(self.account.content_count)),
        ]

        for i, (label, value) in enumerate(metrics):
            col = i % 4
            row = i // 4

            metric_layout = QVBoxLayout()
            metric_layout.setSpacing(4)

            val_label = QLabel(value)
            val_label.setFont(QFont(config.ui.font_family, 16, QFont.Bold))
            val_label.setStyleSheet(f"color: {COLORS['accent']};")
            metric_layout.addWidget(val_label)

            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {COLORS['text2']}; font-size: 12px;")
            metric_layout.addWidget(lbl)

            stats.addLayout(metric_layout, row, col)

        layout.addLayout(stats)

        # 标签
        if self.account.tags:
            tags_layout = QHBoxLayout()
            tags_layout.setSpacing(8)

            for tag in self.account.tags[:3]:  # 最多显示3个标签
                tag_label = QLabel(f"#{tag}")
                tag_label.setStyleSheet(f"""
                    background-color: {COLORS["card"]};
                    color: {COLORS["text2"]};
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 11px;
                """)
                tags_layout.addWidget(tag_label)

            tags_layout.addStretch()
            layout.addLayout(tags_layout)

        # 操作按钮
        btn_row = QHBoxLayout()

        refresh_btn = QPushButton("🔄 刷新数据")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["card"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 12px;
            }}
        """)
        btn_row.addWidget(refresh_btn)

        settings_btn = QPushButton("⚙️ 设置")
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["card"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 6px 12px;
                border-radius: 6px;
                font-size: 12px;
            }}
        """)
        btn_row.addWidget(settings_btn)

        btn_row.addStretch()

        layout.addLayout(btn_row)

    def _get_platform_icon(self) -> str:
        """获取平台图标"""
        icons = {
            Platform.DOUYIN: "🎵",
            Platform.XIAOHONGSHU: "📕",
            Platform.KUAISHOU: "⚡",
            Platform.BILIBILI: "📺",
            Platform.TIKTOK: "🎵",
            Platform.INSTAGRAM: "📷",
            Platform.YOUTUBE: "▶️",
        }
        return icons.get(self.account.platform, "📱")

    def _get_status_text(self) -> str:
        """获取状态文本"""
        status_map = {
            AccountStatus.ACTIVE: "正常",
            AccountStatus.INACTIVE: "未激活",
            AccountStatus.SUSPENDED: "封禁",
            AccountStatus.RESTRICTED: "受限",
            AccountStatus.PENDING: "待审核",
        }
        return status_map.get(self.account.status, "未知")


class AccountManagementPage(QWidget):
    """账号管理页面"""

    def __init__(self):
        super().__init__()
        self.account_manager = AccountManager()
        self._setup_ui()
        self._load_accounts()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        # 标题
        title = QLabel("账号矩阵管理")
        title.setFont(QFont(config.ui.font_family, 24, QFont.Bold))
        title.setStyleSheet(f"color: {COLORS['text']};")
        layout.addWidget(title)

        subtitle = QLabel("多平台账号统一管理、授权与监控")
        subtitle.setStyleSheet(f"color: {COLORS['text2']}; font-size: 14px;")
        layout.addWidget(subtitle)

        layout.addSpacing(16)

        # 统计卡片
        stats_row = QHBoxLayout()

        summary = self.account_manager.get_account_summary()

        for title_text, value, color in [
            ("总账号数", str(summary.get("total_accounts", 0)), COLORS["accent"]),
            ("正常运营", str(summary.get("active_accounts", 0)), COLORS["success"]),
            ("异常账号", str(summary.get("suspended_accounts", 0)), COLORS["danger"]),
            (
                "总粉丝数",
                f"{(summary.get('total_followers') or 0) / 10000:.1f}万",
                COLORS["warning"],
            ),
        ]:
            card = QFrame()
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {COLORS["surface"]};
                    border: 1px solid {COLORS["border"]};
                    border-radius: 12px;
                    padding: 16px;
                    min-width: 150px;
                }}
            """)
            card_layout = QVBoxLayout(card)

            val_label = QLabel(value)
            val_label.setFont(QFont(config.ui.font_family, 28, QFont.Bold))
            val_label.setStyleSheet(f"color: {color};")
            val_label.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(val_label)

            title_label = QLabel(title_text)
            title_label.setStyleSheet(f"color: {COLORS['text2']}; font-size: 12px;")
            title_label.setAlignment(Qt.AlignCenter)
            card_layout.addWidget(title_label)

            stats_row.addWidget(card)

        layout.addLayout(stats_row)

        # 工具栏
        toolbar = QHBoxLayout()

        # 筛选
        filter_label = QLabel("平台筛选:")
        filter_label.setStyleSheet(f"color: {COLORS['text']};")
        toolbar.addWidget(filter_label)

        self.platform_filter = QComboBox()
        self.platform_filter.addItems(
            [
                "全部平台",
                "抖音",
                "小红书",
                "快手",
                "B站",
                "TikTok",
                "Instagram",
                "YouTube",
            ]
        )
        self.platform_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 8px;
                border-radius: 6px;
                min-width: 120px;
            }}
        """)
        self.platform_filter.currentTextChanged.connect(self._filter_accounts)
        toolbar.addWidget(self.platform_filter)

        toolbar.addSpacing(20)

        # 状态筛选
        status_label = QLabel("状态:")
        status_label.setStyleSheet(f"color: {COLORS['text']};")
        toolbar.addWidget(status_label)

        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部状态", "正常", "未激活", "封禁", "受限"])
        self.status_filter.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                border: 1px solid {COLORS["border"]};
                padding: 8px;
                border-radius: 6px;
                min-width: 100px;
            }}
        """)
        self.status_filter.currentTextChanged.connect(self._filter_accounts)
        toolbar.addWidget(self.status_filter)

        toolbar.addStretch()

        # 添加按钮
        add_btn = QPushButton("➕ 添加账号")
        add_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }}
        """)
        add_btn.clicked.connect(self._show_add_dialog)
        toolbar.addWidget(add_btn)

        layout.addLayout(toolbar)

        # 账号列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        self.accounts_container = QWidget()
        self.accounts_layout = QVBoxLayout(self.accounts_container)
        self.accounts_layout.setContentsMargins(0, 0, 0, 0)
        self.accounts_layout.setSpacing(16)
        self.accounts_layout.addStretch()

        scroll.setWidget(self.accounts_container)
        layout.addWidget(scroll)

    def _load_accounts(self) -> None:
        """加载账号列表"""
        # 清空现有列表
        while self.accounts_layout.count() > 1:
            item = self.accounts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 获取账号
        accounts = self.account_manager.list_accounts()

        for account in accounts:
            card = AccountCard(account)
            self.accounts_layout.insertWidget(self.accounts_layout.count() - 1, card)

    def _filter_accounts(self) -> None:
        """筛选账号"""
        platform_map = {
            "全部平台": None,
            "抖音": Platform.DOUYIN,
            "小红书": Platform.XIAOHONGSHU,
            "快手": Platform.KUAISHOU,
            "B站": Platform.BILIBILI,
            "TikTok": Platform.TIKTOK,
            "Instagram": Platform.INSTAGRAM,
            "YouTube": Platform.YOUTUBE,
        }

        status_map = {
            "全部状态": None,
            "正常": AccountStatus.ACTIVE,
            "未激活": AccountStatus.INACTIVE,
            "封禁": AccountStatus.SUSPENDED,
            "受限": AccountStatus.RESTRICTED,
        }

        platform = platform_map.get(self.platform_filter.currentText())
        status = status_map.get(self.status_filter.currentText())

        # 清空列表
        while self.accounts_layout.count() > 1:
            item = self.accounts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 获取筛选后的账号
        accounts = self.account_manager.list_accounts(platform=platform, status=status)

        for account in accounts:
            card = AccountCard(account)
            self.accounts_layout.insertWidget(self.accounts_layout.count() - 1, card)

    def _show_add_dialog(self) -> None:
        """显示添加账号对话框"""
        dialog = AddAccountDialog(self)
        dialog.account_added.connect(self._on_account_added)
        dialog.exec()

    def _on_account_added(self, data: dict) -> None:
        """处理账号添加"""
        try:
            account = self.account_manager.add_account(
                platform=data["platform"],
                account_id=data["account_name"].lower().replace(" ", "_"),
                account_name=data["account_name"],
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                nickname=data["nickname"],
                tags=data.get("tags", []),
                region=data.get("region"),
                category=data.get("category"),
            )

            QMessageBox.information(
                self, "添加成功", f"账号 {account.nickname} 添加成功！"
            )
            self._load_accounts()

        except Exception as e:
            logger.error(f"Failed to add account: {e}")
            QMessageBox.critical(self, "添加失败", f"添加账号失败: {e}")
