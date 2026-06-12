#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Inventory Optimization Page
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QGroupBox,
)
from PySide6.QtGui import QFont

from ...core.config import config
from ...ml.inventory_optimizer import inventory_optimizer

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


class InventoryPage(QWidget):
    """Inventory optimization page"""

    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._generate_recommendations()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(24)

        # Header
        header = QLabel("📦 Inventory Optimization")
        header.setFont(QFont(config.ui.font_family, 24, QFont.Bold))
        layout.addWidget(header)

        desc = QLabel("AI-powered inventory management and reorder recommendations")
        desc.setStyleSheet(f"color: {COLORS['text2']};")
        layout.addWidget(desc)

        # Alert banner
        self.alert_banner = QLabel()
        self.alert_banner.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS["danger"]}22;
                color: {COLORS["danger"]};
                padding: 16px 20px;
                border-radius: 8px;
                font-weight: bold;
            }}
        """)
        self.alert_banner.setVisible(False)
        layout.addWidget(self.alert_banner)

        # Controls
        controls = QGroupBox("Actions")
        ctrl_layout = QHBoxLayout(controls)

        refresh_btn = QPushButton("🔄 Refresh Analysis")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS["accent"]};
                color: #fff;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-weight: bold;
            }}
        """)
        refresh_btn.clicked.connect(self._generate_recommendations)
        ctrl_layout.addWidget(refresh_btn)

        ctrl_layout.addStretch()
        layout.addWidget(controls)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(7)
        self.table.setHorizontalHeaderLabels(
            [
                "Product",
                "Current Stock",
                "Recommended Order",
                "Urgency",
                "Days Until Stockout",
                "Reorder Point",
                "Confidence",
            ]
        )
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS["card"]};
                border: 1px solid {COLORS["border"]};
                border-radius: 8px;
            }}
            QHeaderView::section {{
                background-color: {COLORS["surface"]};
                color: {COLORS["text"]};
                padding: 12px;
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: 10px;
                color: {COLORS["text"]};
            }}
        """)
        layout.addWidget(self.table, 1)

    def _generate_recommendations(self) -> None:
        """Generate inventory recommendations"""
        from datetime import datetime, timedelta
        import random

        # Sample inventory data
        inventory_data = [
            {
                "product_id": "PROD-001",
                "name": "Premium Widget A",
                "stock": 150,
                "cost": 25.0,
            },
            {
                "product_id": "PROD-002",
                "name": "Standard Widget B",
                "stock": 45,
                "cost": 15.0,
            },
            {
                "product_id": "PROD-003",
                "name": "Deluxe Widget C",
                "stock": 8,
                "cost": 50.0,
            },
            {
                "product_id": "PROD-004",
                "name": "Basic Widget D",
                "stock": 500,
                "cost": 10.0,
            },
            {
                "product_id": "PROD-005",
                "name": "Pro Widget E",
                "stock": 23,
                "cost": 75.0,
            },
        ]

        # Generate sales history
        sales_history = {}
        for item in inventory_data:
            history = []
            base = random.randint(20, 50)
            for i in range(60, 0, -1):
                date = datetime.now() - timedelta(days=i)
                value = base + random.randint(-10, 10)
                history.append((date, float(max(0, value))))
            sales_history[item["product_id"]] = history

        # Get recommendations
        recommendations = inventory_optimizer.optimize_inventory(
            inventory_data, sales_history, 30
        )

        # Update table
        self.table.setRowCount(len(recommendations))

        critical_count = 0
        for i, rec in enumerate(recommendations):
            if rec.urgency_level == "critical":
                critical_count += 1

            self.table.setItem(i, 0, QTableWidgetItem(rec.product_name))
            self.table.setItem(i, 1, QTableWidgetItem(str(rec.current_stock)))
            self.table.setItem(
                i, 2, QTableWidgetItem(str(rec.recommended_order_quantity))
            )
            self.table.setItem(i, 3, QTableWidgetItem(rec.urgency_level.upper()))

            days_str = (
                f"{rec.days_until_stockout:.1f}" if rec.days_until_stockout else "N/A"
            )
            self.table.setItem(i, 4, QTableWidgetItem(days_str))
            self.table.setItem(i, 5, QTableWidgetItem(str(rec.reorder_point)))
            self.table.setItem(i, 6, QTableWidgetItem(f"{rec.confidence_score:.0%}"))

        # Show alert if critical items
        if critical_count > 0:
            self.alert_banner.setText(
                f"⚠️ {critical_count} product(s) require immediate reorder!"
            )
            self.alert_banner.setVisible(True)
        else:
            self.alert_banner.setVisible(False)
