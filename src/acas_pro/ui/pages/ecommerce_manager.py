"""
电商管理页面 - 店铺/商品/订单/供应链
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTabWidget, QGridLayout, QScrollArea, QFrame, QComboBox,
    QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QDialog, QDialogButtonBox,
    QFormLayout, QSpinBox, QDoubleSpinBox, QGroupBox,
    QListWidget, QListWidgetItem, QSplitter, QStackedWidget
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor

from typing import Optional, List

from ...ecommerce.shop_manager import ShopManager, Shop, ShopPlatform, ShopStatus, ShopStats
from ...ecommerce.product_manager import ProductManager, Product, ProductCategory, ProductStatus
from ...ecommerce.order_manager import OrderManager, Order, OrderStatus
from ...ecommerce.supply_chain import SupplyChainManager, Supplier


class ShopCard(QFrame):
    """店铺卡片"""
    
    def __init__(self, shop: Shop, parent=None):
        super().__init__(parent)
        self.shop = shop
        self.setup_ui()
    
    def setup_ui(self) -> None:
        self.setFixedSize(280, 180)
        self.setStyleSheet("""
            ShopCard {
                background-color: #161b22;
                border: 2px solid #30363d;
                border-radius: 12px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        
        # 平台图标和名称
        header = QHBoxLayout()
        
        platform_icons = {
            ShopPlatform.DOUYIN_SHOP: "🎵",
            ShopPlatform.KUAISHOU_SHOP: "⚡",
            ShopPlatform.TAOBAO: "🛒",
            ShopPlatform.TMALL: "🐱",
            ShopPlatform.JD: "🐕",
            ShopPlatform.PDD: "🔴",
            ShopPlatform.XIAOHONGSHU_SHOP: "📕",
            ShopPlatform.WECHAT_SHOP: "💬",
        }
        
        platform_label = QLabel(platform_icons.get(self.shop.platform, "🏪"))
        platform_label.setStyleSheet("font-size: 24px;")
        header.addWidget(platform_label)
        
        name = QLabel(self.shop.name)
        name.setStyleSheet("font-size: 14px; font-weight: bold; color: #c9d1d9;")
        header.addWidget(name)
        header.addStretch()
        
        # 状态
        status_colors = {
            ShopStatus.ACTIVE: "#238636",
            ShopStatus.PAUSED: "#d29922",
            ShopStatus.SUSPENDED: "#da3633",
            ShopStatus.PENDING: "#8b949e",
        }
        status_label = QLabel(self.shop.status.value)
        status_label.setStyleSheet(f"""
            color: {status_colors.get(self.shop.status, '#8b949e')};
            font-size: 11px;
            background-color: #21262d;
            padding: 2px 8px;
            border-radius: 4px;
        """)
        header.addWidget(status_label)
        
        layout.addLayout(header)
        
        # 统计
        stats_layout = QHBoxLayout()
        
        products = QLabel(f"📦 {self.shop.stats.total_products}")
        products.setStyleSheet("color: #8b949e; font-size: 12px;")
        stats_layout.addWidget(products)
        
        orders = QLabel(f"📋 {self.shop.stats.total_orders_today}")
        orders.setStyleSheet("color: #8b949e; font-size: 12px;")
        stats_layout.addWidget(orders)
        
        revenue = QLabel(f"💰 ¥{self.shop.stats.revenue_today:.0f}")
        revenue.setStyleSheet("color: #238636; font-size: 12px;")
        stats_layout.addWidget(revenue)
        
        layout.addLayout(stats_layout)
        
        # 操作按钮
        btn_layout = QHBoxLayout()
        
        sync_btn = QPushButton("🔄 同步")
        sync_btn.setStyleSheet("""
            QPushButton {
                background-color: #1f6feb;
                color: white;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        btn_layout.addWidget(sync_btn)
        
        manage_btn = QPushButton("管理")
        manage_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d;
                color: #c9d1d9;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        btn_layout.addWidget(manage_btn)
        
        layout.addLayout(btn_layout)


class EcommerceManagerPage(QWidget):
    """电商管理页面"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.shop_manager = ShopManager()
        self.product_manager = ProductManager()
        self.order_manager = OrderManager()
        self.supply_manager = SupplyChainManager()
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 标题
        title = QLabel("电商管理中心")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #c9d1d9;")
        layout.addWidget(title)
        
        # 标签页
        self.tabs = QTabWidget()
        
        # 店铺管理
        self.shops_tab = self._create_shops_tab()
        self.tabs.addTab(self.shops_tab, "🏪 店铺管理")
        
        # 商品管理
        self.products_tab = self._create_products_tab()
        self.tabs.addTab(self.products_tab, "📦 商品管理")
        
        # 订单管理
        self.orders_tab = self._create_orders_tab()
        self.tabs.addTab(self.orders_tab, "📋 订单管理")
        
        # 供应链
        self.supply_tab = self._create_supply_tab()
        self.tabs.addTab(self.supply_tab, "🚚 供应链")
        
        layout.addWidget(self.tabs)
    
    def _create_shops_tab(self) -> QWidget:
        """创建店铺管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        add_btn = QPushButton("+ 添加店铺")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
        """)
        add_btn.clicked.connect(self.on_add_shop)
        toolbar.addWidget(add_btn)
        
        toolbar.addStretch()
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.load_shops)
        toolbar.addWidget(refresh_btn)
        
        layout.addLayout(toolbar)
        
        # 店铺网格
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        
        self.shops_container = QWidget()
        self.shops_grid = QGridLayout(self.shops_container)
        self.shops_grid.setSpacing(15)
        
        scroll.setWidget(self.shops_container)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_products_tab(self) -> QWidget:
        """创建商品管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 工具栏
        toolbar = QHBoxLayout()
        
        add_product_btn = QPushButton("+ 添加商品")
        add_product_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: white;
                padding: 10px 20px;
                border-radius: 6px;
            }
        """)
        toolbar.addWidget(add_product_btn)
        
        toolbar.addStretch()
        
        # 搜索
        self.product_search = QLineEdit()
        self.product_search.setPlaceholderText("搜索商品...")
        self.product_search.setMaximumWidth(300)
        toolbar.addWidget(self.product_search)
        
        layout.addLayout(toolbar)
        
        # 商品表格
        self.product_table = QTableWidget()
        self.product_table.setColumnCount(7)
        self.product_table.setHorizontalHeaderLabels([
            "商品名称", "类目", "价格", "库存", "销量", "状态", "操作"
        ])
        self.product_table.horizontalHeader().setStretchLastSection(True)
        self.product_table.setStyleSheet("""
            QTableWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
            QHeaderView::section {
                background-color: #21262d;
                color: #c9d1d9;
                padding: 10px;
                border: none;
            }
        """)
        layout.addWidget(self.product_table)
        
        return widget
    
    def _create_orders_tab(self) -> QWidget:
        """创建订单管理标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 筛选栏
        filter_layout = QHBoxLayout()
        
        self.order_status_filter = QComboBox()
        self.order_status_filter.addItems([
            "全部状态", "待付款", "待发货", "已发货", "已完成", "已取消"
        ])
        filter_layout.addWidget(QLabel("状态:"))
        filter_layout.addWidget(self.order_status_filter)
        
        filter_layout.addStretch()
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.load_orders)
        filter_layout.addWidget(refresh_btn)
        
        layout.addLayout(filter_layout)
        
        # 订单表格
        self.order_table = QTableWidget()
        self.order_table.setColumnCount(8)
        self.order_table.setHorizontalHeaderLabels([
            "订单号", "平台", "买家", "金额", "状态", "下单时间", "操作"
        ])
        self.order_table.horizontalHeader().setStretchLastSection(True)
        self.order_table.setStyleSheet("""
            QTableWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.order_table)
        
        # 统计
        stats_layout = QHBoxLayout()
        
        self.order_stats_label = QLabel("今日订单: 0 | 今日销售额: ¥0.00")
        self.order_stats_label.setStyleSheet("color: #8b949e; padding: 10px;")
        stats_layout.addWidget(self.order_stats_label)
        
        layout.addLayout(stats_layout)
        
        return widget
    
    def _create_supply_tab(self) -> QWidget:
        """创建供应链标签页"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # 分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧：供应商
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        supplier_toolbar = QHBoxLayout()
        add_supplier_btn = QPushButton("+ 添加供应商")
        add_supplier_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
        """)
        supplier_toolbar.addWidget(add_supplier_btn)
        supplier_toolbar.addStretch()
        left_layout.addLayout(supplier_toolbar)
        
        self.supplier_list = QListWidget()
        self.supplier_list.setStyleSheet("""
            QListWidget {
                background-color: #161b22;
                border: 1px solid #30363d;
                border-radius: 8px;
            }
            QListWidget::item {
                padding: 12px;
                border-bottom: 1px solid #21262d;
            }
        """)
        left_layout.addWidget(self.supplier_list)
        
        splitter.addWidget(left_widget)
        
        # 右侧：库存预警和采购
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 库存预警
        alert_group = QGroupBox("⚠️ 低库存预警")
        alert_layout = QVBoxLayout(alert_group)
        
        self.alert_list = QListWidget()
        alert_layout.addWidget(self.alert_list)
        
        right_layout.addWidget(alert_group)
        
        # 采购订单
        po_group = QGroupBox("📦 采购订单")
        po_layout = QVBoxLayout(po_group)
        
        create_po_btn = QPushButton("+ 创建采购单")
        po_layout.addWidget(create_po_btn)
        
        self.po_list = QListWidget()
        po_layout.addWidget(self.po_list)
        
        right_layout.addWidget(po_group)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([400, 500])
        
        layout.addWidget(splitter)
        
        return widget
    
    def load_data(self) -> None:
        """加载数据"""
        self.load_shops()
        self.load_products()
        self.load_orders()
        self.load_supply_data()
    
    def load_shops(self) -> None:
        """加载店铺列表"""
        # 清除现有
        while self.shops_grid.count():
            item = self.shops_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # TODO: 获取当前用户的店铺
        # 模拟数据
        demo_shops = [
            Shop(
                id="shop_1",
                name="抖音旗舰店",
                platform=ShopPlatform.DOUYIN_SHOP,
                status=ShopStatus.ACTIVE,
                stats=ShopStats(total_products=128, total_orders_today=45, revenue_today=5680.0)
            ),
            Shop(
                id="shop_2",
                name="快手优选店",
                platform=ShopPlatform.KUAISHOU_SHOP,
                status=ShopStatus.ACTIVE,
                stats=ShopStats(total_products=96, total_orders_today=32, revenue_today=4230.0)
            ),
        ]
        
        for i, shop in enumerate(demo_shops):
            card = ShopCard(shop)
            self.shops_grid.addWidget(card, i // 3, i % 3)
    
    def load_products(self) -> None:
        """加载商品列表"""
        self.product_table.setRowCount(0)
        
        # 模拟数据
        demo_products = [
            ("夏季新款连衣裙", "服饰鞋包", "¥199.00", 156, 328, "在售"),
            ("保湿精华液", "美妆个护", "¥299.00", 89, 156, "在售"),
            ("智能蓝牙耳机", "数码家电", "¥159.00", 45, 89, "在售"),
            ("有机燕麦片", "食品饮料", "¥39.90", 234, 567, "在售"),
        ]
        
        for row, product in enumerate(demo_products):
            self.product_table.insertRow(row)
            for col, value in enumerate(product):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.product_table.setItem(row, col, item)
            
            # 操作按钮
            action_btn = QPushButton("编辑")
            self.product_table.setCellWidget(row, 6, action_btn)
    
    def load_orders(self) -> None:
        """加载订单列表"""
        self.order_table.setRowCount(0)
        
        # 模拟数据
        demo_orders = [
            ("DD20241201001", "抖音", "用户***123", "¥299.00", "待发货", "2024-12-01 10:30"),
            ("KS20241201002", "快手", "用户***456", "¥159.00", "已发货", "2024-12-01 09:15"),
            ("DD20241201003", "抖音", "用户***789", "¥599.00", "待付款", "2024-12-01 08:45"),
        ]
        
        for row, order in enumerate(demo_orders):
            self.order_table.insertRow(row)
            for col, value in enumerate(order):
                item = QTableWidgetItem(str(value))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.order_table.setItem(row, col, item)
            
            # 操作按钮
            action_btn = QPushButton("详情")
            self.order_table.setCellWidget(row, 6, action_btn)
    
    def load_supply_data(self) -> None:
        """加载供应链数据"""
        # 供应商列表
        self.supplier_list.clear()
        demo_suppliers = [
            "🏭 广州服装厂 (合作中)",
            "🏭 深圳电子厂 (合作中)",
            "🏭 杭州美妆供应商 (合作中)",
        ]
        for supplier in demo_suppliers:
            self.supplier_list.addItem(supplier)
        
        # 库存预警
        self.alert_list.clear()
        demo_alerts = [
            "⚠️ 夏季连衣裙 - 库存: 5 (阈值: 10)",
            "⚠️ 保湿精华 - 库存: 3 (阈值: 10)",
        ]
        for alert in demo_alerts:
            self.alert_list.addItem(alert)
    
    def on_add_shop(self) -> None:
        """添加店铺"""
        QMessageBox.information(self, "添加店铺", "店铺授权功能开发中...")
