"""
区块链结算页面 - 透明化分账与钱包管理
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTabWidget,
    QGridLayout,
    QScrollArea,
    QFrame,
    QComboBox,
    QLineEdit,
    QTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QFormLayout,
    QDoubleSpinBox,
    QGroupBox,
)
from PySide6.QtCore import Qt


from ...blockchain.settlement_engine import (
    SettlementEngine,
    SettlementRecord,
    SettlementStatus,
    SettlementParty,
)
from ...blockchain.wallet_manager import WalletManager, Wallet


class WalletCard(QFrame):
    """钱包卡片"""

    def __init__(self, wallet: Wallet, parent=None):
        super().__init__(parent)
        self.wallet = wallet
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setFixedSize(280, 160)
        self.setStyleSheet("""
            WalletCard {
                background-color: #161b22;
                border: 2px solid #30363d;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # 链类型和地址
        header = QHBoxLayout()

        chain_icons = {
            "ethereum": "⬡",
            "bsc": "🔶",
            "polygon": "⬣",
        }

        chain_label = QLabel(chain_icons.get(self.wallet.chain_type, "⬡"))
        chain_label.setStyleSheet("font-size: 20px;")
        header.addWidget(chain_label)

        # 缩短地址显示
        address_short = f"{self.wallet.address[:10]}...{self.wallet.address[-8:]}"
        address = QLabel(address_short)
        address.setStyleSheet(
            "color: #8b949e; font-size: 11px; font-family: monospace;"
        )
        header.addWidget(address)
        header.addStretch()

        layout.addLayout(header)

        # 余额
        for currency, amount in self.wallet.balances.items():
            if amount > 0:
                balance_layout = QHBoxLayout()

                currency_label = QLabel(currency)
                currency_label.setStyleSheet("color: #8b949e; font-size: 12px;")
                balance_layout.addWidget(currency_label)

                amount_label = QLabel(f"{amount:,.2f}")
                amount_label.setStyleSheet(
                    "color: #c9d1d9; font-size: 18px; font-weight: bold;"
                )
                balance_layout.addWidget(amount_label)

                layout.addLayout(balance_layout)

        # 操作按钮
        btn_layout = QHBoxLayout()

        deposit_btn = QPushButton("充值")
        deposit_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        btn_layout.addWidget(deposit_btn)

        withdraw_btn = QPushButton("提现")
        withdraw_btn.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        btn_layout.addWidget(withdraw_btn)

        layout.addLayout(btn_layout)


class SettlementCard(QFrame):
    """结算记录卡片"""

    def __init__(self, settlement: SettlementRecord, parent=None):
        super().__init__(parent)
        self.settlement = settlement
        self.setup_ui()

    def setup_ui(self) -> None:
        self.setMinimumHeight(120)
        self.setStyleSheet("""
            SettlementCard {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # 头部
        header = QHBoxLayout()

        id_label = QLabel(f"#{self.settlement.id[-8:]}")
        id_label.setStyleSheet(
            "color: #8b949e; font-size: 11px; font-family: monospace;"
        )
        header.addWidget(id_label)

        header.addStretch()

        # 状态
        status_colors = {
            SettlementStatus.PENDING: "#d29922",
            SettlementStatus.PROCESSING: "#58a6ff",
            SettlementStatus.COMPLETED: "#238636",
            SettlementStatus.FAILED: "#da3633",
        }
        status_label = QLabel(self.settlement.status.value)
        status_label.setStyleSheet(f"""
            color: {status_colors.get(self.settlement.status, "#8b949e")};
            font-size: 11px;
            background-color: #21262d;
            padding: 2px 8px;
            border-radius: 4px;
        """)
        header.addWidget(status_label)

        layout.addLayout(header)

        # 金额
        amount = QLabel(
            f"{self.settlement.total_amount:,.2f} {self.settlement.currency}"
        )
        amount.setStyleSheet("color: #c9d1d9; font-size: 16px; font-weight: bold;")
        layout.addWidget(amount)

        # 描述
        desc = QLabel(self.settlement.description)
        desc.setStyleSheet("color: #8b949e; font-size: 12px;")
        layout.addWidget(desc)

        # 参与方
        parties = QLabel(f"参与方: {len(self.settlement.parties)} 个")
        parties.setStyleSheet("color: #58a6ff; font-size: 11px;")
        layout.addWidget(parties)


class SettlementType:
    REVENUE_SHARE = "revenue_share"
    PERFORMANCE_BASED = "performance_based"
    AFFILIATE_COMMISSION = "affiliate_commission"
    BONUS_REWARD = "bonus_reward"
    COMMISSION = "commission"


class BlockchainSettlementPage(QWidget):
    """区块链结算页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settlement_engine = SettlementEngine()
        self.wallet_manager = WalletManager()
        self.setup_ui()
        self.load_data()

    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # 标题
        title = QLabel("区块链结算中心")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #c9d1d9;")
        layout.addWidget(title)

        # 标签页
        self.tabs = QTabWidget()

        # 钱包管理
        self.wallet_tab = self._create_wallet_tab()
        self.tabs.addTab(self.wallet_tab, "💳 钱包管理")

        # 结算记录
        self.settlement_tab = self._create_settlement_tab()
        self.tabs.addTab(self.settlement_tab, "📊 结算记录")

        # 新建结算
        self.new_settlement_tab = self._create_new_settlement_tab()
        self.tabs.addTab(self.new_settlement_tab, "➕ 新建结算")

        # 交易记录
        self.transaction_tab = self._create_transaction_tab()
        self.tabs.addTab(self.transaction_tab, "🔄 交易记录")

        layout.addWidget(self.tabs)

    def _create_wallet_tab(self) -> QWidget:
        """创建钱包管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 工具栏
        toolbar = QHBoxLayout()

        create_btn = QPushButton("+ 创建钱包")
        create_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
        """)
        create_btn.clicked.connect(self.on_create_wallet)
        toolbar.addWidget(create_btn)

        toolbar.addStretch()

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.load_wallets)
        toolbar.addWidget(refresh_btn)

        layout.addLayout(toolbar)

        # 钱包网格
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        self.wallet_container = QWidget()
        self.wallet_grid = QGridLayout(self.wallet_container)
        self.wallet_grid.setSpacing(15)

        scroll.setWidget(self.wallet_container)
        layout.addWidget(scroll)

        # 余额汇总
        summary_group = QGroupBox("余额汇总")
        summary_layout = QHBoxLayout(summary_group)

        self.balance_summary = QLabel("USDT: 0.00 | USDC: 0.00")
        self.balance_summary.setStyleSheet("color: #c9d1d9; font-size: 16px;")
        summary_layout.addWidget(self.balance_summary)

        layout.addWidget(summary_group)

        return widget

    def _create_settlement_tab(self) -> QWidget:
        """创建结算记录标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 筛选
        filter_layout = QHBoxLayout()

        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部状态", "待结算", "结算中", "已完成", "失败"])
        filter_layout.addWidget(QLabel("状态:"))
        filter_layout.addWidget(self.status_filter)

        filter_layout.addStretch()

        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.load_settlements)
        filter_layout.addWidget(refresh_btn)

        layout.addLayout(filter_layout)

        # 结算列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")

        self.settlement_list = QWidget()
        self.settlement_list_layout = QVBoxLayout(self.settlement_list)
        self.settlement_list_layout.setSpacing(10)
        self.settlement_list_layout.addStretch()

        scroll.setWidget(self.settlement_list)
        layout.addWidget(scroll)

        return widget

    def _create_new_settlement_tab(self) -> QWidget:
        """创建新建结算标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 模板选择
        template_group = QGroupBox("选择结算模板")
        template_layout = QVBoxLayout(template_group)

        self.template_combo = QComboBox()
        self.template_combo.addItems(
            [
                "内容收益分成 (平台30% + 创作者50% + 推广20%)",
                "广告收益分成 (平台20% + 广告主70% + 代理10%)",
                "电商销售分成 (平台5% + 商家85% + 物流10%)",
                "直播打赏分成 (平台50% + 主播45% + 公会5%)",
            ]
        )
        template_layout.addWidget(self.template_combo)

        layout.addWidget(template_group)

        # 结算信息
        info_group = QGroupBox("结算信息")
        info_layout = QFormLayout(info_group)

        self.source_id_input = QLineEdit()
        self.source_id_input.setPlaceholderText("订单ID/内容ID等")
        info_layout.addRow("来源ID:", self.source_id_input)

        self.total_amount_input = QDoubleSpinBox()
        self.total_amount_input.setRange(0, 999999999)
        self.total_amount_input.setDecimals(2)
        self.total_amount_input.setValue(1000)
        info_layout.addRow("总金额:", self.total_amount_input)

        self.currency_combo = QComboBox()
        self.currency_combo.addItems(["USDT", "USDC", "CNY"])
        info_layout.addRow("货币:", self.currency_combo)

        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        self.description_input.setPlaceholderText("结算描述...")
        info_layout.addRow("描述:", self.description_input)

        layout.addWidget(info_group)

        # 参与方
        parties_group = QGroupBox("参与方")
        parties_layout = QVBoxLayout(parties_group)

        self.parties_table = QTableWidget()
        self.parties_table.setColumnCount(4)
        self.parties_table.setHorizontalHeaderLabels(
            ["名称", "类型", "钱包地址", "分成比例%"]
        )
        self.parties_table.setRowCount(3)

        # 默认填充
        defaults = [
            ("平台", "platform", "", "30"),
            ("创作者", "creator", "", "50"),
            ("推广者", "affiliate", "", "20"),
        ]
        for row, (name, ptype, wallet, share) in enumerate(defaults):
            self.parties_table.setItem(row, 0, QTableWidgetItem(name))
            self.parties_table.setItem(row, 1, QTableWidgetItem(ptype))
            self.parties_table.setItem(row, 2, QTableWidgetItem(wallet))
            self.parties_table.setItem(row, 3, QTableWidgetItem(share))

        parties_layout.addWidget(self.parties_table)

        add_party_btn = QPushButton("+ 添加参与方")
        parties_layout.addWidget(add_party_btn)

        layout.addWidget(parties_group)

        # 创建按钮
        create_settlement_btn = QPushButton("🚀 创建结算")
        create_settlement_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: white;
                padding: 16px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        create_settlement_btn.clicked.connect(self.on_create_settlement)
        layout.addWidget(create_settlement_btn)

        layout.addStretch()

        return widget

    def _create_transaction_tab(self) -> QWidget:
        """创建交易记录标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 交易表格
        self.tx_table = QTableWidget()
        self.tx_table.setColumnCount(7)
        self.tx_table.setHorizontalHeaderLabels(
            ["交易ID", "类型", "金额", "手续费", "状态", "时间", "操作"]
        )
        self.tx_table.horizontalHeader().setStretchLastSection(True)
        self.tx_table.setStyleSheet("""
            QTableWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.tx_table)

        return widget

    def load_data(self) -> None:
        """加载数据"""
        self.load_wallets()
        self.load_settlements()
        self.load_transactions()

    def load_wallets(self) -> None:
        """加载钱包列表"""
        # 清除现有
        while self.wallet_grid.count():
            item = self.wallet_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 模拟数据
        demo_wallets = [
            Wallet(
                id="wal_1",
                owner_id="user_1",
                owner_type="user",
                address="0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb",
                chain_type="ethereum",
                balances={"USDT": 12580.50, "USDC": 5000.00},
            ),
            Wallet(
                id="wal_2",
                owner_id="user_1",
                owner_type="user",
                address="0x8ba1f109551bD432803012645Hac136c82C3e8C",
                chain_type="bsc",
                balances={"USDT": 3500.00},
            ),
        ]

        for i, wallet in enumerate(demo_wallets):
            card = WalletCard(wallet)
            self.wallet_grid.addWidget(card, i // 3, i % 3)

        # 更新余额汇总
        self.balance_summary.setText("USDT: 16,080.50 | USDC: 5,000.00")

    def load_settlements(self) -> None:
        """加载结算记录"""
        # 清除现有
        while self.settlement_list_layout.count() > 1:
            item = self.settlement_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # 模拟数据
        demo_settlements = [
            SettlementRecord(
                id="stl_001",
                settlement_type=SettlementType.REVENUE_SHARE,
                source_id="content_123",
                source_type="content",
                total_amount=5000,
                parties=[
                    SettlementParty(
                        "platform", "platform", "平台", share_percentage=30
                    ),
                    SettlementParty(
                        "creator", "creator", "创作者", share_percentage=50
                    ),
                    SettlementParty(
                        "affiliate", "affiliate", "推广者", share_percentage=20
                    ),
                ],
                status=SettlementStatus.COMPLETED,
                description="视频内容收益结算",
                distribution={"platform": 1500, "creator": 2500, "affiliate": 1000},
            ),
            SettlementRecord(
                id="stl_002",
                settlement_type=SettlementType.COMMISSION,
                source_id="ad_456",
                source_type="ad",
                total_amount=10000,
                parties=[
                    SettlementParty(
                        "platform", "platform", "平台", share_percentage=20
                    ),
                    SettlementParty(
                        "advertiser", "advertiser", "广告主", share_percentage=70
                    ),
                    SettlementParty("agency", "agency", "代理", share_percentage=10),
                ],
                status=SettlementStatus.PENDING,
                description="广告投放收益结算",
                distribution={},
            ),
        ]

        for settlement in demo_settlements:
            card = SettlementCard(settlement)
            self.settlement_list_layout.insertWidget(0, card)

    def load_transactions(self) -> None:
        """加载交易记录"""
        self.tx_table.setRowCount(0)

        # 模拟数据
        demo_txs = [
            (
                "tx_001",
                "转账",
                "1,000.00 USDT",
                "1.00 USDT",
                "已完成",
                "2024-12-01 10:30",
            ),
            (
                "tx_002",
                "结算",
                "5,000.00 USDT",
                "2.00 USDT",
                "已完成",
                "2024-12-01 09:15",
            ),
            (
                "tx_003",
                "充值",
                "10,000.00 USDT",
                "0.00 USDT",
                "已完成",
                "2024-11-30 18:45",
            ),
        ]

        for row, tx in enumerate(demo_txs):
            self.tx_table.insertRow(row)
            for col, value in enumerate(tx):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.tx_table.setItem(row, col, item)

            # 操作按钮
            detail_btn = QPushButton("详情")
            self.tx_table.setCellWidget(row, 6, detail_btn)

    def on_create_wallet(self) -> None:
        """创建钱包"""
        QMessageBox.information(self, "创建钱包", "钱包创建功能开发中...")

    def on_create_settlement(self) -> None:
        """创建结算"""
        QMessageBox.information(
            self,
            "创建结算",
            f"结算创建成功！\n\n"
            f"来源: {self.source_id_input.text()}\n"
            f"金额: {self.total_amount_input.value()} {self.currency_combo.currentText()}\n"
            f"参与方: {self.parties_table.rowCount()} 个",
        )
