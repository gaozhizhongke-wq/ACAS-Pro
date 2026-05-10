#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ACAS Pro - Multi-Channel Alert Notifier
Enterprise alert notification system with WeChat Work, Email, SMS support
"""

import json
import smtplib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Optional, Callable
from enum import Enum

import requests

from ..core.logging import get_logger
from ..core.config import config

logger = get_logger(__name__)


class AlertChannel(Enum):
    """Alert delivery channels"""
    WECHAT_WORK = "wechat_work"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    DINGTALK = "dingtalk"
    FEISHU = "feishu"


class AlertPriority(Enum):
    """Alert priority levels"""
    P0_CRITICAL = "p0"
    P1_URGENT = "p1"
    P2_ATTENTION = "p2"
    P3_ROUTINE = "p3"


@dataclass
class AlertMessage:
    """Alert message structure"""
    title: str
    content: str
    priority: AlertPriority = AlertPriority.P3_ROUTINE
    category: str = "general"
    source: str = "acas"
    timestamp: datetime = None
    metadata: Dict = field(default_factory=dict)
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
    
    def to_markdown(self) -> str:
        """Format as markdown for WeChat Work"""
        priority_emoji = {
            AlertPriority.P0_CRITICAL: "🔴",
            AlertPriority.P1_URGENT: "🟠",
            AlertPriority.P2_ATTENTION: "🟡",
            AlertPriority.P3_ROUTINE: "🟢",
        }
        emoji = priority_emoji.get(self.priority, "⚪")
        
        return f"""{emoji} **{self.title}**

{self.content}

