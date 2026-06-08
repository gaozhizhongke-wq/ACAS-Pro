#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Market Intelligence Page (Enhanced)
Integrated with RSS collector, sentiment analysis, and brand reputation metrics
"""

from datetime import datetime
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem,
    QHeaderView, QGroupBox, QComboBox, QTabWidget,
    QProgressBar, QFrame, QScrollArea, QGridLayout,
    QSpinBox, QLineEdit, QMessageBox
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QColor

from ...core.config import config
from ...core.logging import get_logger
from ...sentiment.news_engine import market_intelligence

# Import new WorldMonitor modules
try:
    from ...collectors.rss_collector import rss_collector
    from ...alert.notifier import alert_manager, AlertMessage, AlertPriority, AlertChannel
    from ...metrics.brand_reputation import reputation_calculator, SentimentArticle
    WORLDMONITOR_ENABLED = True
except ImportError:
    WORLDMONITOR_ENABLED = False

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

class IntelligencePage(QWidget):
    """Market intelligence page with WorldMonitor integration"""
    
    # Signals
    alert_triggered = Signal(str, str)  # title, content
    
    def __init__(self):
        super().__init__()
        self._articles = []
        self._reputation_score = None
        self._setup_ui()
        self._load_intelligence()
        
        # Auto-refresh timer (every 5 minutes)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._auto_refresh)
        self._refresh_timer.start(300000)
    
    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(24)
        
        # Header
        header_layout = QHBoxLayout()
        header = QLabel("🌍 Market Intelligence")
        header.setFont(QFont(config.ui.font_family, 24, QFont.Bold))
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Reputation score badge
        self.score_label = QLabel("--")
        self.score_label.setFont(QFont(config.ui.font_family, 16, QFont.Bold))
        self.score_label.setStyleSheet(f"""
            QLabel {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                padding: 8px 16px;
                border-radius: 8px;
            }}
        """)
        header_layout.addWidget(self.score_label)
        
        layout.addLayout(header_layout)
        
        # Tabs
        tabs = QTabWidget()
        tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {COLORS['border']};
                border-radius: 8px;
                background-color: {COLORS['card']};
            }}
            QTabBar::tab {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                padding: 12px 24px;
                margin-right: 4px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }}
            QTabBar::tab:selected {{
                background-color: {COLORS['accent']};
                color: #fff;
            }}
        """)
        
        # Tab 1: News Feed
        tabs.addTab(self._create_news_tab(), "📰 News Feed")
        
        # Tab 2: Reputation Dashboard
        tabs.addTab(self._create_reputation_tab(), "📊 Reputation")
        
        # Tab 3: Alerts
        tabs.addTab(self._create_alerts_tab(), "🚨 Alerts")
        
        # Tab 4: Settings
        tabs.addTab(self._create_settings_tab(), "⚙️ Settings")
        
        layout.addWidget(tabs, 1)
    
    def _create_news_tab(self) -> QWidget:
        """Create news feed tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
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
        
        filter_layout.addWidget(QLabel("Hours:"))
        self.hours_spin = QSpinBox()
        self.hours_spin.setRange(1, 168)
        self.hours_spin.setValue(24)
        filter_layout.addWidget(self.hours_spin)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {COLORS['accent']};
                color: #fff;
                border: none;
                padding: 10px 24px;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: #4c90d9;
            }}
        """)
        refresh_btn.clicked.connect(self._load_intelligence)
        filter_layout.addWidget(refresh_btn)
        
        # RSS refresh button (if WorldMonitor enabled)
        if WORLDMONITOR_ENABLED:
            rss_btn = QPushButton("📡 Fetch RSS")
            rss_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {COLORS['success']};
                    color: #fff;
                    border: none;
                    padding: 10px 24px;
                    border-radius: 6px;
                }}
            """)
            rss_btn.clicked.connect(self._fetch_rss)
            filter_layout.addWidget(rss_btn)
        
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
                gridline-mode: none;
            }}
            QHeaderView::section {{
                background-color: {COLORS['surface']};
                color: {COLORS['text']};
                padding: 12px;
                font-weight: bold;
                border: none;
            }}
            QTableWidget::item {{
                padding: 10px;
                color: {COLORS['text']};
                border-bottom: 1px solid {COLORS['border']};
            }}
            QTableWidget::item:selected {{
                background-color: {COLORS['accent']};
                color: #fff;
            }}
        """)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        layout.addWidget(self.table, 1)
        
        return widget
    
    def _create_reputation_tab(self) -> QWidget:
        """Create reputation dashboard tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(20)
        
        # Score card
        score_card = QFrame()
        score_card.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['card']};
                border: 1px solid {COLORS['border']};
                border-radius: 12px;
                padding: 20px;
            }}
        """)
        score_layout = QGridLayout(score_card)
        
        # Main score
        self.main_score = QLabel("50")
        self.main_score.setFont(QFont(config.ui.font_family, 48, QFont.Bold))
        self.main_score.setAlignment(Qt.AlignCenter)
        score_layout.addWidget(self.main_score, 0, 0, 2, 1)
        
        self.grade_label = QLabel("Grade: C")
        self.grade_label.setFont(QFont(config.ui.font_family, 16))
        self.grade_label.setAlignment(Qt.AlignCenter)
        score_layout.addWidget(self.grade_label, 2, 0)
        
        # Stats
        stats_frame = QFrame()
        stats_layout = QGridLayout(stats_frame)
        
        self.positive_count = QLabel("0 positive")
        self.neutral_count = QLabel("0 neutral")
        self.negative_count = QLabel("0 negative")
        self.trend_label = QLabel("→ Stable")
        
        for label in [self.positive_count, self.neutral_count, self.negative_count, self.trend_label]:
            label.setFont(QFont(config.ui.font_family, 14))
        
        stats_layout.addWidget(QLabel("📈 Positive:"), 0, 0)
        stats_layout.addWidget(self.positive_count, 0, 1)
        stats_layout.addWidget(QLabel("➖ Neutral:"), 1, 0)
        stats_layout.addWidget(self.neutral_count, 1, 1)
        stats_layout.addWidget(QLabel("📉 Negative:"), 2, 0)
        stats_layout.addWidget(self.negative_count, 2, 1)
        stats_layout.addWidget(QLabel("📊 Trend:"), 3, 0)
        stats_layout.addWidget(self.trend_label, 3, 1)
        
        score_layout.addWidget(stats_frame, 0, 1, 3, 1)
        layout.addWidget(score_card)
        
        # Platform breakdown
        platform_group = QGroupBox("Platform Breakdown")
        platform_layout = QVBoxLayout(platform_group)
        
        self.platform_table = QTableWidget()
        self.platform_table.setColumnCount(2)
        self.platform_table.setHorizontalHeaderLabels(["Platform", "Score"])
        self.platform_table.horizontalHeader().setStretchLastSection(True)
        platform_layout.addWidget(self.platform_table)
        
        layout.addWidget(platform_group)
        
        return widget
    
    def _create_alerts_tab(self) -> QWidget:
        """Create alerts configuration tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(16)
        
        # Alert channels config
        channels_group = QGroupBox("Alert Channels")
        channels_layout = QGridLayout(channels_group)
        
        # WeChat Work
        channels_layout.addWidget(QLabel("企业微信 Webhook:"), 0, 0)
        self.wechat_input = QLineEdit()
        self.wechat_input.setPlaceholderText("https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx")
        channels_layout.addWidget(self.wechat_input, 0, 1)
        
        test_wechat_btn = QPushButton("Test")
        test_wechat_btn.clicked.connect(self._test_wechat_alert)
        channels_layout.addWidget(test_wechat_btn, 0, 2)
        
        # DingTalk
        channels_layout.addWidget(QLabel("钉钉 Webhook:"), 1, 0)
        self.dingtalk_input = QLineEdit()
        self.dingtalk_input.setPlaceholderText("https://oapi.dingtalk.com/robot/send?access_token=xxx")
        channels_layout.addWidget(self.dingtalk_input, 1, 1)
        
        # Email
        channels_layout.addWidget(QLabel("Email SMTP:"), 2, 0)
        self.smtp_input = QLineEdit()
        self.smtp_input.setPlaceholderText("smtp.example.com:587")
        channels_layout.addWidget(self.smtp_input, 2, 1)
        
        layout.addWidget(channels_group)
        
        # Alert thresholds
        thresholds_group = QGroupBox("Alert Thresholds")
        thresholds_layout = QGridLayout(thresholds_group)
        
        thresholds_layout.addWidget(QLabel("Critical Score <"), 0, 0)
        self.critical_threshold = QSpinBox()
        self.critical_threshold.setRange(0, 100)
        self.critical_threshold.setValue(60)
        thresholds_layout.addWidget(self.critical_threshold, 0, 1)
        
        thresholds_layout.addWidget(QLabel("Warning Score <"), 1, 0)
        self.warning_threshold = QSpinBox()
        self.warning_threshold.setRange(0, 100)
        self.warning_threshold.setValue(70)
        thresholds_layout.addWidget(self.warning_threshold, 1, 1)
        
        layout.addWidget(thresholds_group)
        
        # Alert history
        history_group = QGroupBox("Recent Alerts")
        history_layout = QVBoxLayout(history_group)
        
        self.alert_table = QTableWidget()
        self.alert_table.setColumnCount(3)
        self.alert_table.setHorizontalHeaderLabels(["Time", "Alert", "Status"])
        self.alert_table.horizontalHeader().setStretchLastSection(True)
        history_layout.addWidget(self.alert_table)
        
        layout.addWidget(history_group)
        
        return widget
    
    def _create_settings_tab(self) -> QWidget:
        """Create settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # RSS Sources
        rss_group = QGroupBox("RSS Sources")
        rss_layout = QVBoxLayout(rss_group)
        
        rss_info = QLabel("RSS sources are configured in collectors/rss_collector.py\n"
                         "Current sources: Sina Finance, Tencent, 36Kr, FT Chinese, Reuters, Bloomberg")
        rss_info.setStyleSheet(f"color: {COLORS['text2']};")
        rss_layout.addWidget(rss_info)
        
        layout.addWidget(rss_group)
        
        # Auto-refresh
        refresh_group = QGroupBox("Auto Refresh")
        refresh_layout = QGridLayout(refresh_group)
        
        refresh_layout.addWidget(QLabel("Refresh Interval (minutes):"), 0, 0)
        self.refresh_interval = QSpinBox()
        self.refresh_interval.setRange(1, 60)
        self.refresh_interval.setValue(5)
        self.refresh_interval.valueChanged.connect(self._update_refresh_interval)
        refresh_layout.addWidget(self.refresh_interval, 0, 1)
        
        layout.addWidget(refresh_group)
        
        layout.addStretch()
        
        return widget
    
    def _load_intelligence(self) -> None:
        """Load market intelligence"""
        try:
            articles = market_intelligence.fetch_intelligence(max_items=50)
            self._articles = articles
            
            self.table.setRowCount(len(articles))
            
            for i, article in enumerate(articles):
                self.table.setItem(i, 0, QTableWidgetItem(article.published_at.strftime("%m-%d %H:%M")))
                self.table.setItem(i, 1, QTableWidgetItem(article.category.value.title()))
                self.table.setItem(i, 2, QTableWidgetItem(article.title[:60] + "..."))
                self.table.setItem(i, 3, QTableWidgetItem(article.source))
                
                sentiment_text = "Neutral"
                sentiment_color = COLORS['text']
                if article.sentiment:
                    sentiment_text = article.sentiment.overall_sentiment.value.replace("_", " ").title()
                    if "positive" in sentiment_text.lower():
                        sentiment_color = COLORS['success']
                    elif "negative" in sentiment_text.lower():
                        sentiment_color = COLORS['danger']
                
                sentiment_item = QTableWidgetItem(sentiment_text)
                sentiment_item.setForeground(QColor(sentiment_color))
                self.table.setItem(i, 4, sentiment_item)
                
                self.table.setItem(i, 5, QTableWidgetItem(f"{article.relevance_score:.0%}"))
            
            # Update reputation if WorldMonitor enabled
            if WORLDMONITOR_ENABLED:
                self._update_reputation()
                
        except Exception as e:
            logger.error(f"Failed to load intelligence: {e}")
    
    def _fetch_rss(self) -> None:
        """Fetch RSS feeds"""
        if not WORLDMONITOR_ENABLED:
            QMessageBox.warning(self, "Error", "WorldMonitor modules not available")
            return
        
        try:
            hours = self.hours_spin.value()
            articles = rss_collector.collect(hours_back=hours, max_per_source=20)
            
            QMessageBox.information(
                self,
                "RSS Fetched",
                f"Collected {len(articles)} articles from RSS feeds"
            )
            
            # Refresh intelligence
            self._load_intelligence()
            
        except Exception as e:
            logger.error(f"RSS fetch failed: {e}")
            QMessageBox.warning(self, "Error", f"RSS fetch failed: {str(e)}")
    
    def _update_reputation(self) -> None:
        """Update reputation score from articles"""
        if not WORLDMONITOR_ENABLED or not self._articles:
            return
        
        # Convert articles to SentimentArticle format
        sentiment_articles = []
        for article in self._articles:
            if article.sentiment:
                sentiment_articles.append(SentimentArticle(
                    id=str(hash(article.title)),
                    title=article.title,
                    content=article.content or "",
                    source=article.source,
                    published_at=article.published_at,
                    sentiment_score=article.sentiment.score if hasattr(article.sentiment, 'score') else 0,
                    sentiment_level=self._map_sentiment_level(article.sentiment.overall_sentiment.value),
                    platform=article.source.lower()
                ))
        
        if sentiment_articles:
            self._reputation_score = reputation_calculator.calculate(
                sentiment_articles,
                previous_score=float(self.main_score.text()) if self.main_score.text() != "--" else None
            )
            
            # Update UI
            self.main_score.setText(f"{self._reputation_score.score:.0f}")
            self.grade_label.setText(f"Grade: {self._reputation_score.grade}")
            
            self.positive_count.setText(f"{self._reputation_score.positive_count} positive")
            self.neutral_count.setText(f"{self._reputation_score.neutral_count} neutral")
            self.negative_count.setText(f"{self._reputation_score.negative_count} negative")
            
            trend_icon = "↑" if self._reputation_score.trend == "improving" else "↓" if self._reputation_score.trend == "declining" else "→"
            self.trend_label.setText(f"{trend_icon} {self._reputation_score.trend.title()}")
            
            # Update score badge color
            if self._reputation_score.score >= 80:
                color = COLORS['success']
            elif self._reputation_score.score >= 60:
                color = COLORS['warning']
            else:
                color = COLORS['danger']
            
            self.main_score.setStyleSheet(f"color: {color};")
            self.score_label.setText(f"Score: {self._reputation_score.score:.0f}")
            
            # Update platform table
            self.platform_table.setRowCount(len(self._reputation_score.platform_breakdown))
            for i, (platform, score) in enumerate(self._reputation_score.platform_breakdown.items()):
                self.platform_table.setItem(i, 0, QTableWidgetItem(platform.title()))
                self.platform_table.setItem(i, 1, QTableWidgetItem(f"{score:.1f}"))
            
            # Check for alerts
            self._check_alerts()
    
    def _map_sentiment_level(self, level: str) -> str:
        """Map sentiment level to reputation calculator format"""
        mapping = {
            "very_positive": "very_positive",
            "positive": "positive",
            "neutral": "neutral",
            "negative": "negative",
            "very_negative": "very_negative"
        }
        return mapping.get(level.lower(), "neutral")
    
    def _check_alerts(self) -> None:
        """Check and send alerts based on reputation score"""
        if not WORLDMONITOR_ENABLED or not self._reputation_score:
            return
        
        alert_status = reputation_calculator.get_alert_status(self._reputation_score)
        
        if alert_status['has_alerts']:
            for alert in alert_status['alerts']:
                if alert['level'] == 'critical':
                    priority = AlertPriority.P0_CRITICAL
                elif alert['level'] == 'warning':
                    priority = AlertPriority.P1_URGENT
                else:
                    priority = AlertPriority.P2_ATTENTION
                
                alert_msg = AlertMessage(
                    title="品牌口碑告警",
                    content=alert['message'],
                    priority=priority,
                    category="reputation"
                )
                
                alert_manager.send(alert_msg)
                self.alert_triggered.emit(alert_msg.title, alert_msg.content)
    
    def _test_wechat_alert(self) -> None:
        """Test WeChat Work alert"""
        if not WORLDMONITOR_ENABLED:
            QMessageBox.warning(self, "Error", "WorldMonitor modules not available")
            return
        
        webhook = self.wechat_input.text().strip()
        if not webhook:
            QMessageBox.warning(self, "Error", "Please enter WeChat Work webhook URL")
            return
        
        # Configure and test
        alert_manager.configure_channel(AlertChannel.WECHAT_WORK, webhook=webhook)
        
        test_alert = AlertMessage(
            title="测试告警",
            content="这是一条来自 ACAS Pro 的测试告警消息。",
            priority=AlertPriority.P3_ROUTINE,
            category="test"
        )
        
        results = alert_manager.send(test_alert)
        
        if results.get(AlertChannel.WECHAT_WORK):
            QMessageBox.information(self, "Success", "Test alert sent successfully!")
        else:
            QMessageBox.warning(self, "Failed", "Failed to send test alert")
    
    def _update_refresh_interval(self, minutes: int) -> None:
        """Update auto-refresh interval"""
        self._refresh_timer.setInterval(minutes * 60 * 1000)
    
    def _auto_refresh(self) -> None:
        """Auto-refresh handler"""
        self._load_intelligence()
