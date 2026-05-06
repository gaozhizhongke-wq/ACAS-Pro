# ACAS Pro - 企业级自动获客系统
# 版权所有 (c) 2026 高智中科（北京）科技有限公司

"""
多渠道告警通知模块
支持：钉钉、企业微信、飞书、邮件
"""

import json
import time
import hashlib
import logging
import smtplib
import hmac
import base64
import urllib.parse
import urllib.request
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class NotifyChannel(Enum):
    """通知渠道"""
    DINGTALK = "dingtalk"
    WECHAT = "wechat"
    FEISHU = "feishu"
    EMAIL = "email"


@dataclass
class AlertMessage:
    """告警消息"""
    title: str
    content: str
    level: AlertLevel = AlertLevel.INFO
    source: str = "acas-pro"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    labels: Dict[str, str] = field(default_factory=dict)
    fingerprint: str = ""

    def __post_init__(self):
        if not self.fingerprint:
            raw = f"{self.title}:{self.source}:{json.dumps(self.labels, sort_keys=True)}"
            self.fingerprint = hashlib.md5(raw.encode()).hexdigest()[:12]


@dataclass
class AlertRule:
    """告警路由规则"""
    level: AlertLevel
    channels: List[NotifyChannel]
    at_users: List[str] = field(default_factory=list)
    escalate_after_minutes: int = 0
    escalate_to: Optional[AlertLevel] = None


class AlertAggregator:
    """告警聚合与去重"""

    def __init__(self, window_seconds: int = 300, max_alerts_per_fingerprint: int = 10):
        self.window_seconds = window_seconds
        self.max_alerts = max_alerts_per_fingerprint
        self._alerts: Dict[str, List[datetime]] = defaultdict(list)
        self._muted: Dict[str, datetime] = {}

    def should_send(self, alert: AlertMessage) -> bool:
        now = datetime.now()
        fp = alert.fingerprint

        # 检查是否被静默
        if fp in self._muted and now < self._muted[fp]:
            return False

        # 窗口内去重
        cutoff = now - timedelta(seconds=self.window_seconds)
        self._alerts[fp] = [t for t in self._alerts[fp] if t > cutoff]

        if len(self._alerts[fp]) >= self.max_alerts:
            return False

        self._alerts[fp].append(now)
        return True

    def mute(self, fingerprint: str, duration_minutes: int = 30):
        self._muted[fingerprint] = datetime.now() + timedelta(minutes=duration_minutes)

    def unmute(self, fingerprint: str):
        self._muted.pop(fingerprint, None)


class AlertEscalator:
    """告警升级机制"""

    def __init__(self):
        self._pending: Dict[str, Dict] = {}

    def track(self, alert: AlertMessage, rule: AlertRule):
        if rule.escalate_after_minutes > 0 and rule.escalate_to:
            self._pending[alert.fingerprint] = {
                "alert": alert,
                "rule": rule,
                "escalate_at": datetime.now() + timedelta(minutes=rule.escalate_after_minutes),
                "original_level": alert.level,
                "resolved": False
            }

    def resolve(self, fingerprint: str):
        if fingerprint in self._pending:
            self._pending[fingerprint]["resolved"] = True

    def check_escalations(self) -> List[tuple]:
        now = datetime.now()
        escalated = []
        for fp, item in list(self._pending.items()):
            if item["resolved"]:
                continue
            if now >= item["escalate_at"]:
                alert = item["alert"]
                new_level = item["rule"].escalate_to
                alert.level = new_level
                escalated.append((alert, item["rule"]))
                del self._pending[fp]
        return escalated


class DingTalkNotifier:
    """钉钉机器人通知"""

    def __init__(self, webhook: str, secret: str = None):
        self.webhook = webhook
        self.secret = secret

    def _sign(self) -> str:
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        return f"{timestamp}&{sign}"

    def send(self, alert: AlertMessage, at_users: List[str] = None) -> bool:
        try:
            url = self.webhook
            if self.secret:
                url = f"{url}&{self._sign()}"

            level_emoji = {"critical": "🔴", "warning": "🟡", "info": "🔵"}
            emoji = level_emoji.get(alert.level.value, "⚪")

            content_text = (
                f"{emoji} **{alert.title}**\n\n"
                f"**级别**: {alert.level.value.upper()}\n"
                f"**来源**: {alert.source}\n"
                f"**时间**: {alert.timestamp}\n\n"
                f"{alert.content}"
            )

            data = {
                "msgtype": "markdown",
                "markdown": {
                    "title": f"{emoji} {alert.title}",
                    "text": content_text
                },
                "at": {}
            }

            if at_users:
                data["at"] = {
                    "atMobiles": at_users,
                    "isAtAll": False
                }

            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                if result.get("errcode") == 0:
                    logger.info("钉钉通知发送成功: %s", alert.title)
                    return True
                else:
                    logger.error("钉钉通知失败: %s", result)
                    return False
        except Exception as e:
            logger.error("钉钉通知异常: %s", e)
            return False


