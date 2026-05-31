#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Sales Forecast Page
TimesFM-powered sales forecasting
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QSpinBox, QTableWidget,
    QTableWidgetItem, QHeaderView, QGroupBox, QTextEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from datetime import datetime, timedelta
import random

from ...core.config import config
from ...ml.timesfm_engine import timesfm_engine, ForecastResult

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
}

class ForecastPage(QWidget):
    """Sales forecast page with TimesFM"""
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._generate_sample_forecast()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(24)
        
        # Header
        header = QLabel("📈 Sales Forecast")
        header.setFont(QFont(config.ui.font_family, 24, QFont.Bold))
        layout.addWidget(header)
        
        desc = QLabel("AI-powered sales forecasting using TimesFM engine")
        desc.setStyleSheet(f"color: {COLORS['text2']};")
        layout.addWidget(desc)
        
        # Controls
        controls = QGroupBox("Forecast Settings")
        controls.setStyleSheet(f"""
            QGroupBox {{
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }}
        """)
        
        ctrl_layout = QHBoxLayout(controls)
        
        ctrl_layout.addWidget(QLabel("Product:"))
        self.product_combo = QComboBox()
        self.product_combo.addItems(["All Products", "Product A", "Product B", "Product C"])
        ctrl_layout.addWidget(self.product_combo)
        
        ctrl_layout.addWidget(QLabel("Period:"))
        self.days_spin = QSpinBox()
        self.days_spin.setRange(7, 90)
        self.days_spin.setValue(30)
        ctrl_layout.addWidget(self.days_spin)
        
        ctrl_layout.addWidget(QLabel("Region:"))
        self.region_combo = QComboBox()
        self.region_combo.addItems(["Global", "North America", "Europe", "Asia Pacific"])
        ctrl_layout.addWidget(self.region_combo)
        
        generate_btn = QPushButton("Generate Forecast")
        generate_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: #fff;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #79c0ff;
            }}
        """)
        generate_btn.clicked.connect(self._generate_forecast)
        ctrl_layout.addWidget(generate_btn)
        
        ctrl_layout.addStretch()
        layout.addWidget(controls)
        
        # Results table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Date", "Predicted Sales", "Lower Bound", "Upper Bound", "Confidence"
        ])
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                gridline-color: {COLORS['border']};
            }}
            QHeaderView::section {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                padding: 12px;
                border: none;
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: 10px;
                color: {COLORS['text']};
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['accent']};
            }}
        """)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        
        # Summary
        self.summary = QTextEdit()
        self.summary.setReadOnly(True)
        self.summary.setMaximumHeight(100)
        self.summary.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['card']};
                color: {COLORS['text']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                padding: 12px;
            }}
        """)
        layout.addWidget(self.summary)
    
    def _generate_sample_forecast(self):
        """Generate sample forecast data"""
        # Create sample historical data
        history = []
        base = 1000
        for i in range(60, 0, -1):
            date = datetime.now() - timedelta(days=i)
            trend = (60 - i) * 5
            seasonal = 100 if date.weekday() < 5 else -50
            noise = random.randint(-30, 30)
            value = max(0, base + trend + seasonal + noise)
            history.append((date, float(value)))
        
        # Generate forecast
        result = timesfm_engine.forecast("SAMPLE-001", history, 30)
        self._display_result(result)
    
    def _generate_forecast(self):
        """Generate forecast from user input"""
        self._generate_sample_forecast()
    
    def _display_result(self, result: ForecastResult):
        """Display forecast result"""
        # Update table
        self.table.setRowCount(len(result.forecast))
        
        for i, point in enumerate(result.forecast):
            self.table.setItem(i, 0, QTableWidgetItem(point.timestamp.strftime("%Y-%m-%d")))
            self.table.setItem(i, 1, QTableWidgetItem(f"{point.value:,.0f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{point.lower_bound:,.0f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{point.upper_bound:,.0f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{point.confidence:.0%}"))
        
        # Update summary
        trend_icon = "📈" if result.trend_direction == "up" else ("📉" if result.trend_direction == "down" else "➡️")
        summary_text = f"""
        <b>Forecast Summary</b><br>
        Trend: {trend_icon} {result.trend_direction.title()} ({result.trend_magnitude:.1f}%)<br>
        Seasonality Detected: {'Yes' if result.seasonality_detected else 'No'}<br>
        Model: {result.model_version}<br>
        Generated: {result.generated_at.strftime('%Y-%m-%d %H:%M')}
        """
        self.summary.setHtml(summary_text)
