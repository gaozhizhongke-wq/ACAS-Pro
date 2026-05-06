#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Market Intelligence Page
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QComboBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from acas_pro.core.config import config
from acas_pro.sentiment.news_engine import market_intelligence


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


class IntelligencePage(QWidget):
    """Market intelligence page"""
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._load_intelligence()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(24)
        
        # Header
        header = QLabel("🌍 Market Intelligence")
        header.setFont(QFont(config.ui.font_family, 24, QFont.Bold))
        layout.addWidget(header)
        
        desc = QLabel("Real-time market news and risk monitoring")
        desc.setStyleSheet(f"color: {COLORS['text2']};")
        layout.addWidget(desc)
        
        # Filters
        filters = QGroupBox("Filters")
        filter_layout = QHBoxLayout(filters)
        
        filter_layout.addWidget(QLabel("Category:"))
        self.cat_combo = QComboBox()
        self.cat_combo.addItems(["All", "Business", "Technology", "Finance", "Logistics", "Disaster"])
        filter_layout.addWidget(self.cat_combo)
        
        filter_layout.addWidget(QLabel("Region:"))
        self.region_combo = QComboBox()
        self.region_combo.addItems(["Global", "North America", "Europe", "Asia Pacific", "MENA"])
        filter_layout.addWidget(self.region_combo)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: #fff;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
            }}
        """)
        refresh_btn.clicked.connect(self._load_intelligence)
        filter_layout.addWidget(refresh_btn)
        
        filter_layout.addStretch()
        layout.addWidget(filters)
        
        # News table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Time", "Category", "Title", "Source", "Sentiment", "Relevance"
        ])
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
            }}
            QHeaderView::section {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                padding: 12px;
                font-weight: bold;
            }}
            QTableWidget::item {{
                padding: 10px;
                color: {COLORS['text']};
            }}
        """)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
    
    def _load_intelligence(self):
        """Load market intelligence"""
        articles = market_intelligence.fetch_intelligence(max_items=50)
        
        self.table.setRowCount(len(articles))
        
        for i, article in enumerate(articles):
            self.table.setItem(i, 0, QTableWidgetItem(article.published_at.strftime("%m-%d %H:%M")))
            self.table.setItem(i, 1, QTableWidgetItem(article.category.value.title()))
            self.table.setItem(i, 2, QTableWidgetItem(article.title[:60] + "..."))
            self.table.setItem(i, 3, QTableWidgetItem(article.source))
            
            sentiment_text = "Neutral"
            if article.sentiment:
                sentiment_text = article.sentiment.overall_sentiment.value.replace("_", " ").title()
            self.table.setItem(i, 4, QTableWidgetItem(sentiment_text))
            
            self.table.setItem(i, 5, QTableWidgetItem(f"{article.relevance_score:.0%}"))