class WeChatNotifier:
    """企业微信机器人通知"""

    def __init__(self, webhook: str):
        self.webhook = webhook

    def send(self, alert: AlertMessage, at_users: List[str] = None) -> bool:
        try:
            level_color = {
                "critical": "warning",
                "warning": "comment",
                "info": "info"
            }
            color = level_color.get(alert.level.value, "comment")

            content = (
                f'<font color="{color}">{alert.level.value.upper()}</font> '
                f'**{alert.title}**\n'
                f'> 来源: {alert.source}\n'
                f'> 时间: {alert.timestamp}\n\n'
                f'{alert.content}'
            )

            data = {
                "msgtype": "markdown",
                "markdown": {"content": content}
            }

            if at_users:
                mentioned_list = at_users if at_users else []
                data["markdown"]["mentioned_mobile_list"] = mentioned_list

            req = urllib.request.Request(
                self.webhook,
                data=json.dumps(data).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                if result.get("errcode") == 0:
                    logger.info("企业微信通知发送成功: %s", alert.title)
                    return True
                else:
                    logger.error("企业微信通知失败: %s", result)
                    return False
        except Exception as e:
            logger.error("企业微信通知异常: %s", e)
            return False


class FeishuNotifier:
    """飞书机器人通知"""

    def __init__(self, webhook: str, secret: str = None):
        self.webhook = webhook
        self.secret = secret

    def _sign(self) -> str:
        timestamp = str(round(time.time()))
        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            self.secret.encode("utf-8"),
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        ).digest()
        sign = base64.b64encode(hmac_code).decode("utf-8")
        return timestamp, sign

    def send(self, alert: AlertMessage, at_users: List[str] = None) -> bool:
        try:
            url = self.webhook
            headers = {"Content-Type": "application/json"}

            if self.secret:
                ts, sign = self._sign()
                url = f"{url}&timestamp={ts}&sign={sign}"

            level_tag = {
                "critical": "<font color='red'>🔴 CRITICAL</font>",
                "warning": "<font color='orange'>🟡 WARNING</font>",
                "info": "<font color='blue'>🔵 INFO</font>"
            }
            tag = level_tag.get(alert.level.value, alert.level.value)

            content = (
                f"{tag} **{alert.title}**\n\n"
                f"**来源**: {alert.source}\n"
                f"**时间**: {alert.timestamp}\n\n"
                f"{alert.content}"
            )

            data = {
                "msg_type": "interactive",
                "card": {
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": content
                        }
                    ],
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": f"ACAS Pro 告警 - {alert.title}"
                        },
                        "template": "red" if alert.level == AlertLevel.CRITICAL else "orange" if alert.level == AlertLevel.WARNING else "blue"
                    }
                }
            }

            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                result = json.loads(resp.read().decode())
                if result.get("code") == 0:
                    logger.info("飞书通知发送成功: %s", alert.title)
                    return True
                else:
                    logger.error("飞书通知失败: %s", result)
                    return False
        except Exception as e:
            logger.error("飞书通知异常: %s", e)
            return False


class EmailNotifier:
    """邮件通知"""

    def __init__(self, smtp_host: str, smtp_port: int = 465,
                 username: str = None, password: str = None,
                 use_tls: bool = True, from_addr: str = ""):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.from_addr = from_addr or username

    def send(self, alert: AlertMessage, recipients: List[str] = None) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[ACAS Pro {alert.level.value.upper()}] {alert.title}"
            msg["From"] = self.from_addr
            msg["To"] = ", ".join(recipients or [])

            level_colors = {
                "critical": "#dc3545",
                "warning": "#ffc107",
                "info": "#17a2b8"
            }
            color = level_colors.get(alert.level.value, "#6c757d")

            html = f"""
            <html><body>
            <div style="border-left:4px solid {color};padding:12px;margin:10px 0;">
                <h2 style="color:{color};margin:0 0 8px 0;">{alert.level.value.upper()}: {alert.title}</h2>
                <p><strong>来源:</strong> {alert.source}</p>
                <p><strong>时间:</strong> {alert.timestamp}</p>
                <hr>
                <p>{alert.content.replace(chr(10), '<br>')}</p>
            </div>
            </body></html>
            """

            text = f"[{alert.level.value.upper()}] {alert.title}\n来源: {alert.source}\n时间: {alert.timestamp}\n\n{alert.content}"

            msg.attach(MIMEText(text, "plain", "utf-8"))
            msg.attach(MIMEText(html, "html", "utf-8"))

            if self.use_tls:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                server.starttls()

            if self.username and self.password:
                server.login(self.username, self.password)

            server.sendmail(self.from_addr, recipients or [], msg.as_string())
            server.quit()

            logger.info("邮件通知发送成功: %s -> %s", alert.title, recipients)
            return True
        except Exception as e:
            logger.error("邮件通知异常: %s", e)
            return False


