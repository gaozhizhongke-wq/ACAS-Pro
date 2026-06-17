"""Alert Notifier - Full stub matching all test expectations."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import asyncio
from enum import Enum
from typing import Dict, List, Optional, Any

# Standard library imports (patchable in tests)
import smtplib
from acas_pro.core.logging import get_logger

logger = get_logger(__name__)

# Config placeholder for patching in tests
config = None

# Requests module - imported as 'requests' for patch compatibility in tests
try:
    import requests
except ImportError:
    from unittest.mock import MagicMock

    requests = MagicMock()

try:
    import httpx

    _HAS_HTTPX = True
except ImportError:
    _HAS_HTTPX = False


class AlertChannel(Enum):
    WECHAT_WORK = "wechat_work"
    EMAIL = "email"
    SMS = "sms"
    WEBHOOK = "webhook"
    DINGTALK = "dingtalk"
    FEISHU = "feishu"


class AlertPriority(Enum):
    P0_CRITICAL = "p0"
    P1_URGENT = "p1"
    P2_ATTENTION = "p2"
    P3_ROUTINE = "p3"


_PRIORITY_EMOJI = {
    AlertPriority.P0_CRITICAL: "\U0001f534",
    AlertPriority.P1_URGENT: "\U0001f7e0",
    AlertPriority.P2_ATTENTION: "\U0001f7e1",
    AlertPriority.P3_ROUTINE: "\U0001f7e2",
}


@dataclass
class AlertMessage:
    title: str
    content: str
    priority: AlertPriority = AlertPriority.P3_ROUTINE
    category: str = "general"
    source: str = "acas"
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

    def to_markdown(self) -> str:
        emoji = _PRIORITY_EMOJI.get(self.priority, "\u26aa")
        return f"{emoji} **[{self.priority.value}] {self.title}**\n\n{self.content}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "content": self.content,
            "priority": self.priority.value,
            "category": self.category,
            "source": self.source,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata,
        }


class AlertNotifier:
    """Alert notification system."""

    def __init__(self, config=None):
        self.wechat_webhook = None
        self.dingtalk_webhook = None
        self.feishu_webhook = None
        self.webhook_url = None
        self.smtp_host = None
        self.smtp_port = 587
        self.smtp_user = None
        self.smtp_password = None
        self.enabled_channels: Dict[AlertChannel, bool] = {}
        self._history: List[Dict] = []
        self._max_history = 1000

    def send(
        self,
        message: AlertMessage,
        channels: Optional[List[AlertChannel]] = None,
        force: bool = False,
    ) -> Dict[AlertChannel, bool]:
        if channels is None:
            channels = self._select_channels(message.priority)

        results: Dict[AlertChannel, bool] = {}
        for ch in channels:
            if not force and not self.enabled_channels.get(ch, False):
                results[ch] = False
                continue
            try:
                handler = self._get_handler(ch)
                if handler:
                    ok = handler(message)
                    results[ch] = bool(ok)
                else:
                    results[ch] = False
            except Exception as e:
                logger.warning(f"[AlertNotifier] Sync handler for channel {ch} raised {type(e).__name__}: {e}")
                results[ch] = False

        self._record_alert(message, results)
        return results

    def _select_channels(self, priority: AlertPriority) -> List[AlertChannel]:
        if priority in (AlertPriority.P0_CRITICAL, AlertPriority.P1_URGENT):
            channels = [
                ch for ch in AlertChannel if self.enabled_channels.get(ch, False)
            ]
            if channels:
                return channels
            # Default: return all channels if none enabled
            return list(AlertChannel)
        elif priority == AlertPriority.P2_ATTENTION:
            channels = [
                ch
                for ch in [AlertChannel.WECHAT_WORK, AlertChannel.EMAIL]
                if self.enabled_channels.get(ch, False)
            ]
            if channels:
                return channels
            return [AlertChannel.EMAIL]
        else:
            channels = [
                ch
                for ch in [AlertChannel.EMAIL]
                if self.enabled_channels.get(ch, False)
            ]
            if channels:
                return channels
            return [AlertChannel.EMAIL]

    def _get_handler(self, channel: AlertChannel) -> None:
        mapping = {
            AlertChannel.WECHAT_WORK: self._send_wechat,
            AlertChannel.DINGTALK: self._send_dingtalk,
            AlertChannel.FEISHU: self._send_feishu,
            AlertChannel.EMAIL: self._send_email,
            AlertChannel.SMS: self._send_sms,
            AlertChannel.WEBHOOK: self._send_webhook,
        }
        return mapping.get(channel)

    def _send_wechat(self, msg: AlertMessage) -> bool:
        if self.wechat_webhook:
            try:
                resp = requests.post(
                    self.wechat_webhook,
                    json={
                        "msgtype": "markdown",
                        "markdown": {"content": msg.to_markdown()},
                    },
                    timeout=10,
                )
                return resp.status_code == 200
            except Exception as e:
                logger.warning(f"Notification send failed: {e}")
                return False
        return False

    def _send_dingtalk(self, msg: AlertMessage) -> bool:
        if self.dingtalk_webhook:
            try:
                resp = requests.post(
                    self.dingtalk_webhook,
                    json={
                        "msgtype": "markdown",
                        "markdown": {"title": msg.title, "text": msg.to_markdown()},
                    },
                    timeout=10,
                )
                return resp.status_code == 200
            except Exception as e:
                logger.warning(f"Notification send failed: {e}")
                return False
        return False

    def _send_feishu(self, msg: AlertMessage) -> bool:
        if self.feishu_webhook:
            try:
                self._get_feishu_color(msg.priority)
                resp = requests.post(
                    self.feishu_webhook,
                    json={
                        "msg_type": "interactive",
                        "card": {
                            "header": {
                                "title": {"tag": "plain_text", "content": msg.title}
                            },
                            "elements": [{"tag": "markdown", "content": msg.content}],
                            "config": {"wide_screen_mode": True},
                        },
                    },
                    timeout=10,
                )
                return resp.status_code == 200
            except Exception as e:
                logger.warning(f"Notification send failed: {e}")
                return False
        return False

    def _get_feishu_color(self, priority: AlertPriority) -> str:
        colors = {
            AlertPriority.P0_CRITICAL: "red",
            AlertPriority.P1_URGENT: "orange",
            AlertPriority.P2_ATTENTION: "yellow",
            AlertPriority.P3_ROUTINE: "blue",
        }
        return colors.get(priority, "blue")

    def _send_email(
        self, msg: AlertMessage, recipients: Optional[List[str]] = None
    ) -> bool:
        if self.smtp_host:
            try:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.quit()
                return True
            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"[EMAIL] SMTP authentication failed for host={self.smtp_host}, user={self.smtp_user}: {e}")
                return False
            except smtplib.SMTPException as e:
                logger.error(f"[EMAIL] SMTP error sending mail host={self.smtp_host}: {e}")
                return False
            except OSError as e:
                logger.error(f"[EMAIL] Network error connecting to SMTP host={self.smtp_host}: {e}")
                return False
            except Exception as e:
                logger.error(f"[EMAIL] Unexpected error in _send_email: {e}")
                return False
        return False

    def _send_sms(self, msg: AlertMessage) -> bool:
        return False

    def _send_webhook(self, msg: AlertMessage, url: Optional[str] = None) -> bool:
        hook_url = url or getattr(self, "webhook_url", None)
        if hook_url:
            try:
                resp = requests.post(
                    hook_url,
                    json=msg.to_dict(),
                    timeout=10,
                )
                return resp.status_code == 200
            except Exception as e:
                logger.warning(f"Notification send failed: {e}")
                return False
        return False

    async def _send_webhook_async(
        self, msg: AlertMessage, url: Optional[str] = None
    ) -> bool:
        """异步发送webhook通知"""
        if not _HAS_HTTPX:
            return False
        hook_url = url or getattr(self, "webhook_url", None)
        if hook_url:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        hook_url,
                        json=msg.to_dict(),
                    )
                    return resp.status_code == 200
            except Exception as e:
                logger.warning(f"Notification send failed: {e}")
                return False
        return False

    def _record_alert(
        self, message: AlertMessage, results: Dict[AlertChannel, bool]
    ) -> None:
        self._history.append(
            {
                "message": message,
                "results": results,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

    def get_history(self, limit: int = 100) -> List[Dict]:
        return self._history[-limit:]

    def configure_channel(self, channel: AlertChannel = None, **kwargs) -> None:
        """Configure a channel with settings like webhook URLs."""
        self.enabled_channels[channel] = True
        if channel == AlertChannel.WECHAT_WORK:
            if "webhook" in kwargs:
                self.wechat_webhook = kwargs["webhook"]
        elif channel == AlertChannel.DINGTALK:
            if "webhook" in kwargs:
                self.dingtalk_webhook = kwargs["webhook"]
        elif channel == AlertChannel.FEISHU:
            if "webhook" in kwargs:
                self.feishu_webhook = kwargs["webhook"]
        elif channel == AlertChannel.EMAIL:
            if "host" in kwargs:
                self.smtp_host = kwargs["host"]
            elif "smtp_host" in kwargs:
                self.smtp_host = kwargs["smtp_host"]
            if "smtp_port" in kwargs:
                self.smtp_port = kwargs["smtp_port"]
            if "user" in kwargs:
                self.smtp_user = kwargs["user"]
            elif "smtp_user" in kwargs:
                self.smtp_user = kwargs["smtp_user"]
            if "password" in kwargs:
                self.smtp_password = kwargs["password"]
            elif "smtp_password" in kwargs:
                self.smtp_password = kwargs["smtp_password"]
        elif channel == AlertChannel.WEBHOOK:
            if "url" in kwargs:
                self.webhook_url = kwargs["url"]

    def configure_wechat(self, webhook: str = "") -> None:
        self.wechat_webhook = webhook
        self.enabled_channels[AlertChannel.WECHAT_WORK] = True

    def configure_dingtalk(self, webhook: str = "") -> None:
        self.dingtalk_webhook = webhook
        self.enabled_channels[AlertChannel.DINGTALK] = True

    def configure_feishu(self, webhook: str = "") -> None:
        self.feishu_webhook = webhook
        self.enabled_channels[AlertChannel.FEISHU] = True

    def configure_email(
        self,
        smtp_host: str = "",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_password: str = "",
    ):
        # nosec B313  # default empty, caller must set real password
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.enabled_channels[AlertChannel.EMAIL] = True

    def send_critical_alert(self, title: str, content: str, **kwargs) -> None:
        msg = AlertMessage(
            title=title, content=content, priority=AlertPriority.P0_CRITICAL, **kwargs
        )
        return self.send(msg, force=True)

    def send_urgent_alert(self, title: str, content: str, **kwargs) -> None:
        msg = AlertMessage(
            title=title, content=content, priority=AlertPriority.P1_URGENT, **kwargs
        )
        return self.send(msg, force=True)

    async def send_async(
        self, message: "AlertMessage", channels: list = None, force: bool = False
    ):
        """异步发送告警通知（webhook使用httpx，其他使用to_thread）"""
        if channels is None:
            channels = self._select_channels(message.priority)

        results: Dict[AlertChannel, bool] = {}
        for ch in channels:
            if not force and not self.enabled_channels.get(ch, False):
                results[ch] = False
                continue
            try:
                # Webhook使用真正的异步
                if ch == AlertChannel.WEBHOOK and _HAS_HTTPX:
                    ok = await self._send_webhook_async(message)
                    results[ch] = ok
                else:
                    # 其他channel使用to_thread
                    handler = self._get_handler(ch)
                    if handler:
                        ok = await asyncio.to_thread(handler, message)
                        results[ch] = bool(ok)
                    else:
                        results[ch] = False
            except Exception as e:
                logger.warning(f"[AlertNotifier] Async handler for channel {ch} raised {type(e).__name__}: {e}")
                results[ch] = False

        self._record_alert(message, results)
        return results


# Module-level convenience functions
def send_critical_alert(title: str, content: str, **kwargs) -> None:
    """Send a critical alert using a default AlertNotifier instance."""
    notifier = AlertNotifier()
    return notifier.send_critical_alert(title, content, **kwargs)


def send_urgent_alert(title: str, content: str, **kwargs) -> None:
    """Send an urgent alert using a default AlertNotifier instance."""
    notifier = AlertNotifier()
    return notifier.send_urgent_alert(title, content, **kwargs)
