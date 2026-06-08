"""
广告投放管理页面
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit,
    QGroupBox, QFormLayout, QDateEdit, QCheckBox, QProgressBar,
    QMessageBox, QFileDialog, QDialog, QDialogButtonBox,
    QListWidget, QListWidgetItem, QSplitter
)
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtGui import QColor

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from ...ads.ad_manager import (
    AdManager, AdAccount, AdCampaign, AdSet, AdCreative,
    AdPlatform, CampaignStatus, BudgetType
)
from ...ads.bidding_engine import BiddingEngine, BiddingStrategy
from ...ads.audience_targeting import AudienceTargeting, AudienceSegment, AudienceType


class CampaignDialog(QDialog):
    """广告计划创建/编辑对话框"""
    
    def __init__(self, manager: AdManager, campaign: Optional[AdCampaign] = None, parent=None):
        super().__init__(parent)
        self.manager = manager
        self.campaign = campaign
        self.setWindowTitle('编辑广告计划" if campaign else "新建广告计划')
        self.setMinimumSize(700, 600)
        self.setup_ui()
        
        if campaign:
            self.load_campaign_data()
    
    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        
        # 基本信息
        basic_group = QGroupBox("基本信息")
        basic_layout = QFormLayout(basic_group)
        
        self.name_input = QLineEdit()
        basic_layout.addRow("计划名称:", self.name_input)
        
        self.platform_combo = QComboBox()
        self.platform_combo.addItems([
            "巨量引擎", "磁力引擎", "腾讯广告", "快手广告", "小红书聚光"
        ])
        basic_layout.addRow("投放平台:", self.platform_combo)
        
        self.objective_combo = QComboBox()
        self.objective_combo.addItems([
            "转化量", "点击量", "展示量", "加粉", "直播间引流"
        ])
        basic_layout.addRow("推广目标:", self.objective_combo)
        
        layout.addWidget(basic_group)
        
        # 预算设置
        budget_group = QGroupBox("预算设置")
        budget_layout = QFormLayout(budget_group)
        
        self.budget_type_combo = QComboBox()
        self.budget_type_combo.addItems(["日预算", "总预算"])
        budget_layout.addRow("预算类型:", self.budget_type_combo)
        
        self.budget_amount = QDoubleSpinBox()
        self.budget_amount.setRange(100, 10000000)
        self.budget_amount.setValue(1000)
        self.budget_amount.setSuffix(" 元")
        budget_layout.addRow("预算金额:", self.budget_amount)
        
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate())
        budget_layout.addRow("开始日期:", self.start_date)
        
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate().addDays(7))
        budget_layout.addRow("结束日期:", self.end_date)
        
        layout.addWidget(budget_group)
        
        # 出价设置
        bidding_group = QGroupBox("出价设置")
        bidding_layout = QFormLayout(bidding_group)
        
        self.strategy_combo = QComboBox()
        self.strategy_combo.addItems([
            "手动出价", "自动oCPC", "自动oCPM", "最大转化", "目标CPA", "目标ROI"
        ])
        bidding_layout.addRow("出价策略:", self.strategy_combo)
        
        self.bid_amount = QDoubleSpinBox()
        self.bid_amount.setRange(0.1, 1000)
        self.bid_amount.setValue(5.0)
        self.bid_amount.setSuffix(" 元")
        bidding_layout.addRow("出价金额:", self.bid_amount)
        
        layout.addWidget(bidding_group)
        
        # 按钮
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def load_campaign_data(self) -> None:
        """加载广告计划数据"""
        if not self.campaign:
            return
        
        self.name_input.setText(self.campaign.name)
        
        platform_map = {
            AdPlatform.OCEAN_ENGINE: 0,
            AdPlatform.MAGNETIC_ENGINE: 1,
            AdPlatform.TENCENT_ADS: 2,
            AdPlatform.KUAISHOU_ADS: 3,
            AdPlatform.XIAOHONGSHU: 4
        }
        self.platform_combo.setCurrentIndex(
            platform_map.get(self.campaign.platform, 0)
        )
        
        self.budget_type_combo.setCurrentIndex(
            0 if self.campaign.budget_type == BudgetType.DAILY else 1
        )
        self.budget_amount.setValue(self.campaign.budget_amount)
    
    def get_campaign_data(self) -> Dict[str, Any]:
        """获取广告计划数据"""
        platforms = [
            AdPlatform.OCEAN_ENGINE, AdPlatform.MAGNETIC_ENGINE,
            AdPlatform.TENCENT_ADS, AdPlatform.KUAISHOU_ADS,
            AdPlatform.XIAOHONGSHU
        ]
        
        objectives = ["conversion", "click", "impression", "follow", "live"]
        strategies = [
            BiddingStrategy.MANUAL, BiddingStrategy.AUTO_OCPC,
            BiddingStrategy.AUTO_OCPM, BiddingStrategy.MAX_CONVERSION,
            BiddingStrategy.TARGET_CPA, BiddingStrategy.TARGET_ROI
        ]
        
        return {
            'name': self.name_input.text(),
            'platform': platforms[self.platform_combo.currentIndex()],
            'objective': objectives[self.objective_combo.currentIndex()],
            'budget_type': BudgetType.DAILY if self.budget_type_combo.currentIndex() == 0 else BudgetType.TOTAL,
            'budget_amount': self.budget_amount.value(),
            'start_date': self.start_date.date().toString("yyyy-MM-dd"),
            'end_date': self.end_date.date().toString("yyyy-MM-dd"),
            'bidding_strategy': strategies[self.strategy_combo.currentIndex()],
            'bid_amount': self.bid_amount.value()
        }


class AdManagerPage(QWidget):
    """广告投放管理页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = AdManager()
        self.bidding_engine = BiddingEngine()
        self.audience_targeting = AudienceTargeting()
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("智能广告投放")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #1a1a2e;")
        layout.addWidget(title)
        
        # 标签页
        self.tabs = QTabWidget()
        
        # 广告计划标签页
        self.campaign_tab = self._create_campaign_tab()
        self.tabs.addTab(self.campaign_tab, "广告计划")
        
        # 账户管理标签页
        self.account_tab = self._create_account_tab()
        self.tabs.addTab(self.account_tab, "账户管理")
        
        # 人群定向标签页
        self.audience_tab = self._create_audience_tab()
        self.tabs.addTab(self.audience_tab, "人群定向")
        
        # 数据报表标签页
        self.report_tab = self._create_report_tab()
        self.tabs.addTab(self.report_tab, "数据报表")
        
        layout.addWidget(self.tabs)
    
    def _create_campaign_tab(self) -> QWidget:
        """创建广告计划标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        self.new_campaign_btn = QPushButton("+ 新建计划")
        self.new_campaign_btn.setStyleSheet("""
            QPushButton {
                background-color: #4361ee;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #3a56d4;
            }
        """)
        self.new_campaign_btn.clicked.connect(self.on_new_campaign)
        toolbar.addWidget(self.new_campaign_btn)
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.load_campaigns)
        toolbar.addWidget(self.refresh_btn)
        
        toolbar.addStretch()
        
        # 筛选
        toolbar.addWidget(QLabel("平台:"))
        self.platform_filter = QComboBox()
        self.platform_filter.addItems(["全部", "巨量引擎", "磁力引擎", "腾讯广告", "快手广告", "小红书"])
        self.platform_filter.currentIndexChanged.connect(self.load_campaigns)
        toolbar.addWidget(self.platform_filter)
        
        toolbar.addWidget(QLabel("状态:"))
        self.status_filter = QComboBox()
        self.status_filter.addItems(["全部", "投放中", "已暂停", "已完成", "草稿"])
        self.status_filter.currentIndexChanged.connect(self.load_campaigns)
        toolbar.addWidget(self.status_filter)
        
        layout.addLayout(toolbar)
        
        # 广告计划表格
        self.campaign_table = QTableWidget()
        self.campaign_table.setColumnCount(10)
        self.campaign_table.setHorizontalHeaderLabels([
            "计划名称", "平台", "状态", "预算", "消耗", "展示", "点击", "转化", "CTR", "操作"
        ])
        self.campaign_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.campaign_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.campaign_table.setAlternatingRowColors(True)
        self.campaign_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 10px;
                font-weight: bold;
                border: none;
            }
        """)
        layout.addWidget(self.campaign_table)
        
        # 统计信息
        stats_layout = QHBoxLayout()
        
        self.total_spend_label = QLabel("总消耗: ¥0.00")
        self.total_spend_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #4361ee;")
        stats_layout.addWidget(self.total_spend_label)
        
        self.total_impressions_label = QLabel("总展示: 0")
        self.total_impressions_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        stats_layout.addWidget(self.total_impressions_label)
        
        self.total_clicks_label = QLabel("总点击: 0")
        self.total_clicks_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        stats_layout.addWidget(self.total_clicks_label)
        
        self.avg_ctr_label = QLabel("平均CTR: 0.00%")
        self.avg_ctr_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        stats_layout.addWidget(self.avg_ctr_label)
        
        stats_layout.addStretch()
        layout.addLayout(stats_layout)
        
        return widget
    
    def _create_account_tab(self) -> QWidget:
        """创建账户管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        add_account_btn = QPushButton("+ 添加账户")
        add_account_btn.setStyleSheet("""
            QPushButton {
                background-color: #4361ee;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
        """)
        toolbar.addWidget(add_account_btn)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # 账户列表
        self.account_table = QTableWidget()
        self.account_table.setColumnCount(6)
        self.account_table.setHorizontalHeaderLabels([
            "账户名称", "平台", "状态", "余额", "日限额", "操作"
        ])
        self.account_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.account_table)
        
        return widget
    
    def _create_audience_tab(self) -> QWidget:
        """创建人群定向标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：人群包列表
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        toolbar = QHBoxLayout()
        new_segment_btn = QPushButton("+ 新建人群包")
        new_segment_btn.clicked.connect(self.on_new_segment)
        toolbar.addWidget(new_segment_btn)
        toolbar.addStretch()
        left_layout.addLayout(toolbar)
        
        self.segment_list = QListWidget()
        self.segment_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #4361ee;
                color: white;
            }
        """)
        left_layout.addWidget(self.segment_list)
        
        splitter.addWidget(left_widget)
        
        # 右侧：人群详情
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        self.segment_detail = QGroupBox("人群包详情")
        detail_layout = QFormLayout(self.segment_detail)
        
        self.segment_name_label = QLabel("-")
        detail_layout.addRow("名称:", self.segment_name_label)
        
        self.segment_type_label = QLabel("-")
        detail_layout.addRow("类型:", self.segment_type_label)
        
        self.segment_size_label = QLabel("-")
        detail_layout.addRow("预估规模:", self.segment_size_label)
        
        self.segment_status_label = QLabel("-")
        detail_layout.addRow("状态:", self.segment_status_label)
        
        right_layout.addWidget(self.segment_detail)
        right_layout.addStretch()
        
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 400])
        
        layout.addWidget(splitter)
        
        return widget
    
    def _create_report_tab(self) -> QWidget:
        """创建数据报表标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 筛选条件
        filter_layout = QHBoxLayout()
        
        filter_layout.addWidget(QLabel("时间范围:"))
        self.report_start = QDateEdit()
        self.report_start.setDate(QDate.currentDate().addDays(-30))
        filter_layout.addWidget(self.report_start)
        
        filter_layout.addWidget(QLabel("至"))
        self.report_end = QDateEdit()
        self.report_end.setDate(QDate.currentDate())
        filter_layout.addWidget(self.report_end)
        
        generate_btn = QPushButton("生成报表")
        generate_btn.clicked.connect(self.on_generate_report)
        filter_layout.addWidget(generate_btn)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        # 报表内容区域
        self.report_content = QTextEdit()
        self.report_content.setReadOnly(True)
        self.report_content.setPlaceholderText("点击「生成报表」查看数据...")


        layout.addWidget(self.report_content)
        
        return widget
    
    def load_data(self) -> None:
        """加载所有数据"""
        self.load_campaigns()
        self.load_accounts()
        self.load_segments()
    
    def load_campaigns(self) -> None:
        """加载广告计划列表"""
        self.campaign_table.setRowCount(0)
        
        # 获取筛选条件
        platform_filter = self.platform_filter.currentIndex()
        status_filter = self.status_filter.currentIndex()
        
        campaigns = self.manager.get_campaigns()
        
        total_spend = 0
        total_impressions = 0
        total_clicks = 0
        
        for campaign in campaigns:
            # 应用筛选
            if platform_filter > 0:
                platform_map = {
                    1: AdPlatform.OCEAN_ENGINE,
                    2: AdPlatform.MAGNETIC_ENGINE,
                    3: AdPlatform.TENCENT_ADS,
                    4: AdPlatform.KUAISHOU_ADS,
                    5: AdPlatform.XIAOHONGSHU
                }
                if campaign.platform != platform_map.get(platform_filter):
                    continue
            
            if status_filter > 0:
                status_map = {
                    1: CampaignStatus.ACTIVE,
                    2: CampaignStatus.PAUSED,
                    3: CampaignStatus.FINISHED,
                    4: CampaignStatus.DRAFT
                }
                if campaign.status != status_map.get(status_filter):
                    continue
            
            row = self.campaign_table.rowCount()
            self.campaign_table.insertRow(row)
            
            # 平台名称映射
            platform_names = {
                AdPlatform.OCEAN_ENGINE: "巨量引擎",
                AdPlatform.MAGNETIC_ENGINE: "磁力引擎",
                AdPlatform.TENCENT_ADS: "腾讯广告",
                AdPlatform.KUAISHOU_ADS: "快手广告",
                AdPlatform.XIAOHONGSHU: "小红书"
            }
            
            # 状态样式
            status_names = {
                CampaignStatus.DRAFT: "草稿",
                CampaignStatus.PENDING: "待审核",
                CampaignStatus.ACTIVE: "投放中",
                CampaignStatus.PAUSED: "已暂停",
                CampaignStatus.DISABLED: "已禁用",
                CampaignStatus.FINISHED: "已完成",
                CampaignStatus.REJECTED: "审核拒绝"
            }
            
            # 统计数据
            stats = self.manager.get_campaign_stats(campaign.id, 30)
            
            items = [
                campaign.name,
                platform_names.get(campaign.platform, "未知"),
                status_names.get(campaign.status, "未知"),
                f"¥{campaign.budget_amount:,.2f}",
                f"¥{stats['spend']:,.2f}",
                f"{stats['impressions']:,}",
                f"{stats['clicks']:,}",
                f"{stats['conversions']:,}",
                f"{stats['ctr']:.2f}%",
                "编辑 | 暂停 | 删除"
            ]
            
            for col, text in enumerate(items):
                item = QTableWidgetItem(text)
                if col == 2:  # 状态列
                    if campaign.status == CampaignStatus.ACTIVE:
                        item.setForeground(QColor("#28a745"))
                    elif campaign.status == CampaignStatus.PAUSED:
                        item.setForeground(QColor("#ffc107"))
                self.campaign_table.setItem(row, col, item)
            
            total_spend += stats['spend']
            total_impressions += stats['impressions']
            total_clicks += stats['clicks']
        
        # 更新统计
        self.total_spend_label.setText(f"总消耗: ¥{total_spend:,.2f}")
        self.total_impressions_label.setText(f"总展示: {total_impressions:,}")
        self.total_clicks_label.setText(f"总点击: {total_clicks:,}")
        avg_ctr = (total_clicks / total_impressions * 100) if total_impressions > 0 else 0
        self.avg_ctr_label.setText(f"平均CTR: {avg_ctr:.2f}%")
    
    def load_accounts(self) -> None:
        """加载账户列表"""
        self.account_table.setRowCount(0)
        
        accounts = self.manager.get_all_accounts()
        
        for account in accounts:
            row = self.account_table.rowCount()
            self.account_table.insertRow(row)
            
            platform_names = {
                AdPlatform.OCEAN_ENGINE: "巨量引擎",
                AdPlatform.MAGNETIC_ENGINE: "磁力引擎",
                AdPlatform.TENCENT_ADS: "腾讯广告",
                AdPlatform.KUAISHOU_ADS: "快手广告",
                AdPlatform.XIAOHONGSHU: "小红书"
            }
            
            items = [
                account.account_name,
                platform_names.get(account.platform, "未知"),
                "正常" if account.status == "active" else "异常",
                f"¥{account.balance:,.2f}",
                f"¥{account.daily_budget_limit:,.2f}" if account.daily_budget_limit > 0 else "无限制",
                "编辑 | 刷新余额 | 删除"
            ]
            
            for col, text in enumerate(items):
                self.account_table.setItem(row, col, QTableWidgetItem(text))
    
    def load_segments(self) -> None:
        """加载人群包列表"""
        self.segment_list.clear()
        
        segments = self.audience_targeting.get_segments()
        
        for segment in segments:
            item = QListWidgetItem(f"{segment.name} ({segment.estimated_size:,}人)")
            item.setData(Qt.UserRole, segment.id)
            self.segment_list.addItem(item)
        
        self.segment_list.itemClicked.connect(self.on_segment_selected)
    
    def on_new_campaign(self) -> None:
        """新建广告计划"""
        dialog = CampaignDialog(self.manager, parent=self)
        if dialog.exec() == QDialog.Accepted:
            data = dialog.get_campaign_data()
            
            # 创建广告计划
            campaign = AdCampaign(
                id=f"camp_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                name=data['name'],
                platform=data['platform'],
                account_id="default_account",
                status=CampaignStatus.DRAFT,
                objective=data['objective'],
                budget_type=data['budget_type'],
                budget_amount=data['budget_amount'],
                start_date=data['start_date'],
                end_date=data['end_date'],
                adsets=[],
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat()
            )
            
            if self.manager.create_campaign(campaign):
                QMessageBox.information(self, "成功", "广告计划创建成功！")
                self.load_campaigns()
            else:
                QMessageBox.warning(self, "错误", "创建失败，请重试")
    
    def on_new_segment(self) -> None:
        """新建人群包"""
        QMessageBox.information(self, "提示", "人群包创建功能开发中...")
    
    def on_segment_selected(self, item) -> None:
        """选择人群包"""
        segment_id = item.data(Qt.UserRole)
        segment = self.audience_targeting.get_segment(segment_id)
        
        if segment:
            self.segment_name_label.setText(segment.name)
            self.segment_type_label.setText(segment.type.value)
            self.segment_size_label.setText(f"{segment.estimated_size:,}人")
            self.segment_status_label.setText('正常" if segment.status == "active" else "暂停')
    
    def on_generate_report(self) -> None:
        """生成报表"""
        start_date = self.report_start.date().toString("yyyy-MM-dd")
        end_date = self.report_end.date().toString("yyyy-MM-dd")
        
        # 获取平台对比数据
        comparison = self.manager.get_platform_comparison(30)
        
        report = f"""
<h2>广告投放数据报表</h2>
<p><strong>时间范围:</strong> {start_date} 至 {end_date}</p>

<h3>平台投放对比</h3>
<table border="1" cellpadding="8" style="border-collapse: collapse;">
    <tr style="background-color: #f0f0f0;">
        <th>平台</th>
        <th>展示量</th>
        <th>点击量</th>
        <th>转化量</th>
        <th>消耗</th>
        <th>CTR</th>
        <th>CPC</th>
    </tr>
"""
        
        platform_names = {
            'ocean_engine': '巨量引擎',
            'magnetic': '磁力引擎',
            'tencent': '腾讯广告',
            'kuaishou': '快手广告',
            'xiaohongshu': '小红书'
        }
        
        for platform, data in comparison.items():
            name = platform_names.get(platform, platform)
            report += f"""
    <tr>
        <td>{name}</td>
        <td>{data['impressions']:,}</td>
        <td>{data['clicks']:,}</td>
        <td>{data['conversions']:,}</td>
        <td>¥{data['spend']:,.2f}</td>
        <td>{data['ctr']:.2f}%</td>
        <td>¥{data['cpc']:.2f}</td>
    </tr>
"""
        
        report += "</table>"
        
        self.report_content.setHtml(report)