class NotificationManager:
    """统一通知管理器"""

    DEFAULT_RULES = {
        AlertLevel.CRITICAL: AlertRule(
            level=AlertLevel.CRITICAL,
            channels=[NotifyChannel.DINGTALK, NotifyChannel.WECHAT, NotifyChannel.EMAIL],
            escalate_after_minutes=15,
            escalate_to=None
        ),
        AlertLevel.WARNING: AlertRule(
            level=AlertLevel.WARNING,
            channels=[NotifyChannel.DINGTALK, NotifyChannel.WECHAT],
            escalate_after_minutes=30,
            escalate_to=AlertLevel.CRITICAL
        ),
        AlertLevel.INFO: AlertRule(
            level=AlertLevel.INFO,
            channels=[NotifyChannel.FEISHU]
        ),
    }

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.notifiers: Dict[NotifyChannel, Any] = {}
        self.rules: Dict[AlertLevel, AlertRule] = dict(self.DEFAULT_RULES)
        self.aggregator = AlertAggregator()
        self.escalator = AlertEscalator()
        self.email_recipients: List[str] = []

        self._init_notifiers()

    def _init_notifiers(self):
        cfg = self.config

        if cfg.get("dingtalk_webhook"):
            self.notifiers[NotifyChannel.DINGTALK] = DingTalkNotifier(
                webhook=cfg["dingtalk_webhook"],
                secret=cfg.get("dingtalk_secret", "")
            )

        if cfg.get("wechat_webhook"):
            self.notifiers[NotifyChannel.WECHAT] = WeChatNotifier(
                webhook=cfg["wechat_webhook"]
            )

        if cfg.get("feishu_webhook"):
            self.notifiers[NotifyChannel.FEISHU] = FeishuNotifier(
                webhook=cfg["feishu_webhook"],
                secret=cfg.get("feishu_secret", "")
            )

        if cfg.get("smtp_host"):
            self.notifiers[NotifyChannel.EMAIL] = EmailNotifier(
                smtp_host=cfg["smtp_host"],
                smtp_port=cfg.get("smtp_port", 465),
                username=cfg.get("smtp_user", ""),
                password=cfg.get("smtp_pass", ""),
                use_tls=cfg.get("smtp_tls", True),
                from_addr=cfg.get("smtp_from", "")
            )
            self.email_recipients = cfg.get("email_recipients", [])

    def send_alert(self, alert: AlertMessage) -> Dict[str, bool]:
        results = {}

        # 告警聚合去重
        if not self.aggregator.should_send(alert):
            logger.info("告警被聚合过滤: %s (fingerprint=%s)", alert.title, alert.fingerprint)
            return results

        # 获取路由规则
        rule = self.rules.get(alert.level)
        if not rule:
            logger.warning("无告警路由规则: %s", alert.level)
            return results

        # 跟踪升级
        self.escalator.track(alert, rule)

        # 按渠道发送
        for channel in rule.channels:
            notifier = self.notifiers.get(channel)
            if not notifier:
                logger.warning("通知渠道未配置: %s", channel.value)
                results[channel.value] = False
                continue

            try:
                if channel == NotifyChannel.EMAIL:
                    success = notifier.send(alert, self.email_recipients)
                else:
                    success = notifier.send(alert, rule.at_users)
                results[channel.value] = success
            except Exception as e:
                logger.error("发送通知失败 [%s]: %s", channel.value, e)
                results[channel.value] = False

        return results

    def resolve_alert(self, fingerprint: str):
        self.escalator.resolve(fingerprint)

    def mute_alert(self, fingerprint: str, duration_minutes: int = 30):
        self.aggregator.mute(fingerprint, duration_minutes)

    def check_escalations(self):
        escalated = self.escalator.check_escalations()
        for alert, rule in escalated:
            logger.warning("告警升级: %s -> %s", alert.fingerprint, alert.level.value)
            self.send_alert(alert)

    @classmethod
    def from_env(cls) -> "NotificationManager":
        """从环境变量创建"""
        import os
        from dotenv import load_dotenv
        load_dotenv()

        config = {
            "dingtalk_webhook": os.getenv("DINGTALK_WEBHOOK", ""),
            "dingtalk_secret": os.getenv("DINGTALK_SECRET", ""),
            "wechat_webhook": os.getenv("WECHAT_WEBHOOK", ""),
            "feishu_webhook": os.getenv("FEISHU_WEBHOOK", ""),
            "feishu_secret": os.getenv("FEISHU_SECRET", ""),
            "smtp_host": os.getenv("SMTP_HOST", ""),
            "smtp_port": int(os.getenv("SMTP_PORT", "465")),
            "smtp_user": os.getenv("SMTP_USER", ""),
            "smtp_pass": os.getenv("SMTP_PASS", ""),
            "smtp_tls": os.getenv("SMTP_TLS", "true").lower() == "true",
            "smtp_from": os.getenv("SMTP_FROM", ""),
            "email_recipients": [e.strip() for e in os.getenv("EMAIL_RECIPIENTS", "").split(",") if e.strip()],
        }
        return cls(config)