---
📅 时间: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
📂 分类: {self.category}
🔗 来源: {self.source}"""
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "content": self.content,
            "priority": self.priority.value,
            "category": self.category,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


class AlertNotifier:
    """
    Multi-channel alert notifier
    - WeChat Work (企业微信) webhook
    - DingTalk (钉钉) webhook
    - Feishu (飞书) webhook
    - Email SMTP
    - Custom webhook
    """
    
    def __init__(self):
        # Load configurations from config
        self.wechat_webhook = getattr(config, 'wechat_work_webhook', None)
        self.dingtalk_webhook = getattr(config, 'dingtalk_webhook', None)
        self.feishu_webhook = getattr(config, 'feishu_webhook', None)
        
        # Email config
        self.smtp_host = getattr(config, 'smtp_host', None)
        self.smtp_port = getattr(config, 'smtp_port', 587)
        self.smtp_user = getattr(config, 'smtp_user', None)
        self.smtp_password = getattr(config, 'smtp_password', None)
        
        # Channel enable flags
        self.enabled_channels = {
            AlertChannel.WECHAT_WORK: bool(self.wechat_webhook),
            AlertChannel.DINGTALK: bool(self.dingtalk_webhook),
            AlertChannel.FEISHU: bool(self.feishu_webhook),
            AlertChannel.EMAIL: bool(self.smtp_host and self.smtp_user),
        }
        
        # Alert history
        self._history: List[Dict] = []
        self._max_history = 1000
    
    def send(
        self,
        alert: AlertMessage,
        channels: List[AlertChannel] = None,
        force: bool = False
    ) -> Dict[AlertChannel, bool]:
        """
        Send alert through specified channels
        
        Args:
            alert: AlertMessage to send
            channels: Specific channels (None = auto-select by priority)
            force: Send even if channel is disabled
        
        Returns:
            Dict of channel -> success status
        """
        # Auto-select channels by priority if not specified
        if channels is None:
            channels = self._select_channels(alert.priority)
        
        results = {}
        
        for channel in channels:
            if not force and not self.enabled_channels.get(channel, False):
                logger.debug(f"Channel {channel.value} is disabled, skipping")
                results[channel] = False
                continue
            
            try:
                if channel == AlertChannel.WECHAT_WORK:
                    success = self._send_wechat(alert)
                elif channel == AlertChannel.DINGTALK:
                    success = self._send_dingtalk(alert)
                elif channel == AlertChannel.FEISHU:
                    success = self._send_feishu(alert)
                elif channel == AlertChannel.EMAIL:
                    success = self._send_email(alert)
                elif channel == AlertChannel.WEBHOOK:
                    success = self._send_webhook(alert)
                else:
                    success = False
                
                results[channel] = success
                
            except Exception as e:
                logger.error(f"Failed to send alert via {channel.value}: {e}")
                results[channel] = False
        
        # Record in history
        self._record_alert(alert, results)
        
        return results
    
    def _select_channels(self, priority: AlertPriority) -> List[AlertChannel]:
        """Select channels based on priority"""
        if priority == AlertPriority.P0_CRITICAL:
            # P0: All available channels
            return [c for c in AlertChannel if self.enabled_channels.get(c, False)]
        elif priority == AlertPriority.P1_URGENT:
            # P1: WeChat + DingTalk
            return [AlertChannel.WECHAT_WORK, AlertChannel.DINGTALK]
        elif priority == AlertPriority.P2_ATTENTION:
            # P2: WeChat only
            return [AlertChannel.WECHAT_WORK]
        else:
            # P3: WeChat only
            return [AlertChannel.WECHAT_WORK]
    
    def _send_wechat(self, alert: AlertMessage) -> bool:
        """Send via WeChat Work webhook"""
        if not self.wechat_webhook:
            return False
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "content": alert.to_markdown()
            }
        }
        
        response = requests.post(
            self.wechat_webhook,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('errcode') == 0:
                logger.info(f"WeChat alert sent: {alert.title}")
                return True
        
        logger.warning(f"WeChat alert failed: {response.text}")
        return False
    
    def _send_dingtalk(self, alert: AlertMessage) -> bool:
        """Send via DingTalk webhook"""
        if not self.dingtalk_webhook:
            return False
        
        payload = {
            "msgtype": "markdown",
            "markdown": {
                "title": alert.title,
                "text": alert.to_markdown()
            }
        }
        
        response = requests.post(
            self.dingtalk_webhook,
            json=payload,
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('errcode') == 0:
                logger.info(f"DingTalk alert sent: {alert.title}")
                return True
        
        return False
    
    def _send_feishu(self, alert: AlertMessage) -> bool:
        """Send via Feishu webhook"""
        if not self.feishu_webhook:
            return False
        
        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {
                        "tag": "plain_text",
                        "content": alert.title
                    },
                    "template": self._get_feishu_color(alert.priority)
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": alert.content
                    }
                ]
            }
        }
        
        response = requests.post(
            self.feishu_webhook,
            json=payload,
            timeout=10
        )
        
        return response.status_code == 200
    
    def _get_feishu_color(self, priority: AlertPriority) -> str:
        """Get Feishu card color for priority"""
        colors = {
            AlertPriority.P0_CRITICAL: "red",
            AlertPriority.P1_URGENT: "orange",
            AlertPriority.P2_ATTENTION: "yellow",
            AlertPriority.P3_ROUTINE: "blue",
        }
        return colors.get(priority, "blue")
    
    def _send_email(self, alert: AlertMessage, recipients: List[str] = None) -> bool:
        """Send via email SMTP"""
        if not self.smtp_host or not self.smtp_user:
            return False
        
        recipients = recipients or getattr(config, 'alert_email_recipients', [])
        if not recipients:
            return False
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"[{alert.priority.value.upper()}] {alert.title}"
        msg['From'] = self.smtp_user
        msg['To'] = ', '.join(recipients)
        
        # Plain text version
        text_content = f"{alert.title}\n\n{alert.content}\n\n时间: {alert.timestamp}"
        msg.attach(MIMEText(text_content, 'plain', 'utf-8'))
        
        # HTML version
        html_content = f"""
        <html>
        <body>
            <h2>{alert.title}</h2>
            <p>{alert.content}</p>
            <hr>
            <p><small>时间: {alert.timestamp} | 分类: {alert.category}</small></p>
        </body>
        </html>
        """
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        try:
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.smtp_user, recipients, msg.as_string())
            
            logger.info(f"Email alert sent to {len(recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False
    
    def _send_webhook(self, alert: AlertMessage, url: str = None) -> bool:
        """Send to custom webhook"""
        url = url or getattr(config, 'alert_webhook_url', None)
        if not url:
            return False
        
        payload = alert.to_dict()
        
        response = requests.post(url, json=payload, timeout=10)
        return response.status_code == 200
    
    def _record_alert(self, alert: AlertMessage, results: Dict[AlertChannel, bool]):
        """Record alert in history"""
        record = {
            "alert": alert.to_dict(),
            "channels": {c.value: s for c, s in results.items()},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        self._history.append(record)
        
        # Trim history
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
    
    def get_history(self, limit: int = 100) -> List[Dict]:
        """Get recent alert history"""
        return self._history[-limit:]
    
    def configure_channel(self, channel: AlertChannel, **kwargs):
        """Configure a specific channel"""
        if channel == AlertChannel.WECHAT_WORK:
            self.wechat_webhook = kwargs.get('webhook')
            self.enabled_channels[channel] = bool(self.wechat_webhook)
        elif channel == AlertChannel.DINGTALK:
            self.dingtalk_webhook = kwargs.get('webhook')
            self.enabled_channels[channel] = bool(self.dingtalk_webhook)
        elif channel == AlertChannel.FEISHU:
            self.feishu_webhook = kwargs.get('webhook')
            self.enabled_channels[channel] = bool(self.feishu_webhook)
        elif channel == AlertChannel.EMAIL:
            self.smtp_host = kwargs.get('host')
            self.smtp_port = kwargs.get('port', 587)
            self.smtp_user = kwargs.get('user')
            self.smtp_password = kwargs.get('password')
            self.enabled_channels[channel] = bool(self.smtp_host and self.smtp_user)
        
        logger.info(f"Configured {channel.value} channel")


# Global instance
alert_manager = AlertNotifier()


# Convenience functions
def send_critical_alert(title: str, content: str, **kwargs):
    """Send a critical (P0) alert"""
    alert = AlertMessage(
        title=title,
        content=content,
        priority=AlertPriority.P0_CRITICAL,
        **kwargs
    )
    return alert_manager.send(alert)


def send_urgent_alert(title: str, content: str, **kwargs):
    """Send an urgent (P1) alert"""
    alert = AlertMessage(
        title=title,
        content=content,
        priority=AlertPriority.P1_URGENT,
        **kwargs
    )
    return alert_manager.send(alert)


if __name__ == "__main__":
    # Test alert
    alert = AlertMessage(
        title="测试告警",
        content="这是一条测试告警消息，用于验证告警系统正常工作。",
        priority=AlertPriority.P2_ATTENTION,
        category="test"
    )
    
    results = alert_manager.send(alert)
    print(f"Alert sent: {results}")
